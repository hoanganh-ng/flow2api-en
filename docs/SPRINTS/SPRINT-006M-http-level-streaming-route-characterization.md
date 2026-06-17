# Sprint 006M — HTTP-Level Streaming Route Characterization

| Field | Value |
|-------|-------|
| Sprint ID | 006M |
| Type | Implementation (tests) |
| Predecessor | Sprint 006L |
| Status | Completed |

---

## 1. Objective

Implement the first HTTP-level streaming route characterization tests using
the seam recommended by Sprint 006L: a test-local FastAPI application with
`routes.router`, a dependency override for `verify_api_key_flexible`, a
patched fake generation handler, and Starlette `TestClient`.

These tests exercise the streaming generation routes through the full HTTP
request path — FastAPI routing, Pydantic validation, dependency injection,
`StreamingResponse` construction, and TestClient buffering — while remaining
fully offline and deterministic.

---

## 2. Scope

### In scope

- Build a test-local `FastAPI()` application (no lifespan).
- Include only `src.api.routes.router`.
- Override `verify_api_key_flexible` with a fixed deterministic test value.
- Use `TestClient` (fully buffered response).
- Patch `src.api.routes.generation_handler` with an offline deterministic
  fake handler.
- Add exactly two tests:
  1. OpenAI successful HTTP-level streaming response
  2. Gemini successful HTTP-level streaming response
- Assert status codes, SSE headers, fully buffered SSE body content,
  event ordering, termination behavior, and handler call arguments.
- Include non-ASCII content (`Xin chào — 世界`) in both tests.

### Out of scope

- Runtime source changes
- Authentication 401 tests
- Request-validation 422 tests
- Production lifespan
- `src.main.app` import
- Database or production services
- Upstream network calls
- Browser, captcha, token, session, proxy, or media operations
- Client disconnect
- Cancellation
- Backpressure
- Proxy buffering
- TCP or transfer-encoding behavior
- Live Uvicorn/socket server
- Dependency upgrades
- More than two tests

---

## 3. Test-Local Application Construction

```python
from fastapi import FastAPI
from starlette.testclient import TestClient

import src.api.routes as routes_module
from src.api.routes import router
from src.core.auth import verify_api_key_flexible

def _make_test_app() -> FastAPI:
    app = FastAPI()  # no lifespan
    app.include_router(router)
    app.dependency_overrides[verify_api_key_flexible] = lambda: "test-api-key"
    return app
```

Key characteristics:

- `FastAPI()` is created without a lifespan parameter.
- `src.main` is never imported.
- `routes.router` is a plain `APIRouter()` with no lifespan, middleware,
  or state.
- The dependency override completely replaces `verify_api_key_flexible`.
  No `AuthManager`, `config.api_key`, or database state is consulted.

---

## 4. Dependency Override and Cleanup Strategy

The dependency override is set in `setUp` and cleared in `tearDown`:

```python
def setUp(self):
    self.app = _make_test_app()
    self.client = TestClient(self.app)
    self.patcher = patch.object(routes_module, "generation_handler", fake_handler)
    self.patcher.start()

def tearDown(self):
    self.patcher.stop()
    self.app.dependency_overrides.clear()
```

- `unittest.mock.patch.object` ensures `generation_handler` is restored
  even if a test fails.
- `app.dependency_overrides.clear()` in `tearDown` prevents global state
  leakage between tests.
- Each test creates a fresh `FastAPI()` and `TestClient` instance.

---

## 5. Fake Handler Behavior

`FakeStreamingHandler` is an async-generator-based class matching the
production `handle_generation` signature:

- Yields deterministic raw JSON strings (OpenAI format).
- Records all call arguments for assertions.
- Does not make network calls, read credentials, touch a database,
  create browser/captcha/session services, use proxy behavior, or
  retrieve media.

---

## 6. Test 1: OpenAI HTTP-Level Streaming Response

**Endpoint:** `POST /v1/chat/completions` with `stream: true`

**Request body:**
```json
{
  "model": "gemini-2.0-flash-exp",
  "messages": [{"role": "user", "content": "Xin chào — 世界"}],
  "stream": true
}
```

**Fake handler yields:** 3 raw JSON chunks (2 text deltas + 1 finish reason)

**Assertions:**
- Status code: 200
- `content-type`: contains `text/event-stream` and `charset=utf-8`
- `cache-control`: `no-cache`
- `connection`: `keep-alive`
- `x-accel-buffering`: `no`
- Fully buffered body contains exactly 4 SSE events in order:
  1. `data: {chunk1}\n\n` (content: "Xin chào")
  2. `data: {chunk2}\n\n` (content: " — 世界")
  3. `data: {finish_chunk}\n\n` (finish_reason: "stop")
  4. `data: [DONE]\n\n`
- Each event is separated by a blank line (`\n\n`)
- Final event is exactly `data: [DONE]\n\n`
- Nothing follows `[DONE]`
- Handler called exactly once with expected model, prompt, stream=True,
  images=None, video_media_id=None

---

## 7. Test 2: Gemini HTTP-Level Streaming Response

**Endpoint:** `POST /v1beta/models/{model}:streamGenerateContent`

**Request body:**
```json
{
  "contents": [{
    "role": "user",
    "parts": [{"text": "Xin chào — 世界"}]
  }]
}
```

**Fake handler yields:** 3 raw JSON chunks (OpenAI format, converted to Gemini events)

**Assertions:**
- Status code: 200
- Same SSE headers as OpenAI test
- Fully buffered body contains exactly 3 Gemini SSE events:
  1. Text event: `candidates[0].content.parts[0].text == "Xin chào"`, `modelVersion` present
  2. Text event: `candidates[0].content.parts[0].text == " — 世界"`, `modelVersion` present
  3. Finish event: `candidates[0].finishReason == "STOP"`, no `content` key
- All events have `candidates[0].content.role == "model"` (for text events)
- `modelVersion` matches the request model in all events
- No `data: [DONE]` sentinel anywhere in the body (Gemini contract)
- Handler called exactly once with expected arguments

---

## 8. Response Buffering Confirmation

`TestClient` fully buffers the response body before delivery:

- `_TestClientTransport` collects all `http.response.body` messages into
  `io.BytesIO()`, then wraps the complete buffer as `httpx.ByteStream`.
- The entire response body is delivered as a single chunk.
- `response.text` and `response.content` return the fully reassembled body.
- `client.stream()`, `iter_bytes()`, and `iter_lines()` are not genuinely
  incremental — they operate on the already-buffered body.

These tests use `response.text` for assertions. No claim is made that
`client.stream()`, `iter_bytes()`, or `iter_lines()` demonstrate
incremental delivery.

---

## 9. Deliverables

| Deliverable | Status |
|-------------|--------|
| tests/compatibility/test_http_streaming_routes.py | Created |
| docs/SPRINTS/SPRINT-006M-http-level-streaming-route-characterization.md | Created |
| docs/PROJECT_STATE.md updated | Updated |
| docs/SPRINTS/README.md updated | Updated |
| docs/TEST_HARNESS_PLAN.md updated | Updated |
| docs/HTTP_STREAMING_TEST_SEAM_DISCOVERY.md updated | Updated |
| No src/ changes | Confirmed |
| No requirements.txt/pyproject.toml changes | Confirmed |

---

## 10. Verification

```
.venv/bin/python3 -m unittest tests.compatibility.test_http_streaming_routes -v
# → 2 tests, OK

.venv/bin/python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# → 301 tests, OK

git diff -- src
# → no output

git diff -- requirements.txt pyproject.toml
# → no output

git diff --check
# → no output
```

---

## 11. Explicitly Deferred

The following remain out of scope for this sprint:

- Authentication 401 characterization
- Request-validation 422 characterization
- Original ASGI body-message boundaries (covered by Sprint 006K/006K.1)
- True incremental client delivery (impossible with current transports)
- Client disconnect behavior
- Cancellation propagation
- Backpressure
- Proxy buffering
- TCP or transfer-encoding behavior
- Production lifespan behavior
- Async client testing (Candidate B from Sprint 006L)
- `spec_version` manipulation (Candidate C from Sprint 006L)
