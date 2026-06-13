# Sprint 006D — Mocked Generation Route Seam Discovery

## Goal

Inspect and document the generation route boundary so a later sprint can add
the smallest safe mocked route tests. This sprint is discovery and
documentation only. No generation routes were invoked. No tests were added.

---

## Source Inspected

| File | Purpose |
|------|---------|
| `src/api/routes.py` | Route functions, request normalization, response conversion, streaming iterators |
| `src/services/generation_handler.py` | `GenerationHandler` class, `MODEL_CONFIG`, `handle_generation` async generator |
| `src/core/models.py` | Pydantic request/response models |
| `src/core/monitoring.py` | Prometheus metric definitions |
| `src/main.py` | Handler assignment during lifespan |

No other modules were inspected in detail. `src/core/model_resolver.py`,
`src/core/auth.py`, and service modules were referenced only by import name.

---

## Route Signatures

### OpenAI Unified Route

```python
@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
) -> JSONResponse | StreamingResponse
```

### Gemini Non-Streaming

```python
@router.post("/v1beta/models/{model}:generateContent")
@router.post("/models/{model}:generateContent")
async def generate_content(
    model: str,
    request: GeminiGenerateContentRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
) -> JSONResponse
```

### Gemini Streaming

```python
@router.post("/v1beta/models/{model}:streamGenerateContent")
@router.post("/models/{model}:streamGenerateContent")
async def stream_generate_content(
    model: str,
    request: GeminiGenerateContentRequest,
    raw_request: Request,
    alt: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key_flexible),
) -> StreamingResponse | JSONResponse
```

---

## Dependency Findings

### Shared Entry Point

All three routes share the same handler access pattern:

```
route function
  → _ensure_generation_handler()
    → reads src.api.routes.generation_handler (module global)
  → handler.handle_generation(...)  [async generator]
```

### Call-Chain Reachability

From the route layer, the following services are reachable through
`handle_generation`:

| Service | Reached Via | Patchable at Route Layer? |
|---------|------------|---------------------------|
| `FlowClient` | `handler.flow_client` | No — inside handler |
| `TokenManager` | `handler.token_manager` | No — inside handler |
| `LoadBalancer` | `handler.load_balancer` | No — inside handler |
| `Database` | `handler.db` | No — inside handler |
| `ConcurrencyManager` | `handler.concurrency_manager` | No — inside handler |
| `FileCache` | `handler.file_cache` | No — inside handler |
| `ProxyManager` | via `FileCache` | No — inside handler |
| Prometheus metrics | `record_generation_result` | No — called inside handler |

**Key insight**: By replacing the entire handler with a fake, none of these
services are reached. The fake handler short-circuits the entire dependency
chain.

### Route-Layer Network Calls

The route layer itself can make network calls during request normalization:

- `_load_image_bytes_from_uri` → `retrieve_image_data` → `AsyncSession.get()`
  (for `http://`, `https://`, or `/tmp/` image URIs in messages/contents).
- `_append_openai_reference_images` → `retrieve_image_data` (for reference
  images in assistant message history).
- `_build_gemini_parts_from_output` → `_build_image_parts_from_uri` →
  `retrieve_image_data` (for Gemini non-streaming image output).

**Mitigation for tests**: Use only plain text prompts (no image URIs) and
fake handler output containing data URIs or `https://` URLs that the test
controls. For Priority 1 tests, avoid image input entirely.

---

## generation_handler Assignment and Patchability

### Assignment

```python
# src/api/routes.py line 71
generation_handler: GenerationHandler = None

# src/api/routes.py line 85
def set_generation_handler(handler: GenerationHandler):
    global generation_handler
    generation_handler = handler
```

Called from `src/main.py` during application lifespan startup:

```python
generation_handler = GenerationHandler(flow_client, token_manager, ...)
routes.set_generation_handler(generation_handler)
```

### Patchability

- **Yes**, `src.api.routes.generation_handler` can be safely patched via
  `unittest.mock.patch("src.api.routes.generation_handler", fake_handler)`.
- All route functions read this symbol through `_ensure_generation_handler()`,
  which performs a fresh global read on every call.
- No imported aliases, closures, or early-bound references exist.
- The import `from ..services.generation_handler import GenerationHandler` in
  `routes.py` imports only the class for type annotation, not an instance.

### Imported Aliases

The only import from `generation_handler` module is:

```python
from ..services.generation_handler import MODEL_CONFIG, GenerationHandler
```

`MODEL_CONFIG` is a module-level dict, read-only after import.
`GenerationHandler` is the class, used only for type hints. Neither creates
an instance at import time.

---

## Proposed Fake-Handler Interface

See [GENERATION_ROUTE_MOCKING_PLAN.md](../GENERATION_ROUTE_MOCKING_PLAN.md)
for the full specification. Summary:

### Required Method

```python
class FakeGenerationHandler:
    async def handle_generation(
        self,
        model: str,
        prompt: str,
        images: Optional[List[bytes]] = None,
        stream: bool = False,
        base_url_override: Optional[str] = None,
        video_media_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        ...
```

### Return Shapes

| Scenario | Yielded Value |
|----------|---------------|
| Non-stream success | `json.dumps({"choices": [{"message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}]})` |
| Non-stream error | `json.dumps({"error": {"message": "...", "status_code": 500, ...}})` |
| Stream chunk | `f"data: {json.dumps(chunk)}\n\n"` |
| Unknown model | Never reached — handler validates model in `MODEL_CONFIG` before yielding |

### Methods NOT Required

The fake handler does NOT need:

- `check_token_availability` — not called by route layer.
- `_create_stream_chunk` — the fake yields pre-formatted strings.
- `_create_completion_response` — the fake yields pre-formatted JSON.
- `_create_error_response` — the fake yields pre-formatted error JSON.
- Any `__init__` dependencies — the fake has no real service dependencies.

---

## Request Construction

See [GENERATION_ROUTE_MOCKING_PLAN.md](../GENERATION_ROUTE_MOCKING_PLAN.md)
for full examples. Summary:

### Pydantic Models (Preferred)

- OpenAI: `ChatCompletionRequest(model=..., messages=[...], stream=...)`.
- Gemini: `GeminiGenerateContentRequest(contents=[...])`.
- Both accept `extra="allow"`, so unknown fields are silently ignored.

### Starlette Request (Required for `raw_request`)

Minimal scope for `_get_request_base_url`:

```python
scope = {
    "type": "http", "method": "POST", "path": "/",
    "headers": [(b"host", b"test.local")],
    "query_string": b"", "server": ("test.local", 80), "scheme": "http",
}
```

### Auth Bypass for Direct Calls

When calling route functions directly (not through FastAPI/TestClient),
pass `api_key="fake"` as a keyword argument. `verify_api_key_flexible` is
a FastAPI dependency that is not invoked during direct calls.

---

## Non-Streaming Analysis

### OpenAI Non-Streaming (`create_chat_completion`, `stream=False`)

1. `_normalize_openai_request` extracts prompt, images, model, video_media_id.
2. `_get_request_base_url` reads headers from `raw_request`.
3. `_collect_non_stream_result` calls `handler.handle_generation(stream=False)`,
   iterates the async generator, captures the last yielded string.
4. `_parse_handler_result` parses the string as JSON (falls back to `{"result": text}`).
5. `_build_openai_json_response` creates a `JSONResponse` with status from
   `_get_error_status_code` (200 if no `error` key, extracted status otherwise).

**Success shape**: OpenAI chat completion JSON with `choices[0].message.content`.

**Error shape**: `{"error": {"message": ..., "status_code": ...}}` with
corresponding HTTP status.

**Handler-uninitialized**: `HTTPException(500, "Generation handler not initialized")`,
re-raised by outer `except HTTPException: raise`.

**Handler exception**: Caught by `except Exception as exc`, raised as
`HTTPException(500, str(exc))`.

### Gemini Non-Streaming (`generate_content`)

1. `_normalize_gemini_request` extracts prompt, images, resolved model.
2. `_collect_non_stream_result` same as OpenAI.
3. `_enrich_payload_with_direct_url` adds `url` field if extractable.
4. If `"error"` in payload: `_build_gemini_error_response_from_handler`.
5. Else: `_build_gemini_success_payload` builds Gemini candidates structure.

**Success shape**: `{"candidates": [{"content": {"role": "model", "parts": [...]}, "finishReason": "STOP", "index": 0}], "modelVersion": "..."}`.

**Error shape**: `{"error": {"code": ..., "message": ..., "status": ...}}`.

**Handler-uninitialized**: `HTTPException(500)` caught by `except HTTPException`,
returned as `JSONResponse(500, _build_gemini_error_payload(500, ...))`.

**Handler exception**: `JSONResponse(500, _build_gemini_error_payload(500, str(exc)))`.

### Finish-Reason Mapping

`_normalize_finish_reason` maps OpenAI finish reasons to Gemini:
- `"stop"` → `"STOP"`
- `"length"` → `"MAX_TOKENS"`
- `"content_filter"` → `"SAFETY"`
- Anything else → `"STOP"`

Non-streaming routes always set `"finishReason": "STOP"` in
`_build_gemini_success_payload`.

### Recommended First Non-Streaming Test Slice

1. OpenAI text success (no images, known model, stream=False).
2. Gemini text success (no images, known model).
3. Handler uninitialized for both routes.
4. Handler yields error JSON for both routes.

---

## Streaming Analysis

### OpenAI Streaming (`create_chat_completion`, `stream=True`)

1. `_normalize_openai_request` extracts prompt, images, model.
2. `StreamingResponse` wraps `_iterate_openai_stream(normalized, base_url)`.
3. `_iterate_openai_stream` is an async generator:
   - Calls `_ensure_generation_handler()`.
   - Iterates `handler.handle_generation(stream=True)`.
   - For each chunk starting with `"data: "`: yields as-is.
   - For other chunks: parses JSON, re-frames as `"data: {json}\n\n"`.
   - After handler exhausted: yields `"data: [DONE]\n\n"`.

**Response headers**: `Cache-Control: no-cache`, `Connection: keep-alive`,
`X-Accel-Buffering: no`.

**[DONE] behavior**: Always emitted as the final SSE event.

### Gemini Streaming (`stream_generate_content`)

1. `_normalize_gemini_request` extracts prompt, images, resolved model.
2. `StreamingResponse` wraps `_iterate_gemini_stream(normalized, model, base_url)`.
3. `_iterate_gemini_stream` is an async generator:
   - Calls `_ensure_generation_handler()`.
   - Iterates `handler.handle_generation(stream=True)`.
   - For `"data: "` chunks: strips prefix, skips `[DONE]`, parses JSON.
   - If `"error"` in payload: yields Gemini error event, **returns** (stops).
   - Otherwise: calls `_convert_openai_stream_chunk_to_gemini_event`.
   - Non-`"data:"` chunks are parsed and converted the same way.

**Termination**: No `[DONE]` event. Stream ends when handler is exhausted.

**Error during streaming**: Yielded as an SSE error event, then the generator
returns (stops iteration).

### Errors Before Streaming Begins

If normalization or `_ensure_generation_handler` raises before the
`StreamingResponse` is created, the error is caught by the outer
`except HTTPException` / `except Exception` and returned as a `JSONResponse`.

### Errors During Streaming

Once the `StreamingResponse` begins, errors from the handler are:
- OpenAI: Not specifically handled; would propagate to ASGI server.
- Gemini: Caught inside `_iterate_gemini_stream`, yielded as error event.

### Cancellation

`handle_generation` has an `except asyncio.CancelledError` block that logs,
records metrics, updates the request log, and re-raises. This cleanup runs
inside the handler, not the route layer.

### Direct body_iterator Consumption

For testing, the async generators `_iterate_openai_stream` and
`_iterate_gemini_stream` can be called directly and iterated with
`async for`. This avoids constructing a `StreamingResponse` entirely.
This is the recommended approach for Sprint 006E.

---

## Mutable-State Risks

| State | Mutation | Reset Strategy |
|-------|----------|---------------|
| `src.api.routes.generation_handler` | `set_generation_handler()` | Save/restore in setUp/tearDown |
| `MODEL_CONFIG` | Mutated at import by `_apply_veo_3_1_model_updates()` | Stable after import; do not mutate in tests |
| `GENERATION_REQUESTS_TOTAL` | `record_generation_result()` | Not called if handler is faked |
| `GENERATION_DURATION_SECONDS` | `record_generation_result()` | Not called if handler is faked |
| `debug_logger` | Logs to stdout/file | No state to reset |

### Isolation Rules for Tests

1. Always restore `generation_handler` after each test.
2. Never mutate `MODEL_CONFIG` in tests.
3. Do not assert on absolute Prometheus counter values.
4. Use a fresh `FakeGenerationHandler` instance per test to avoid state leakage.

---

## Recommended First Test Slice

See [GENERATION_ROUTE_MOCKING_PLAN.md](../GENERATION_ROUTE_MOCKING_PLAN.md)
for the full matrix. Summary:

### Priority 1

| # | Test | Route | Fake Behavior |
|---|------|-------|---------------|
| 1 | OpenAI non-stream text success | `create_chat_completion` | yield success JSON |
| 2 | Gemini non-stream text success | `generate_content` | yield success JSON |
| 3 | Handler uninitialized (OpenAI) | `create_chat_completion` | handler=None |
| 4 | Handler uninitialized (Gemini) | `generate_content` | handler=None |
| 5 | Handler error (OpenAI) | `create_chat_completion` | yield error JSON |
| 6 | Handler error (Gemini) | `generate_content` | yield error JSON |

### Priority 2

- Image output (OpenAI and Gemini).
- Video output (Gemini `fileData` parts).
- Streaming iteration (OpenAI `[DONE]`, Gemini conversion).
- `generationConfig`-based model resolution.

### Deferred

- Streaming cancellation, media URL retrieval, video continuation,
  real token/proxy/browser/captcha behavior, upstream network semantics.

---

## Commands and Results

### Baseline Verification

```
$ git status --short
(empty)

$ git log -5 --oneline
93cddf7 (HEAD -> main) test: characterize model catalog routes
48ff504 test: characterize route conversion helpers
76e0f27 docs(builder): add comprehensive builder rules for flow2api fork
a7f249c docs: document route test seam
9ae53cd test: add additional static fixture assertions

$ python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
Ran 215 tests in 0.083s
OK

$ python3 -c "import src.api.routes; print('src.api.routes import: OK')"
src.api.routes import: OK
```

---

## Confirmations

- **No generation route was invoked.** All analysis is source inspection only.
- **No runtime source was modified.** `git diff -- src` is empty.
- **No service was instantiated.** No `GenerationHandler`, `FlowClient`,
  `TokenManager`, `Database`, browser, captcha, proxy, or session service
  was created.
- **No FastAPI app was constructed.** No lifespan, no `TestClient`, no HTTP.
- **No network calls were made.**
- **No tests were added.**

---

## Files Created

| File | Purpose |
|------|---------|
| `docs/GENERATION_ROUTE_DEPENDENCY_MAP.md` | Route signatures, dependency chains, call graphs |
| `docs/GENERATION_ROUTE_MOCKING_PLAN.md` | Fake-handler interface, request construction, test matrix |
| `docs/SPRINTS/SPRINT-006D-mocked-generation-route-seam-discovery.md` | This document |

## Files Updated

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006D entries |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006D reference |
| `docs/SPRINTS/README.md` | Added Sprint 006D row |

---

## Final Status

**Completed.** All discovery objectives met. Documentation created.
No runtime source modified. No tests added. Existing 215 tests pass.
Ready for Sprint 006E (mocked generation route tests).
