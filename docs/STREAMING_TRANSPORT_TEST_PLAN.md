# Streaming Transport Test Plan

> **Sprint 006P — ASGI Send-Await Backpressure Seam Discovery**
> Sprint 006P discovered the ASGI send-await backpressure seam,
> compared six candidate approaches, confirmed via disposable probe
> that blocked send() deterministically prevents handler advancement,
> and recommended direct StreamingResponse invocation with ASGI
> spec_version "2.4" for the next implementation sprint. See
> [STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md](STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md)
> and
> [SPRINT-006P](SPRINTS/SPRINT-006P-asgi-send-await-backpressure-seam-discovery.md)
> for details.
> Sprint 006K implemented 6 direct ASGI send-loop tests using synthetic
> ASGI scope/receive/send callables, characterizing response-start timing,
> header encoding, byte encoding, body-message framing, [DONE] termination
> bytes, more_body flags, normal completion, and exception propagation.
> Sprint 006K.1 strengthened the successful OpenAI and Gemini tests with
> exact ASGI message sequence, exact content-body byte values, non-ASCII
> UTF-8 byte preservation (`Xin chào — 世界`), per-event body message
> separation, and header byte-type assertions.
> Sprint 006I discovered the streaming transport seams and proposed the test
> matrix for Sprint 006J. Sprint 006J implemented wrapper and body-iterator
> characterization tests. See
> [STREAMING_TRANSPORT_SEAM_DISCOVERY.md](STREAMING_TRANSPORT_SEAM_DISCOVERY.md),
> [SPRINT-006I](SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md),
> [SPRINT-006J](SPRINTS/SPRINT-006J-streaming-response-wrapper-body-iterator-characterization.md),
> and
> [SPRINT-006K](SPRINTS/SPRINT-006K-direct-asgi-streaming-response-send-loop-characterization.md)
> for the sprint context.
> Sprint 006N discovered the streaming disconnect and cancellation seam,
> compared six candidate approaches, confirmed determinism of coordinated
> receive-side design with gated handlers, and recommended direct
> StreamingResponse invocation with ASGI spec 2.0 for the next
> implementation sprint. See
> [STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md](STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md)
> and
> [SPRINT-006N](SPRINTS/SPRINT-006N-streaming-disconnect-cancellation-seam-discovery.md)
> for details.
> Sprint 006O implemented the recommended disconnect test: 1 OpenAI
> receive-side disconnect characterization test proving exactly one body
> sent before disconnect, CancelledError observed in handler, finally
> block ran, route iterator terminated, no [DONE] or more_body=False
> emitted. See
> [SPRINT-006O](SPRINTS/SPRINT-006O-receive-side-streaming-disconnect-characterization.md)
> and
> [test_streaming_response_disconnect_cancellation.py](../tests/compatibility/test_streaming_response_disconnect_cancellation.py)
> for the implementation.

---

## Purpose

This document specifies a small, focused test matrix for the next implementation
sprint. The matrix covers the streaming transport boundary: `StreamingResponse`
construction, header/media-type verification, generator iteration at the
transport level, and exception timing relative to response construction.

All tests are offline, deterministic, and use the same fake-handler approach
established in Sprint 006E, 006F, 006G, and 006H. No HTTP transport, TestClient,
FastAPI app, lifespan, or production services are involved.

---

## Recommended Seam

**Direct route function call plus direct `StreamingResponse.body_iterator` consumption.**

This seam provides:
- High isolation (no app, no lifespan, no TestClient)
- Sufficient coverage for transport-level assertions
- Deterministic, offline execution
- Consistency with existing test patterns (Sprint 006E–006H)

---

## Test Matrix

### Group 1: OpenAI Streaming Transport — Happy Path

**Route:** `create_chat_completion`
**Request:** `ChatCompletionRequest(model="text-model", messages=[{"role": "user", "content": "test"}], stream=True)`
**Patched globals:** `src.api.routes.generation_handler` → `FakeStreamingHandler`
**Invocation seam:** Direct function call with `api_key="test-key"`

**Tests:**

1. **test_openai_streaming_response_is_streaming_response**
   - Assert response is an instance of `StreamingResponse`
   - Verify `response.media_type == "text/event-stream"`
   - Verify `response.status_code == 200`

2. **test_openai_streaming_explicit_headers**
   - Verify `Cache-Control: no-cache` in headers
   - Verify `Connection: keep-alive` in headers
   - Verify `X-Accel-Buffering: no` in headers

3. **test_openai_streaming_content_type_includes_charset**
   - Verify `content-type` header includes `text/event-stream`
   - Verify `content-type` header includes `charset=utf-8`

4. **test_openai_streaming_body_iterator_yields_sse_frames**
   - Iterate `response.body_iterator` with `async for`
   - Verify each chunk is a string starting with `data: `
   - Verify final chunk is `data: [DONE]\n\n`

5. **test_openai_streaming_chunk_ordering**
   - Provide multiple chunks in `FakeStreamingHandler`
   - Verify chunks are yielded in the same order

6. **test_openai_streaming_handler_called_with_correct_arguments**
   - Verify `handler.handle_generation` is called with `stream=True`
   - Verify model, prompt, images, base_url_override, video_media_id are forwarded

**Explicit non-coverage:**
- HTTP transport (chunked encoding, connection handling)
- TestClient integration
- Proxy buffering and backpressure
- Client disconnect detection

---

### Group 2: Gemini Streaming Transport — Happy Path

**Route:** `stream_generate_content`
**Request:** `GeminiGenerateContentRequest(contents=[{"role": "user", "parts": [{"text": "test"}]}])`
**Patched globals:** `src.api.routes.generation_handler` → `FakeStreamingHandler`
**Invocation seam:** Direct function call with `model="text-model"`, `api_key="test-key"`

**Tests:**

1. **test_gemini_streaming_response_is_streaming_response**
   - Assert response is an instance of `StreamingResponse`
   - Verify `response.media_type == "text/event-stream"`
   - Verify `response.status_code == 200`

2. **test_gemini_streaming_explicit_headers**
   - Verify `Cache-Control: no-cache` in headers
   - Verify `Connection: keep-alive` in headers
   - Verify `X-Accel-Buffering: no` in headers

3. **test_gemini_streaming_content_type_includes_charset**
   - Verify `content-type` header includes `text/event-stream`
   - Verify `content-type` header includes `charset=utf-8`

4. **test_gemini_streaming_body_iterator_yields_gemini_events**
   - Iterate `response.body_iterator` with `async for`
   - Verify each chunk is a Gemini-shaped SSE frame
   - Verify no `[DONE]` sentinel is emitted

5. **test_gemini_streaming_handler_called_with_correct_arguments**
   - Verify `handler.handle_generation` is called with `stream=True`
   - Verify model, prompt, images, base_url_override, video_media_id are forwarded

**Explicit non-coverage:**
- HTTP transport (chunked encoding, connection handling)
- TestClient integration
- Proxy buffering and backpressure
- Client disconnect detection

---

### Group 3: OpenAI Streaming Transport — Exception Before First Chunk

**Route:** `create_chat_completion`
**Request:** Same as Group 1
**Patched globals:** `generation_handler = None` (triggers `_ensure_generation_handler` to raise)
**Invocation seam:** Direct function call

**Tests:**

1. **test_openai_streaming_handler_uninitialized_raises_http_exception**
   - Verify `HTTPException(status_code=500, detail="Generation handler not initialized")` is raised
   - Verify no `StreamingResponse` is constructed
   - Verify exception occurs before HTTP response start

**Explicit non-coverage:**
- HTTP error response shape (framework behavior)
- Error response conversion (already tested in Sprint 006E)

---

### Group 4: Gemini Streaming Transport — Exception Before First Chunk

**Route:** `stream_generate_content`
**Request:** Same as Group 2
**Patched globals:** `generation_handler = None`
**Invocation seam:** Direct function call

**Tests:**

1. **test_gemini_streaming_handler_uninitialized_returns_error_response**
   - Verify exception is caught by the route's try/except
   - Verify response is a `JSONResponse` with Gemini error shape
   - Verify `status_code == 500`
   - Verify `error.code == 500`
   - Verify `error.status == "INTERNAL"`

**Explicit non-coverage:**
- HTTP transport
- Error response conversion (already tested in Sprint 006E)

---

### Group 5: OpenAI Streaming Transport — Partial Output Then Exception

**Route:** `create_chat_completion`
**Request:** Same as Group 1
**Patched globals:** `FakeFailingHandler(yield_values=[chunk1], error=RuntimeError("synthetic failure"))`
**Invocation seam:** Direct function call, iterate `response.body_iterator`

**Tests:**

1. **test_openai_streaming_partial_output_then_exception**
   - Verify first chunk is yielded successfully
   - Verify second iteration raises `RuntimeError`
   - Verify no `[DONE]` is emitted
   - Verify exception type and message are preserved

**Explicit non-coverage:**
- HTTP partial response
- Client disconnect
- Connection cleanup

---

### Group 6: Gemini Streaming Transport — Partial Output Then Exception

**Route:** `stream_generate_content`
**Request:** Same as Group 2
**Patched globals:** `FakeFailingHandler(yield_values=[chunk1], error=RuntimeError("synthetic failure"))`
**Invocation seam:** Direct function call, iterate `response.body_iterator`

**Tests:**

1. **test_gemini_streaming_partial_output_then_exception**
   - Verify first chunk is yielded successfully
   - Verify second iteration raises `RuntimeError`
   - Verify no synthetic error event is emitted
   - Verify exception type and message are preserved

**Explicit non-coverage:**
- HTTP partial response
- Client disconnect
- Connection cleanup

---

## Test Count Estimate

| Group | Tests | Description |
|-------|-------|-------------|
| Group 1 | 6 | OpenAI streaming happy path |
| Group 2 | 5 | Gemini streaming happy path |
| Group 3 | 1 | OpenAI exception before first chunk |
| Group 4 | 1 | Gemini exception before first chunk |
| Group 5 | 1 | OpenAI partial output then exception |
| Group 6 | 1 | Gemini partial output then exception |
| **Total** | **15** | |

---

## Request Construction

### OpenAI Streaming Request

```python
from src.core.models import ChatCompletionRequest, ChatMessage

request = ChatCompletionRequest(
    model="text-model",
    messages=[ChatMessage(role="user", content="test prompt")],
    stream=True,
)
```

### Gemini Streaming Request

```python
from src.core.models import GeminiGenerateContentRequest, GeminiContent, GeminiPart

request = GeminiGenerateContentRequest(
    contents=[
        GeminiContent(
            role="user",
            parts=[GeminiPart(text="test prompt")],
        )
    ]
)
```

### Raw Request Construction

Both routes require a `raw_request: Request` parameter for base URL extraction.
Construct a minimal `Request` object:

```python
from starlette.requests import Request

scope = {
    "type": "http",
    "method": "POST",
    "path": "/v1/chat/completions",
    "headers": [
        (b"host", b"localhost:8000"),
    ],
}
raw_request = Request(scope)
```

---

## Fake Handler

Reuse the `FakeStreamingHandler` and `FakeFailingHandler` classes from
Sprint 006G and 006H. These handlers:
- Accept a list of `yield_values` to yield during iteration
- Accept an optional `error` exception to raise after yielding
- Record all calls for assertion
- Do not make network calls, read credentials, or touch services

---

## Patching Strategy

Patch `src.api.routes.generation_handler` via `unittest.mock.patch.object`:

```python
from unittest.mock import patch

with patch("src.api.routes.generation_handler", fake_handler):
    response = await create_chat_completion(request, raw_request, api_key="test-key")
    # iterate response.body_iterator
```

For exception-before-first-chunk tests, set `generation_handler = None`:

```python
with patch("src.api.routes.generation_handler", None):
    with pytest.raises(HTTPException) as exc_info:
        await create_chat_completion(request, raw_request, api_key="test-key")
    assert exc_info.value.status_code == 500
```

---

## Explicit Non-Coverage

The following behaviors are explicitly not covered in this test matrix:

- **HTTP transport:** Chunked encoding, connection handling, ASGI server behavior
- **TestClient integration:** Full HTTP request/response cycle
- **Proxy buffering:** nginx, Cloudflare, and other proxy behavior
- **Backpressure:** Flow control and buffer management
- **Client disconnect:** Detection and propagation — Sprint 006N discovered
  the disconnect seam and recommended an approach for the next sprint.
  Sprint 006O implemented 1 receive-side disconnect characterization test.
  See
  [SPRINT-006O](SPRINTS/SPRINT-006O-receive-side-streaming-disconnect-characterization.md)
- **Lifespan behavior:** Startup/shutdown handlers
- **Production services:** Database, token manager, flow client, etc.
- **Network calls:** Upstream service interaction
- **Media retrieval:** Image/video download and conversion
- **Authentication:** Not exercised. Direct route calls supply the already-resolved `api_key` dependency parameter explicitly.
- **Request validation:** Pydantic validation (framework behavior)

---

## Deferred Behaviors

The following behaviors are deferred to future sprints:

- **Full HTTP transport tests** using TestClient or ASGI transport
- **Proxy and buffering behavior** with real or mocked proxies
- **Client disconnect handling** and cancellation — Sprint 006N discovered
  the seam and recommended direct StreamingResponse invocation with ASGI
  spec 2.0 and gated handlers. Sprint 006O implemented the recommended
  test. See
  [STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md](STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md)
  and
  [SPRINT-006O](SPRINTS/SPRINT-006O-receive-side-streaming-disconnect-characterization.md)
- **Backpressure and flow control** — Sprint 006P discovered the ASGI
  send-await backpressure seam and recommended direct StreamingResponse
  invocation with ASGI spec_version "2.4" for the next implementation
  sprint. See
  [STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md](STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md)
  and
  [SPRINT-006P](SPRINTS/SPRINT-006P-asgi-send-await-backpressure-seam-discovery.md)
- **Production integration tests** with lifespan and services

---

## Verification Commands

After implementing the tests in Sprint 006J, verify with:

```bash
# New test file (Sprint 006J)
python3 -m unittest tests.compatibility.test_streaming_response_wrappers -v
# Expected: 8 tests, OK

# Sprint 006K ASGI send-loop tests
python3 -m unittest tests.compatibility.test_streaming_response_asgi_send_loop -v
# Expected: 6 tests, OK

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Expected: 299 tests
# 299 = Static fixture compatibility suite after Sprint 005D (53)
#       + Sprint 006B (67) + Sprint 006C (95)
#       + Sprint 006E (6) + Sprint 006F (5) + Sprint 006G (18) + Sprint 006H (41)
#       + Sprint 006J (8) + Sprint 006K (6)
# Calculation: 53 + 67 + 95 + 6 + 5 + 18 + 41 + 8 + 6 = 299

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Expected: OK

# No runtime source changes
git diff -- src
# Expected: (no output)
```

---

## Confirmation

- Sprint 006J: No routes were invoked during test execution; body_iterator consumed directly.
- Sprint 006K: `StreamingResponse.__call__` was invoked with synthetic ASGI callables; no FastAPI app, TestClient, HTTPX, or HTTP transport was used. Sprint 006K.1 strengthened assertions to exact message sequences, byte values, and UTF-8 encoding proof.
- No production services were instantiated.
- No network calls were made.
- No runtime source was modified.
