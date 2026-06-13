# Sprint 006E — Mocked Non-Streaming Generation Route Tests

## Goal

Add the smallest safe mocked tests for OpenAI and Gemini non-streaming
generation routes. Cover text success, handler-uninitialized behavior, and
deterministic handler-error conversion for each API shape.

---

## Scope

Six test cases using direct Python route-function calls with a fake handler:

1. OpenAI non-streaming text success
2. OpenAI handler uninitialized
3. OpenAI deterministic handler error
4. Gemini non-streaming text success
5. Gemini handler uninitialized
6. Gemini deterministic handler error

---

## Route Functions Tested

### `create_chat_completion` (OpenAI)

```python
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
) -> JSONResponse | StreamingResponse
```

Path: `POST /v1/chat/completions`

### `generate_content` (Gemini)

```python
async def generate_content(
    model: str,
    request: GeminiGenerateContentRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
) -> JSONResponse
```

Paths: `POST /v1beta/models/{model}:generateContent`,
`POST /models/{model}:generateContent`

---

## Fake-Handler Interface

A test-local `FakeGenerationHandler` class implements only the async-generator
contract for `handle_generation`:

```python
class FakeGenerationHandler:
    def __init__(self, yield_value: str = ""):
        self._yield_value = yield_value
        self.calls: list[dict] = []

    async def handle_generation(
        self,
        model: str,
        prompt: str,
        images=None,
        stream: bool = False,
        base_url_override=None,
        video_media_id=None,
    ):
        self.calls.append({...})
        yield self._yield_value
```

### Yielded Formats

| Scenario | Yielded String |
|----------|---------------|
| Success | `json.dumps({"choices": [{"message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}]})` |
| Error | `json.dumps({"error": {"message": "...", "type": "server_error", "code": "generation_failed", "status_code": 500}})` |

The fake handler does not make network calls, read credentials, touch a
database, create browser/captcha/session services, use proxy behavior,
retrieve media, or imitate the full production handler.

---

## Patch Point

`src.api.routes.generation_handler` — patched via
`unittest.mock.patch.object(routes_module, "generation_handler", fake_handler)`.

The `patch.object` context manager guarantees restoration after each test.

---

## Request Construction

### OpenAI (Minimal Text-Only)

```python
ChatCompletionRequest(
    model="gemini-3.0-pro-image-landscape",
    messages=[ChatMessage(role="user", content="Describe a sunset over the ocean")],
    stream=False,
)
```

### Gemini (Minimal Text-Only)

```python
GeminiGenerateContentRequest(
    contents=[GeminiContent(
        role="user",
        parts=[GeminiPart(text="Describe a sunset over the ocean")]
    )]
)
```

### Synthetic Starlette Request

```python
scope = {
    "type": "http", "method": "POST", "path": "/v1/chat/completions",
    "headers": [(b"host", b"test.local")],
    "query_string": b"", "server": ("test.local", 80), "scheme": "http",
}
raw_request = Request(scope)
```

### API Key Parameter

`api_key="test-key"` is passed as a keyword argument to satisfy the function
signature. This supplies the already-resolved dependency parameter.
Authentication behavior is not exercised.

---

## Test Cases

### 1. OpenAI Non-Streaming Text Success

- Calls `create_chat_completion` with `stream=False`.
- Fake handler yields OpenAI-format success JSON.
- **Assertions:**
  - Response is `JSONResponse`, status 200.
  - Body has `choices[0].message.content` matching the fake text.
  - `finish_reason` is `"stop"`.
  - Exactly one handler call.
  - Model passed correctly, `stream=False`, prompt contains synthetic input.
  - No media data introduced (`images=None`, `video_media_id=None`).

### 2. OpenAI Handler Uninitialized

- Patches `generation_handler` to `None`.
- Calls `create_chat_completion` with valid input.
- **Assertions:**
  - `HTTPException` raised with `status_code=500`.
  - Detail contains `"not initialized"`.

### 3. OpenAI Deterministic Handler Error

- Fake handler yields error JSON with `status_code=502`.
- Calls `create_chat_completion`.
- **Assertions:**
  - Response is `JSONResponse`, status 502.
  - Body contains `error.message` and `error.status_code`.
  - Exactly one handler call.

### 4. Gemini Non-Streaming Text Success

- Calls `generate_content` with model path param and text-only contents.
- Fake handler yields OpenAI-format success JSON (handler always yields OpenAI format).
- **Assertions:**
  - Response is `JSONResponse`, status 200.
  - Body has `candidates[0].content.parts[0].text` matching fake text.
  - `finishReason` is `"STOP"`, `index` is 0, `content.role` is `"model"`.
  - `modelVersion` matches the resolved model.
  - No OpenAI `[DONE]` sentinel in response body.
  - Exactly one handler call.
  - Model, non-streaming mode, prompt, and no-media assertions same as OpenAI.

### 5. Gemini Handler Uninitialized

- Patches `generation_handler` to `None`.
- Calls `generate_content` with valid input.
- **Assertions:**
  - Response is `JSONResponse` (Gemini route catches `HTTPException`).
  - Status 500.
  - Body has `error.code=500`, `error.status="INTERNAL"`.
  - Message contains `"not initialized"`.

### 6. Gemini Deterministic Handler Error

- Fake handler yields error JSON with `status_code=503`.
- Calls `generate_content`.
- **Assertions:**
  - Response is `JSONResponse`, status 503.
  - Body has Gemini error shape: `error.code=503`, `error.status="UNAVAILABLE"`.
  - `error.message` matches the fake error message.
  - Exactly one handler call.

---

## Observed Contracts

### Success Contracts

**OpenAI non-streaming success:**
- Response: `JSONResponse` with status 200.
- Body: parsed handler JSON passed through directly.
- `_get_error_status_code` returns 200 when no `error` key is present.

**Gemini non-streaming success:**
- Response: `JSONResponse` with status 200.
- Body: Gemini candidates structure built from handler output.
- `candidates[0].finishReason` is always `"STOP"` for non-streaming.
- `candidates[0].content.role` is always `"model"`.
- `modelVersion` is the resolved model name.
- For text-only output, `parts` contains a single `{"text": "..."}` entry.

### Handler-Uninitialized Contracts

**OpenAI:**
- `_ensure_generation_handler()` raises `HTTPException(500, "Generation handler not initialized")`.
- Re-raised by `except HTTPException: raise` in the outer try/except.
- The caller (FastAPI framework) would convert this to a 500 response.

**Gemini:**
- Same `HTTPException(500)` is raised.
- Caught by `except HTTPException as exc` in the Gemini route.
- Converted to `JSONResponse(500, _build_gemini_error_payload(500, ...))`.
- Error payload: `{"error": {"code": 500, "message": "...", "status": "INTERNAL"}}`.

### Handler-Error Conversion Contracts

**OpenAI:**
- Handler yields error JSON: `{"error": {"message": ..., "status_code": N}}`.
- `_parse_handler_result` parses the JSON.
- `_build_openai_json_response` creates `JSONResponse(content=payload, status_code=N)`.
- Error body is passed through without modification.

**Gemini:**
- Same handler error JSON.
- `_get_error_status_code` extracts `N` from `error.status_code`.
- `_build_gemini_error_response_from_handler` builds Gemini error shape.
- `GEMINI_STATUS_MAP` maps HTTP status to Gemini status string:
  - 500 → `INTERNAL`, 502 → `UNAVAILABLE`, 503 → `UNAVAILABLE`, etc.

---

## Mutable-State Considerations

- `src.api.routes.generation_handler` is patched and restored per test via
  `patch.object` context manager.
- `MODEL_CONFIG` is read-only after import; not mutated.
- Prometheus generation counters are not reached by these tests:
  `record_generation_result` is defined in `src/core/monitoring.py` and called
  only within `src/services/generation_handler.py`, which is fully replaced
  by the fake handler. Source inspection of `src/api/routes.py` confirms
  the route functions themselves do not call `record_generation_result`.
  No exact cumulative metric values were asserted. Tests did not reset or
  replace the Prometheus registry. No metric side effects were observed.
  Route-level metric behavior was not a compatibility assertion in this sprint.
- No shared locks, semaphores, or config are replaced or mutated.

---

## Commands and Results

```
$ python3 -m unittest tests.compatibility.test_static_generation_fixtures -v
Ran 53 tests in 0.009s
OK

$ python3 -m unittest tests.compatibility.test_route_conversion_helpers -v
Ran 67 tests in 0.005s
OK

$ python3 -m unittest tests.compatibility.test_model_catalog_routes -v
Ran 95 tests in 0.073s
OK

$ python3 -m unittest tests.compatibility.test_generation_routes_non_streaming -v
Ran 6 tests in 0.012s
OK

$ python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
Ran 221 tests in 0.092s
OK

$ python3 -c "import src.api.routes; print('src.api.routes import: OK')"
src.api.routes import: OK

$ git diff -- src
(empty)

$ git diff --check
(empty)
```

---

## Limitations and Deferred Behavior

- **Streaming not tested.** `stream_generate_content` and `stream=True` paths
  are not exercised. No `StreamingResponse` is constructed.
- **Media/network helpers not reached.** Text-only requests avoid
  `_load_image_bytes_from_uri`, `retrieve_image_data`,
  `_append_openai_reference_images`, and `_build_image_parts_from_uri`.
- **Image/video output not tested.** Only text-only success paths are covered.
- **Authentication not tested.** `verify_api_key_flexible` dependency is
  satisfied by passing `api_key="test-key"` directly; no auth validation occurs.
- **`extend://` not tested.** No `video_media_id` is set in test inputs.
- **`generationConfig`-based model resolution not tested.**
- **Handler exceptions (vs. yielded errors) not tested.** Only the
  yield-error-json path is covered; a handler raising an exception is deferred.
- **Real `GenerationHandler`, `FlowClient`, `TokenManager`, `Database`,
  browser, captcha, proxy, and session services are not instantiated.**

---

## Confirmations

- **No runtime source was modified.** `git diff -- src` is empty.
- **No streaming route was invoked.** No `StreamingResponse` in test outputs.
- **No HTTP, upstream, database, media retrieval, browser, captcha, token,
  proxy, or session activity occurs.**
- **These are direct Python function calls, not HTTP tests.** No FastAPI app
  or TestClient is used.
- **All 215 existing compatibility tests remain passing.**
- **6 new mocked non-streaming tests pass.**
- **Combined suite: 221 tests passing.**

---

## Files Created

| File | Purpose |
|------|---------|
| `tests/compatibility/test_generation_routes_non_streaming.py` | 6 mocked non-streaming generation route tests |
| `docs/SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md` | This document |

## Files Updated

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006E entries |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006E reference |
| `docs/SPRINTS/README.md` | Added Sprint 006E row |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Added Sprint 006E route-level test status |

---

## Final Status

**Completed.** All six required test cases implemented and passing.
No runtime source modified. Existing 215 tests remain passing.
Combined suite: 221 tests passing. Ready to commit.
