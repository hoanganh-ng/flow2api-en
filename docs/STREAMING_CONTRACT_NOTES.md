# Streaming Contract Notes

> **Sprint 003 — Generation Contract Deep Dive**
> Documentation-only. No runtime behavior changes.

## Purpose

This document captures observed streaming behavior for flow2api generation endpoints. It covers which endpoints support streaming, how streaming is requested, SSE framing, chunk shapes, and terminal behavior. All observations are from source inspection only.

## Which Endpoints Support Streaming

| Endpoint | Streaming supported | How streaming is requested |
|----------|---------------------|---------------------------|
| `POST /v1/chat/completions` | Yes | `stream: true` in request body |
| `POST /v1beta/models/{model}:streamGenerateContent` | Yes | Implicitly (endpoint name) |
| `POST /models/{model}:streamGenerateContent` | Yes | Same as above (duplicate mount) |
| `POST /v1beta/models/{model}:generateContent` | No | Always non-streaming |
| `POST /models/{model}:generateContent` | No | Always non-streaming |

**Observed in:** `src/api/routes.py` L850–L973

## How Streaming Is Requested

### OpenAI-compatible (/v1/chat/completions)

- The `ChatCompletionRequest` model includes `stream: bool = False` (`src/core/models.py` L290)
- When `stream=True`, the route returns a `StreamingResponse` (routes.py L864–L873)
- When `stream=False`, the route collects all chunks synchronously via `_collect_non_stream_result` (routes.py L875–L884)

### Gemini-compatible (streamGenerateContent)

- Streaming is inherent to the endpoint — no `stream` field required
- The `alt` query parameter is accepted (`Optional[str]`, routes.py L944) but does not appear to alter streaming behavior in the handler logic
- Always returns `StreamingResponse` (routes.py L955–L963)

## Streaming Response Media Type

Both OpenAI and Gemini streaming endpoints use:

- **`media_type="text/event-stream"`**
- **Response headers:**
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`

**Observed in:** routes.py L866–L872 (OpenAI), L957–L962 (Gemini)

## SSE Framing / Chunk Observations

### OpenAI-compatible SSE framing

The `_iterate_openai_stream` generator (routes.py L717–L737):

1. Yields chunks from `handler.handle_generation(stream=True)`
2. If a chunk already starts with `data: `, it is yielded as-is
3. Otherwise, the chunk is parsed as JSON and re-wrapped: `data: {json}\n\n`
4. After all chunks, yields the terminal sentinel: `data: [DONE]\n\n`

The `GenerationHandler._create_stream_chunk` method (generation_handler.py L2255–L2280) produces SSE frames in this format:

```
data: {"id":"chatcmpl-{ts}","object":"chat.completion.chunk","created":{ts},"model":"flow2api","choices":[{"index":0,"delta":{...},"finish_reason":null}]}\n\n
```

### Gemini-compatible SSE framing

The `_iterate_gemini_stream` generator (routes.py L740–L785):

1. Yields chunks from `handler.handle_generation(stream=True)`
2. If chunk starts with `data: `, strips the prefix and checks for `[DONE]` sentinel (skips it)
3. Parses the OpenAI-format chunk and converts via `_convert_openai_stream_chunk_to_gemini_event`
4. Non-`data:` chunks are also parsed and converted
5. Errors during streaming are converted to Gemini error format and streaming terminates

**There is no explicit `[DONE]` sentinel in the Gemini stream** — the stream simply ends after the last converted event.

## OpenAI-Compatible Streaming Chunk Shape

Observed in `GenerationHandler._create_stream_chunk` (generation_handler.py L2255–L2280):

```json
{
  "id": "chatcmpl-{timestamp}",
  "object": "chat.completion.chunk",
  "created": 1234567890,
  "model": "flow2api",
  "choices": [{
    "index": 0,
    "delta": {
      "role": "assistant",       // first chunk only
      "reasoning_content": "..." // progress/status messages
      // OR
      "content": "..."           // final content with finish_reason
    },
    "finish_reason": null        // or "stop" on final chunk
  }]
}
```

**Key observation:** Progress/status messages are emitted as `reasoning_content` in the `delta`. The final content (image URL or video URL) is emitted with `finish_reason: "stop"` and placed in `delta.content`.

**Compatibility note:** The `reasoning_content` field is not part of the standard OpenAI ChatCompletion chunk spec. It appears to be a custom extension (possibly inspired by reasoning/thinking model conventions). Clients that strictly parse only `content` may miss progress updates.

## Gemini-Compatible Streaming Chunk Shape

Observed in `_convert_openai_stream_chunk_to_gemini_event` (routes.py L685–L714):

```json
{
  "candidates": [{
    "index": 0,
    "content": {
      "role": "model",
      "parts": [{"text": "..."}]
    },
    "finishReason": "STOP"       // only on terminal chunk
  }],
  "modelVersion": "{model}"
}
```

**Conversion details:**

- `delta.reasoning_content` and `delta.content` are both checked (reasoning_content preferred, routes.py L695)
- `finish_reason` mapping (routes.py L674–L682):
  - `stop` → `STOP`
  - `length` → `MAX_TOKENS`
  - `content_filter` → `SAFETY`
  - Other/unknown → `STOP`
- If neither text nor finish_reason is present, the chunk is skipped (returns `None`)

## Finish / Terminal Chunk Behavior

### OpenAI stream

1. The last content chunk is emitted with `finish_reason: "stop"` and `delta.content` containing the media URL in Markdown format
2. After all handler chunks are exhausted, `data: [DONE]\n\n` is yielded (routes.py L737)

### Gemini stream

1. The last converted event includes `finishReason: "STOP"` in the candidate
2. **No `[DONE]` sentinel** — the stream ends after the last event
3. The `[DONE]` from the internal OpenAI stream is explicitly consumed and skipped (routes.py L756–L757)

## Error Behavior During Streaming

### OpenAI stream

- If the handler yields an error response chunk (JSON with `error` key), it is passed through as a `data: {json}\n\n` SSE event
- The stream may or may not continue after an error — depends on whether the handler returns after yielding the error
- The `data: [DONE]` sentinel is still emitted at the end

### Gemini stream

- Errors are detected by checking for `"error"` key in parsed payloads (routes.py L759, L774)
- On error, a Gemini-format error event is yielded and the stream **terminates immediately** (`return` after yield, routes.py L762–L763)
- Error format:
  ```json
  {
    "error": {
      "code": 500,
      "message": "...",
      "status": "INTERNAL"
    }
  }
  ```

## Unknowns Requiring Runtime Fixture Capture

1. **Exact chunk timing** — how frequently progress chunks are emitted depends on upstream polling intervals; not deterministic from source alone
2. **Chunk ordering guarantees** — progress messages, upload status, and content chunks are interleaved; the exact sequence varies by generation type (image vs. video) and whether caching is enabled
3. **Client disconnect handling** — `asyncio.CancelledError` is caught in `handle_generation` (L1325–L1345) but it is unclear whether the SSE connection is cleanly terminated or left hanging from the client perspective
4. **Gemini `alt=sse` query parameter** — accepted but not observed to change behavior; real Gemini API uses `alt=sse` for SSE framing, but this implementation appears to use SSE regardless of the `alt` value
5. **Multiple content chunks for video** — video generation involves a long polling loop; whether multiple content-bearing chunks are emitted (progress updates as `reasoning_content`) or only a single final chunk needs fixture verification
6. **Binary/image data in streaming** — it is unclear from source whether any streaming path emits base64-encoded image data inline, or always URLs
7. **`data:` prefix double-wrapping risk** — the handler already emits `data: ` prefixed strings, and the route also wraps non-prefixed chunks; if the handler format changes, double-wrapping could occur
