# Generation Route Dependency Map

> Sprint 006D — Mocked Generation Route Seam Discovery
> This document records the actual function signatures, dependency chains,
> and risky call boundaries for each generation route in `src/api/routes.py`.
> No routes were invoked. No runtime source was modified.

---

## Route Function Index

| # | Function | HTTP Method | Path(s) | Sync/Async | Response Type |
|---|----------|-------------|---------|------------|---------------|
| 1 | `create_chat_completion` | POST | `/v1/chat/completions` | async | `JSONResponse` or `StreamingResponse` |
| 2 | `generate_content` | POST | `/v1beta/models/{model}:generateContent`, `/models/{model}:generateContent` | async | `JSONResponse` |
| 3 | `stream_generate_content` | POST | `/v1beta/models/{model}:streamGenerateContent`, `/models/{model}:streamGenerateContent` | async | `StreamingResponse` or `JSONResponse` (error) |

Read-only model routes (`list_models`, `list_model_aliases`, `list_gemini_models`,
`get_gemini_model`) are documented in Sprint 006C and are not repeated here.

---

## 1. `create_chat_completion` (OpenAI Unified Route)

```python
@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
):
```

### Request Model

`ChatCompletionRequest` (Pydantic, `extra="allow"`):

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `model` | `str` | Yes | — |
| `messages` | `Optional[List[ChatMessage]]` | No | `None` |
| `stream` | `bool` | No | `False` |
| `temperature` | `Optional[float]` | No | `None` |
| `max_tokens` | `Optional[int]` | No | `None` |
| `image` | `Optional[str]` | No | `None` |
| `video` | `Optional[str]` | No | `None` |
| `generationConfig` | `Optional[GenerationConfigParam]` | No | `None` |
| `contents` | `Optional[List[Any]]` | No | `None` |

### Non-Streaming Path (`stream=False`)

Call chain:

```
create_chat_completion
  → _normalize_openai_request(request)
    → _extract_prompt_and_images_from_openai_messages(messages)
      → _load_image_bytes_from_uri(uri)  [network if non-data URI]
    → _resolve_request_model(model, request)
      → resolve_model_name(model, request, MODEL_CONFIG)
    → _append_openai_reference_images(model, messages, images)
      → retrieve_image_data(url)  [network]
  → _get_request_base_url(raw_request)  [reads request.headers]
  → _collect_non_stream_result(model, prompt, images, base_url, video_media_id)
    → _ensure_generation_handler()
      → reads src.api.routes.generation_handler
    → handler.handle_generation(...) [async generator]
      → consumes single yielded result
  → _parse_handler_result(result)
  → _build_openai_json_response(payload)
    → _get_error_status_code(payload)
```

Response: `JSONResponse` with status from `_get_error_status_code` (200 on success,
extracted from `payload["error"]["status_code"]` on error).

### Streaming Path (`stream=True`)

Call chain:

```
create_chat_completion
  → _normalize_openai_request(request)
  → _get_request_base_url(raw_request)
  → StreamingResponse(
      _iterate_openai_stream(normalized, base_url),
      media_type="text/event-stream",
      headers={Cache-Control, Connection, X-Accel-Buffering},
    )
```

`_iterate_openai_stream` is an async generator:

```
_iterate_openai_stream
  → _ensure_generation_handler()
  → handler.handle_generation(model, prompt, images, stream=True, ...)
  → for each chunk:
      if starts with "data: ": yield chunk as-is
      else: parse JSON, re-frame as "data: {json}\n\n"
  → yield "data: [DONE]\n\n"
```

Response: `StreamingResponse` with `text/event-stream`.

### Dependencies

| Dependency | How Reached | Risk Level |
|-----------|-------------|------------|
| `generation_handler` | `_ensure_generation_handler()` reads `src.api.routes.generation_handler` | Patchable |
| `verify_api_key_flexible` | FastAPI `Depends()` | Auth boundary |
| `resolve_model_name` | `src.core.model_resolver` | Pure function |
| `MODEL_CONFIG` | `src.services.generation_handler` module global | Read-only dict |
| `retrieve_image_data` | Local helper → `AsyncSession` (curl_cffi) | Network |
| `_load_image_bytes_from_uri` | Local helper → `retrieve_image_data` | Network |
| `debug_logger` | `src.core.logger` | Logging only |

### Globals Read

- `src.api.routes.generation_handler` (module-level, set by `set_generation_handler`)
- `src.services.generation_handler.MODEL_CONFIG` (module-level dict)

### Exceptions Caught

- `HTTPException`: re-raised as-is.
- `Exception`: wrapped as `HTTPException(500, str(exc))`.

---

## 2. `generate_content` (Gemini Non-Streaming)

```python
@router.post("/v1beta/models/{model}:generateContent")
@router.post("/models/{model}:generateContent")
async def generate_content(
    model: str,
    request: GeminiGenerateContentRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
):
```

### Request Model

`GeminiGenerateContentRequest` (Pydantic, `extra="allow"`):

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `contents` | `List[GeminiContent]` | Yes | — |
| `generationConfig` | `Optional[GenerationConfigParam]` | No | `None` |
| `systemInstruction` | `Optional[GeminiContent]` | No | `None` |

`GeminiContent`: `role: Optional[Literal["user","model"]]`, `parts: List[GeminiPart]`.

`GeminiPart`: `text: Optional[str]`, `inlineData: Optional[GeminiInlineData]`,
`fileData: Optional[GeminiFileData]`.

### Call Chain

```
generate_content
  → _normalize_gemini_request(model, request)
    → _resolve_request_model(model, request)
    → _extract_prompt_and_images_from_gemini_contents(contents)
      → _load_image_bytes_from_uri(uri)  [network if fileData]
    → _extract_text_from_gemini_content(systemInstruction)
    → _sanitize_media_prompt(prompt)  [if media model]
    → _should_ignore_media_system_instruction(...)  [if media model]
  → _get_request_base_url(raw_request)
  → _collect_non_stream_result(model, prompt, images, base_url, video_media_id)
    → _ensure_generation_handler()
    → handler.handle_generation(...) [async generator, single result]
  → _parse_handler_result(result)
  → _enrich_payload_with_direct_url(payload)
    → _extract_url_from_openai_payload(payload)
  → if "error" in payload:
      → _build_gemini_error_response_from_handler(payload)
  → else:
      → _build_gemini_success_payload(payload, model)
        → _build_gemini_parts_from_output(output)
          → _build_image_parts_from_uri(uri)  [network via retrieve_image_data]
          → _build_video_parts_from_uri(uri)  [pure]
```

Response: `JSONResponse`. On error: status from `_get_error_status_code`,
body shaped as `_build_gemini_error_payload`. On success: 200 with Gemini
candidates structure.

### Exceptions Caught

- `HTTPException`: converted to `JSONResponse(status_code, _build_gemini_error_payload(...))`.
- `Exception`: `JSONResponse(500, _build_gemini_error_payload(500, str(exc)))`.

### Dependencies

Same as OpenAI route plus `_build_gemini_success_payload` which may call
`retrieve_image_data` for image URIs in the output (network).

---

## 3. `stream_generate_content` (Gemini Streaming)

```python
@router.post("/v1beta/models/{model}:streamGenerateContent")
@router.post("/models/{model}:streamGenerateContent")
async def stream_generate_content(
    model: str,
    request: GeminiGenerateContentRequest,
    raw_request: Request,
    alt: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key_flexible),
):
```

### Call Chain

```
stream_generate_content
  → _normalize_gemini_request(model, request)
  → _get_request_base_url(raw_request)
  → StreamingResponse(
      _iterate_gemini_stream(normalized, model, base_url),
      media_type="text/event-stream",
      headers={Cache-Control, Connection, X-Accel-Buffering},
    )
```

`_iterate_gemini_stream` is an async generator:

```
_iterate_gemini_stream
  → _ensure_generation_handler()
  → handler.handle_generation(model, prompt, images, stream=True, ...)
  → for each chunk:
      if starts with "data: ":
        strip "data: ", skip if "[DONE]"
        parse JSON
        if "error": yield gemini error event, return
        else: _convert_openai_stream_chunk_to_gemini_event(payload, model)
      else:
        parse JSON
        if "error": yield gemini error event, return
        else: _convert_openai_stream_chunk_to_gemini_event(payload, model)
```

### Gemini Termination

Unlike the OpenAI stream, the Gemini stream does NOT emit `data: [DONE]`.
It simply ends when the handler generator is exhausted.

### Exceptions Caught

- `HTTPException`: `JSONResponse(status_code, _build_gemini_error_payload(...))`.
- `Exception`: `JSONResponse(500, _build_gemini_error_payload(500, str(exc)))`.
- Errors raised before `StreamingResponse` body begins are returned as JSON.
- Errors during streaming are yielded as SSE error events inside the stream.

---

## Shared Internal Helpers

### `_collect_non_stream_result`

```python
async def _collect_non_stream_result(
    model: str, prompt: str, images: List[bytes],
    base_url_override: Optional[str] = None,
    video_media_id: Optional[str] = None,
) -> str:
```

- Calls `_ensure_generation_handler()`.
- Iterates `handler.handle_generation(stream=False, ...)` with `async for`.
- Captures the last yielded chunk as `result`.
- Raises `HTTPException(500, "Generation failed: No response")` if no result.
- Returns the raw string result (JSON or plain text).

### `_ensure_generation_handler`

```python
def _ensure_generation_handler() -> GenerationHandler:
```

- Reads module-level `generation_handler`.
- Raises `HTTPException(500, "Generation handler not initialized")` if `None`.

### `_normalize_openai_request`

```python
async def _normalize_openai_request(request: ChatCompletionRequest) -> NormalizedGenerationRequest:
```

- If `request.messages` is set: extracts prompt/images/video_media_id from messages.
- If `request.contents` is set: delegates to `_normalize_gemini_request`.
- Raises `HTTPException(400)` if neither is provided.

### `_normalize_gemini_request`

```python
async def _normalize_gemini_request(model: str, request: GeminiGenerateContentRequest) -> NormalizedGenerationRequest:
```

- Resolves model name via `_resolve_request_model`.
- Extracts prompt and images from `contents`.
- Handles `systemInstruction` (prepends to prompt unless media model ignores it).
- Sanitizes media prompts (strips tool/agent scaffolding).

### `NormalizedGenerationRequest`

```python
@dataclass
class NormalizedGenerationRequest:
    model: str
    prompt: str
    images: List[bytes]
    messages: Optional[List[ChatMessage]] = None
    video_media_id: Optional[str] = None
```

---

## GenerationHandler.handle_generation

```python
async def handle_generation(
    self,
    model: str,
    prompt: str,
    images: Optional[List[bytes]] = None,
    stream: bool = False,
    base_url_override: Optional[str] = None,
    video_media_id: Optional[str] = None,
) -> AsyncGenerator:
```

This is an **async generator** that always yields strings. The route layer
consumes it differently depending on stream mode:

- **Non-streaming**: `_collect_non_stream_result` iterates and captures the
  last yielded value.
- **Streaming**: `_iterate_openai_stream` or `_iterate_gemini_stream` yields
  each chunk through to the `StreamingResponse`.

### Yielded String Types

| Shape | Content | Used In |
|-------|---------|---------|
| `"data: {json}\n\n"` | SSE-formatted stream chunk (from `_create_stream_chunk`) | Streaming progress updates |
| `"{json}"` | Completion response (from `_create_completion_response`) | Final non-streaming result |
| `"{json}"` | Error response (from `_create_error_response`) | Error in both modes |

### What handle_generation Reaches

| Service | Access Pattern | Risky? |
|---------|---------------|--------|
| `self.flow_client` | `clear_request_fingerprint()`, `prefill_remote_browser_pool()` | Yes — upstream |
| `self.token_manager` | `ensure_valid_token()`, `record_usage()`, `record_success()`, `record_error()`, `ensure_project_exists()` | Yes — credentials |
| `self.load_balancer` | `select_token()`, `get_unavailable_reason()`, `release_pending()` | Yes — state |
| `self.db` | `update_task()` (via `_fail_video_task`, `_log_request`) | Yes — persistence |
| `self.file_cache` | File cache operations | Moderate |
| `self.concurrency_manager` | Concurrency control | Yes — locks |
| `MODEL_CONFIG` | Module-level dict lookup | No — read-only |
| `record_generation_result` | Prometheus metric | Low — metric side-effect |
| `debug_logger` | Logging | Low |

---

## Handler Assignment and Lifecycle

```
src/main.py lifespan:
  generation_handler = GenerationHandler(flow_client, token_manager, ...)
  routes.set_generation_handler(generation_handler)
```

`set_generation_handler` assigns the module-level `src.api.routes.generation_handler`.
All route functions read this symbol via `_ensure_generation_handler()`.

---

## Metrics Modified

- `GENERATION_REQUESTS_TOTAL` (Counter) via `record_generation_result`.
- `GENERATION_DURATION_SECONDS` (Histogram) via `record_generation_result`.

These are modified inside `handle_generation`, not in the route layer itself.
A fake handler that does not call `record_generation_result` will produce no
metric side-effects.

---

## Mutable Global State

| Symbol | Module | Mutation Point | Reset Risk |
|--------|--------|---------------|------------|
| `generation_handler` | `src.api.routes` | `set_generation_handler()` | Must save/restore in tests |
| `MODEL_CONFIG` | `src.services.generation_handler` | Module init + `_apply_veo_3_1_model_updates()` | Read-only after import |
| Prometheus counters | `src.core.monitoring` | `record_generation_result` | Not resettable easily |
