# Generation Route Mocking Plan

> Sprint 006D — Mocked Generation Route Seam Discovery
> This document specifies the proposed fake-handler interface, request
> construction approach, mutable-state isolation rules, and recommended
> test matrix for a future Sprint 006E.
> No code was written. No routes were invoked.

---

## Patching Strategy

### Target Symbol

`src.api.routes.generation_handler`

### Why This Works

- All route functions call `_ensure_generation_handler()`, which reads the
  module-level `src.api.routes.generation_handler` global directly.
- There are no captured references, early-bound aliases, or closures over
  this symbol. `_ensure_generation_handler` performs a fresh read each call.
- `unittest.mock.patch("src.api.routes.generation_handler", fake_handler)`
  will safely replace it for the duration of each test.

### Setup / Teardown

```python
def setUp(self):
    self._original_handler = src.api.routes.generation_handler
    src.api.routes.generation_handler = self.fake_handler

def tearDown(self):
    src.api.routes.generation_handler = self._original_handler
```

Or equivalently with `patch`:

```python
@patch("src.api.routes.generation_handler", fake_handler)
```

### What Is NOT Patched

- `MODEL_CONFIG` — read-only after module import; tests can use any known
  model key.
- `verify_api_key_flexible` — must be patched or bypassed (it is a FastAPI
  dependency).
- `resolve_model_name` — pure function; left as-is.
- `debug_logger` — harmless; left as-is.

---

## Proposed Fake-Handler Interface

The fake handler must provide a single method: `handle_generation`.

### `handle_generation` Signature

```python
async def handle_generation(
    self,
    model: str,
    prompt: str,
    images: Optional[List[bytes]] = None,
    stream: bool = False,
    base_url_override: Optional[str] = None,
    video_media_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
```

### Return Contract

The method is an **async generator** that yields strings. The route layer
interprets these strings:

| Yield Shape | Content Format | Route Interpretation |
|-------------|---------------|---------------------|
| SSE chunk | `"data: {json}\n\n"` | Passed through in streaming; parsed in non-streaming |
| JSON string | `"{json with choices}"` | Parsed by `_parse_handler_result` |
| Error JSON | `"{json with error}"` | Detected and converted to error response |

### Non-Streaming Fake Behavior

For a successful non-streaming image generation:

```python
async def handle_generation(self, model, prompt, images=None, stream=False,
                            base_url_override=None, video_media_id=None):
    yield json.dumps({
        "id": "chatcmpl-fake",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "![Generated Image](https://example.com/fake.png)"
            },
            "finish_reason": "stop"
        }]
    })
```

For a successful non-streaming text generation:

```python
yield json.dumps({
    "choices": [{
        "message": {"role": "assistant", "content": "Hello from fake handler"},
        "finish_reason": "stop"
    }]
})
```

For an error:

```python
yield json.dumps({
    "error": {
        "message": "fake error",
        "type": "server_error",
        "code": "generation_failed",
        "status_code": 500
    }
})
```

### Streaming Fake Behavior

For OpenAI streaming:

```python
async def handle_generation(self, model, prompt, images=None, stream=False,
                            base_url_override=None, video_media_id=None):
    chunk = {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {"content": "Hello"},
            "finish_reason": None
        }]
    }
    yield f"data: {json.dumps(chunk)}\n\n"
    final = {**chunk, "choices": [{**chunk["choices"][0], "delta": {}, "finish_reason": "stop"}]}
    yield f"data: {json.dumps(final)}\n\n"
```

For Gemini streaming, the same handler output is consumed by
`_iterate_gemini_stream` which converts each OpenAI-format chunk to Gemini
format via `_convert_openai_stream_chunk_to_gemini_event`.

### Handler-Uninitialized Behavior

When `generation_handler` is `None`, `_ensure_generation_handler()` raises
`HTTPException(500, "Generation handler not initialized")`.

- In `create_chat_completion`: re-raised, caught by outer `except HTTPException`.
- In `generate_content`: caught by `except HTTPException as exc`, returned as
  Gemini error JSON.
- In `stream_generate_content`: caught by `except HTTPException as exc`, returned
  as Gemini error JSON.

### Exceptions from Handler

If `handle_generation` raises an exception (rather than yielding an error
JSON), the route layer catches it:

- `create_chat_completion`: `except Exception as exc` → `HTTPException(500)`.
- `generate_content`: `except Exception as exc` → `JSONResponse(500, ...)`.
- `stream_generate_content`: caught before `StreamingResponse` creation.
  Errors during streaming iteration are **not caught by the route layer** —
  they propagate to the ASGI server.

---

## Request Construction

### OpenAI Non-Streaming (Minimal)

```python
ChatCompletionRequest(
    model="gemini-3.0-pro-image-landscape",
    messages=[ChatMessage(role="user", content="Generate a cat")],
    stream=False,
)
```

### OpenAI Streaming (Minimal)

```python
ChatCompletionRequest(
    model="gemini-3.0-pro-image-landscape",
    messages=[ChatMessage(role="user", content="Generate a cat")],
    stream=True,
)
```

### Gemini Non-Streaming (Minimal)

```python
GeminiGenerateContentRequest(
    contents=[GeminiContent(
        role="user",
        parts=[GeminiPart(text="Generate a cat")]
    )]
)
```

### Synthetic Starlette Request

The `raw_request: Request` parameter is used only for `_get_request_base_url`,
which reads `request.headers` for `x-forwarded-proto`, `x-forwarded-host`,
and `host`. A minimal synthetic scope:

```python
scope = {
    "type": "http",
    "method": "POST",
    "path": "/v1/chat/completions",
    "headers": [
        (b"host", b"localhost:8000"),
    ],
    "query_string": b"",
    "server": ("localhost", 8000),
    "scheme": "http",
}
request = Request(scope)
```

### Bypassing Auth

`verify_api_key_flexible` is a FastAPI dependency. For direct function calls
(bypassing FastAPI routing), pass `api_key="fake"` as a keyword argument.
No verification occurs when calling the function directly.

### Model Selection

Use any model key present in `MODEL_CONFIG`. For non-streaming tests:

- `"gemini-3.0-pro-image-landscape"` — image type, no network in fake path.
- Video models are deferred (complex polling behavior).

### Image Content in Messages

For image output tests, the fake handler should yield content containing a
Markdown image reference:

```python
"content": "![Generated Image](https://example.com/fake.png)"
```

For video output:

```python
"content": "```html\n<video src='https://example.com/fake.mp4' controls></video>\n```"
```

---

## Mutable State Isolation

| State | Isolation Strategy |
|-------|--------------------|
| `src.api.routes.generation_handler` | Save before test, restore in tearDown |
| `MODEL_CONFIG` | Read-only after import; no isolation needed |
| Prometheus counters | Not reset between tests; assertions should not depend on absolute values |
| `debug_logger` | No state to isolate; logging is side-effect-free for tests |

### Risks

- If a test sets `generation_handler` and fails before tearDown restores it,
  subsequent tests see a stale fake. Mitigation: always use `try/finally` or
  `patch` context manager.
- `MODEL_CONFIG` is mutated at import time by `_apply_veo_3_1_model_updates()`.
  After import, it is stable. Tests should not mutate it.

---

## Recommended Test Matrix

### Priority 1 — Smallest Safe First Slice

| Test | Route Function | Request | Fake Behavior | Assertions |
|------|---------------|---------|---------------|------------|
| OpenAI non-streaming text success | `create_chat_completion` | `ChatCompletionRequest(model=..., messages=[...], stream=False)` | yield JSON with `choices[0].message.content` | response is `JSONResponse`, status 200, body contains content |
| Gemini non-streaming text success | `generate_content` | `GeminiGenerateContentRequest(contents=[...])` + model path param | yield JSON with `choices[0].message.content` | response is `JSONResponse`, body has `candidates[0].content.parts` |
| Handler uninitialized (OpenAI) | `create_chat_completion` | Any valid request | handler=None | HTTPException(500) raised |
| Handler uninitialized (Gemini) | `generate_content` | Any valid request | handler=None | JSONResponse with Gemini error shape, status 500 |
| Handler yields error (OpenAI) | `create_chat_completion` | Valid request, stream=False | yield error JSON | JSONResponse with error status |
| Handler yields error (Gemini) | `generate_content` | Valid request | yield error JSON | JSONResponse with Gemini error shape |
| Unknown model (OpenAI) | `create_chat_completion` | `model="nonexistent"` | Not reached (normalization may reject) | HTTPException(400) |

### Priority 2 — Extended Cases

| Test | Route Function | Notes |
|------|---------------|-------|
| Image output (OpenAI) | `create_chat_completion` | Fake yields Markdown image; assert `url` field |
| Image output (Gemini) | `generate_content` | Fake yields Markdown image; assert `inlineData` parts |
| Video output (Gemini) | `generate_content` | Fake yields HTML video; assert `fileData` parts |
| Reasoning content (streaming) | `create_chat_completion` | Fake yields `reasoning_content` delta |
| Usage metadata | — | Deferred; handler does not emit usage in current code |
| `generationConfig`-based model resolution | `create_chat_completion` | Uses `contents` field with `generationConfig` |

### Deferred

| Area | Reason |
|------|--------|
| Streaming cancellation | Requires ASGI-level testing |
| Media URL retrieval (`retrieve_image_data`) | Network dependency |
| Video continuation (`extend://`) | Complex state machine |
| Real token/proxy/browser/captcha | High-risk boundaries |
| Upstream network semantics | Out of scope |
| WebSocket captcha endpoint | Separate subsystem |
| Admin routes | Separate subsystem |

---

## Streaming Test Approach Recommendation

### Recommended: Pure Async-Generator Tests

For Sprint 006E, test the streaming conversion helpers
(`_iterate_openai_stream`, `_iterate_gemini_stream`) by calling them
directly as async generators, **not** through `StreamingResponse`.

```python
async def test_openai_stream_iteration(self):
    chunks = []
    async for chunk in _iterate_openai_stream(normalized, base_url_override=None):
        chunks.append(chunk)
    self.assertTrue(any("[DONE]" in c for c in chunks))
```

### Why Not StreamingResponse.body_iterator

- Constructing a `StreamingResponse` requires a complete ASGI send/receive
  cycle to iterate `body_iterator`.
- The `body_iterator` is the async generator itself, so calling it directly
  is simpler and equivalent.
- Direct consumption avoids FastAPI/Starlette internals entirely.

### Why Not Defer Until HTTP-Level Testing

- The streaming conversion logic (`_iterate_openai_stream`,
  `_iterate_gemini_stream`, `_convert_openai_stream_chunk_to_gemini_event`)
  is pure async-generator code that can be tested without HTTP.
- Testing at the generator level catches conversion bugs before committing
  to an HTTP harness.

---

## Safety Rationale for Each Priority 1 Test

| Test | Safety |
|------|--------|
| OpenAI non-stream success | Direct call; fake handler yields deterministic JSON; no network, no DB |
| Gemini non-stream success | Direct call; fake handler; Gemini conversion is pure functions |
| Handler uninitialized | Sets handler to None; tests `_ensure_generation_handler` guard |
| Handler error | Fake yields error JSON; tests error conversion path; no exception raised |
| Unknown model | Tests `_resolve_request_model` with invalid model; may raise HTTPException before handler |

---

## Starlette Request for Direct Calls

When calling route functions directly (not through TestClient), pass the
`raw_request` parameter as a minimal `Request`:

```python
from starlette.requests import Request

scope = {
    "type": "http",
    "method": "POST",
    "path": "/",
    "headers": [(b"host", b"test.local")],
    "query_string": b"",
    "server": ("test.local", 80),
    "scheme": "http",
}
raw_request = Request(scope)
```

This satisfies `_get_request_base_url` which reads only `headers` and `url.scheme`.
