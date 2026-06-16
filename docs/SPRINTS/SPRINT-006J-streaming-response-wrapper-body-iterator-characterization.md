# Sprint 006J — StreamingResponse Wrapper and Body-Iterator Characterization

## Status

✅ Completed

## Scope

Characterize streaming route-to-StreamingResponse wiring and direct
body-iterator behavior for OpenAI (`create_chat_completion`) and Gemini
(`stream_generate_content`) without FastAPI app construction, TestClient,
ASGI transport, `StreamingResponse.__call__`, or network activity.

## Approach

### Seam

**Direct StreamingResponse wrapper and body-iterator characterization.**

Direct route function calls supply the already-resolved `api_key` dependency
parameter explicitly. Authentication behavior is not exercised.

### Source Inspection

All findings are from source inspection of `src/api/routes.py` and direct
Python function calls with fake handlers.

No `StreamingResponse.__call__`, ASGI send/receive, `http.response.start`,
`http.response.body`, TestClient, HTTPX, FastAPI app construction, lifespan,
dependency override, authentication, cancellation, disconnect, backpressure,
buffering, background task, server/proxy, or network behavior was exercised.

## Tests Created

**File:** `tests/compatibility/test_streaming_response_wrappers.py`

**Test count:** 8 tests across 6 test classes

### Test Cases

1. **test_openai_response_construction_and_deferred_execution**
   - Verifies `StreamingResponse` type, `status_code == 200`,
     `media_type == "text/event-stream"`, explicit headers
     (`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`),
     `body_iterator` existence, and content-type charset.
   - Confirms handler has NOT been called before body consumption (deferred execution).

2. **test_openai_successful_body_iteration**
   - Consumes `response.body_iterator` with multiple chunks.
   - Verifies OpenAI SSE sequence (each chunk starts with `data: `).
   - Verifies final chunk is exactly `data: [DONE]\n\n` (appears once and last).
   - Verifies handler called exactly once with stable argument forwarding.

3. **test_openai_handler_unavailable**
   - Patches `generation_handler=None`.
   - Route call succeeds, returns `StreamingResponse`.
   - First body iteration raises `HTTPException(status_code=500, detail="Generation handler not initialized")`.
   - Confirms `_ensure_generation_handler()` is called inside the generator,
     not during route execution.

4. **test_openai_partial_output_then_exception**
   - Fake handler yields one chunk then raises `RuntimeError`.
   - Response is constructed successfully.
   - First body item is yielded correctly.
   - Next iteration raises the original `RuntimeError`.
   - No `[DONE]` or synthesized error event is emitted.

5. **test_gemini_response_construction_and_deferred_execution**
   - Verifies `StreamingResponse` type, `status_code == 200`,
     `media_type == "text/event-stream"`, explicit headers,
     `body_iterator` existence, and content-type charset.
   - Confirms handler has NOT been called before body consumption.

6. **test_gemini_successful_body_iteration**
   - Consumes `response.body_iterator` with multiple chunks.
   - Verifies Gemini event sequence (each chunk starts with `data: `).
   - Verifies no OpenAI `[DONE]` sentinel is emitted.
   - Verifies handler called exactly once with stable argument forwarding.

7. **test_gemini_handler_unavailable**
   - Patches `generation_handler=None`.
   - Route call succeeds, returns `StreamingResponse`.
   - First body iteration raises `HTTPException(status_code=500, detail="Generation handler not initialized")`.
   - Route's try/except does not catch exceptions from generator iteration.

8. **test_gemini_partial_output_then_exception**
   - Fake handler yields one chunk then raises `RuntimeError`.
   - Response is constructed successfully.
   - First body item is a valid Gemini event (contains `candidates` structure).
   - Next iteration raises the original `RuntimeError`.
   - No synthetic error event or `[DONE]` is emitted.

## Route Signatures Tested

### OpenAI Streaming: `create_chat_completion`

```python
@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
):
```

### Gemini Streaming: `stream_generate_content`

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

## Response Object Fields

Both routes construct identical `StreamingResponse` objects:

| Field | Value |
|-------|-------|
| `status_code` | 200 (default) |
| `media_type` | `"text/event-stream"` |
| `Cache-Control` | `"no-cache"` |
| `Connection` | `"keep-alive"` |
| `X-Accel-Buffering` | `"no"` |
| `content-type` | `"text/event-stream; charset=utf-8"` (Starlette appends charset) |

## Deferred Execution Behavior

**Handler execution is deferred until body iteration.**

- Route call constructs `StreamingResponse` with the generator stored as `body_iterator`.
- `_ensure_generation_handler()` is called inside `_iterate_openai_stream` or `_iterate_gemini_stream`.
- The generator is not executed until `async for chunk in response.body_iterator`.
- No `__anext__` is called during `StreamingResponse.__init__`.

## Body-Iterator Contract

### OpenAI

- Each chunk starts with `data: ` prefix.
- Final chunk is exactly `data: [DONE]\n\n` (appears once, is last).
- Chunks are raw JSON wrapped in SSE framing by `_iterate_openai_stream`.
- Handler called with `stream=True`, `images=None` (for text-only), `video_media_id=None`.

### Gemini

- Each chunk starts with `data: ` prefix.
- No `[DONE]` sentinel is emitted.
- Chunks are Gemini-shaped events (contain `candidates` structure).
- Handler called with `stream=True`, `images=None` (for text-only), `video_media_id=None`.

## Handler-Unavailable Timing

**Both routes exhibit identical timing:**

1. Route call succeeds, returns `StreamingResponse`.
2. First body iteration raises `HTTPException(status_code=500, detail="Generation handler not initialized")`.
3. The route's try/except (in `stream_generate_content`) does not catch exceptions from generator iteration.
4. No `[DONE]` or synthetic error event is emitted.

## Partial-Output Exception Behavior

**Both routes exhibit identical behavior:**

1. Response is constructed successfully.
2. First chunk is yielded correctly.
3. Next iteration raises the original exception (preserves type and message).
4. No `[DONE]` or synthetic error event is emitted before the exception.
5. Exception propagates directly to the caller (no try/except wrapping in generator).

## Dependency Parameter Framing

Direct route calls supply the already-resolved `api_key` dependency parameter
explicitly:

```python
await create_chat_completion(request, raw_request, api_key="test-key")
await stream_generate_content(model=..., request=..., raw_request=..., alt=None, api_key="test-key")
```

Authentication behavior is not exercised. The `api_key` parameter is not
forwarded to the handler or any service.

## Explicit Absence of HTTP/ASGI Transport Coverage

The following behaviors were NOT exercised:

- `StreamingResponse.__call__`
- ASGI `send`/`receive`
- `http.response.start` or `http.response.body`
- TestClient or HTTPX
- FastAPI app construction
- Lifespan startup/shutdown
- Dependency override
- Authentication testing
- Cancellation, disconnect, backpressure, buffering
- Background tasks
- Server or proxy behavior
- Network calls
- Media retrieval

## Remaining Gaps

- Full HTTP transport (chunked encoding, connection handling, ASGI server)
- Proxy buffering and backpressure
- Client disconnect detection and propagation
- TestClient integration
- Cancellation behavior
- Real HTTP header emission

## Verification

```bash
# New test file
python3 -m unittest tests.compatibility.test_streaming_response_wrappers -v
# Result: Ran 8 tests in 0.010s — OK

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Result: Ran 293 tests in 0.116s — OK (285 existing + 8 new)

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Result: OK

# No runtime source changes
git diff -- src
# Result: (no output)

# No whitespace errors
git diff --check
# Result: (no output)

# Final status
git status --short
# Result: worktree contains only intended Sprint 006J changes and no unrelated changes

git diff --stat
# Result: files changed for new test, sprint doc, and updated project docs
```

## Confirmation

- No `StreamingResponse.__call__` was invoked.
- No ASGI send/receive was used.
- No `http.response.start` or `http.response.body` was executed.
- No TestClient or HTTPX was used.
- No FastAPI app was constructed.
- No lifespan was run.
- No production services were instantiated.
- No dependencies were overridden.
- No authentication was tested.
- No network calls were made.
- No media was retrieved.
- No runtime source (`src/`) was modified.
- No fixtures were added.
- No dependencies were added.
- No commits or pushes were performed.

## Documents Created

| File | Purpose |
|------|---------|
| `tests/compatibility/test_streaming_response_wrappers.py` | 8 StreamingResponse wrapper and body-iterator tests |
| `docs/SPRINTS/SPRINT-006J-streaming-response-wrapper-body-iterator-characterization.md` | This sprint document |

## Documents Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006J to sprint history, current sprint, what-is-not-yet-done |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006J streaming response wrapper characterization note |
| `docs/SPRINTS/README.md` | Added Sprint 006J to sprint index |
| `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | Added Sprint 006J implementation note |
| `docs/STREAMING_TRANSPORT_SEAM_DISCOVERY.md` | Fixed auth-bypass wording to dependency-parameter framing |
| `docs/SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md` | Fixed auth-bypass wording, clean-worktree wording |

## What This Sprint Does NOT Cover

- `StreamingResponse.__call__` invocation
- ASGI send/receive
- HTTP transport (chunked encoding, connection handling)
- TestClient or HTTPX integration
- FastAPI app construction
- Dependency override
- Authentication testing
- Lifespan execution
- Cancellation, disconnect, backpressure, buffering
- Background tasks
- Server or proxy behavior
- Network calls
- Media retrieval
- Runtime source modification
- New dependencies
- Commits or pushes

## Recommendation for Next Sprint

The next sprint should consider:

1. **TestClient integration** — Construct a minimal test-local FastAPI app
   with dependency override, use TestClient to verify full HTTP transport
   (status, headers, chunked encoding).

2. **Cancellation behavior** — Test client disconnect propagation and
   generator cleanup when the connection is dropped mid-stream.

3. **Backpressure and buffering** — Characterize behavior when the client
   reads slower than the generator produces.

4. **Exception-to-HTTP-error conversion** — Verify how FastAPI/Starlette
   converts generator exceptions to HTTP error responses (if at all after
   response start).

All tests are offline, deterministic, and consistent with the existing test
patterns established in Sprint 006E–006I.
