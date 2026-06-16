# Streaming Transport Seam Discovery

> **Sprint 006I — HTTP Streaming Transport Seam Discovery**
> This document captures the discovery and analysis of safe seams for testing
> streaming route wrappers and `StreamingResponse` behavior without invoking
> generation routes, constructing `StreamingResponse` instances, or exercising
> HTTP transport.
> See [SPRINT-006I](SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md)
> for the full sprint context.

---

## Purpose

This document identifies and documents the narrowest safe seam for future
testing of streaming route wrappers (`create_chat_completion` and
`stream_generate_content`) and their `StreamingResponse` construction behavior.
The analysis covers:

- Streaming route function signatures and construction points
- Starlette `StreamingResponse` internal behavior
- Authentication dependency chains
- Exception timing relative to HTTP response start
- Headers and media types
- Candidate test seams with safety analysis
- One recommended seam for the next implementation sprint

All findings are from source inspection only. No routes were invoked, no
`StreamingResponse` was constructed or consumed, no HTTP transport was exercised,
and no runtime source was modified.

---

## 1. Streaming Route Functions

### 1.1 OpenAI Streaming: `create_chat_completion`

**Location:** `src/api/routes.py`, lines 850–889

**Signature:**
```python
@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
):
```

**Route path:** `POST /v1/chat/completions`

**Request type:** `ChatCompletionRequest` (Pydantic model)

**Dependency parameters:**
- `api_key: str = Depends(verify_api_key_flexible)` — authentication dependency

**Stream-selection condition:**
```python
if request.stream:
    return StreamingResponse(...)
```
When `request.stream` is truthy, the route returns a `StreamingResponse`.

**Internal generator called:**
```python
_iterate_openai_stream(normalized, request_base_url)
```

**StreamingResponse construction point:**
```python
return StreamingResponse(
    _iterate_openai_stream(normalized, request_base_url),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    },
)
```

**Media type:** `"text/event-stream"`

**Explicit headers:**
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

**Status behavior:** Default 200 (not explicitly set; `StreamingResponse` inherits from `Response` with `status_code: int = 200`).

**Whether construction starts iteration:** No. `StreamingResponse.__init__` stores the async generator as `self.body_iterator` but does not call `__anext__`. Iteration begins only when `stream_response(send)` is invoked via `__call__`.

**Pre-response exceptions:**
- `_normalize_openai_request` may raise `HTTPException(status_code=400)` for empty messages/contents or invalid image URIs.
- `_ensure_generation_handler()` may raise `HTTPException(status_code=500)` if `generation_handler is None`.
- `_get_request_base_url` reads headers; does not raise.
- The `try/except` wrapper catches non-HTTP exceptions and re-raises as `HTTPException(status_code=500)`.
- All exceptions before `StreamingResponse(...)` construction occur before HTTP response start.

**Raw Request fields:**
- `raw_request.headers` — used for `x-forwarded-proto`, `x-forwarded-host`, `host`
- `raw_request.url.scheme` — fallback for proto

**Locks, metrics, and config accessed:** None at the route wrapper level. The generator reads the module-level `generation_handler` global but does not modify metrics or configuration.

---

### 1.2 Gemini Streaming: `stream_generate_content`

**Location:** `src/api/routes.py`, lines 938–973

**Signature:**
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

**Route path:** `POST /v1beta/models/{model}:streamGenerateContent` (also `POST /models/{model}:streamGenerateContent`)

**Request type:** `GeminiGenerateContentRequest` (Pydantic model)

**Dependency parameters:**
- `model: str` — path parameter
- `alt: Optional[str] = Query(None)` — query parameter (unused in route body)
- `api_key: str = Depends(verify_api_key_flexible)` — authentication dependency

**Stream-selection condition:** Always streaming. The route is dedicated to streaming; there is no `stream` flag check.

**Internal generator called:**
```python
_iterate_gemini_stream(normalized, normalized.model, request_base_url)
```

**StreamingResponse construction point:**
```python
return StreamingResponse(
    _iterate_gemini_stream(normalized, normalized.model, request_base_url),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    },
)
```

**Media type:** `"text/event-stream"`

**Explicit headers:** Identical to OpenAI streaming:
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

**Status behavior:** Default 200.

**Whether construction starts iteration:** No. Same as OpenAI streaming.

**Pre-response exceptions:**
- `_normalize_gemini_request` may raise `HTTPException(status_code=400)` for empty contents, unsupported mime types, or image load failures.
- `_ensure_generation_handler()` may raise `HTTPException(status_code=500)`.
- The `try/except` wrapper catches `HTTPException` and returns a `JSONResponse` with Gemini error shape; non-HTTP exceptions become 500 errors.
- All exceptions before `StreamingResponse(...)` construction occur before HTTP response start.

**Raw Request fields:** Same as OpenAI streaming.

**Locks, metrics, and config accessed:** None at the route wrapper level.

---

### 1.3 Shared Response-Construction Helpers

**`_iterate_openai_stream`:**
- Location: `src/api/routes.py`, lines 717–737
- Signature: `async def _iterate_openai_stream(normalized: NormalizedGenerationRequest, base_url_override: Optional[str] = None)`
- Type: async generator yielding `str`
- Yields `data:`-prefixed SSE frames and terminates with `data: [DONE]\n\n`

**`_iterate_gemini_stream`:**
- Location: `src/api/routes.py`, lines 740–786
- Signature: `async def _iterate_gemini_stream(normalized: NormalizedGenerationRequest, response_model: str, base_url_override: Optional[str] = None)`
- Type: async generator yielding `str`
- Yields Gemini-shaped SSE frames; no terminal sentinel

Both generators:
- Call `_ensure_generation_handler()` to obtain the module-level handler
- Iterate `handler.handle_generation(...)` with `stream=True`
- Do not catch exceptions (propagate directly to caller)
- Do not modify global state

---

## 2. Starlette StreamingResponse Behavior

**Source inspected:** `.venv/lib/python3.12/site-packages/starlette/responses.py`, lines 220–281

### 2.1 Construction

```python
class StreamingResponse(Response):
    body_iterator: AsyncContentStream

    def __init__(
        self,
        content: ContentStream,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        if isinstance(content, AsyncIterable):
            self.body_iterator = content
        else:
            self.body_iterator = iterate_in_threadpool(content)
        self.status_code = status_code
        self.media_type = self.media_type if media_type is None else media_type
        self.background = background
        self.init_headers(headers)
```

**Whether construction consumes the iterator:** No. The async generator is stored as `self.body_iterator` without calling `__anext__`. Iteration begins only during `stream_response(send)`.

**When body_iterator execution starts:** Only when `stream_response(send)` is invoked via `__call__(scope, receive, send)`. This happens after the response is returned from the route and the ASGI server calls it.

**Iterator wrapping:** If `content` is a sync `Iterable`, it is wrapped via `iterate_in_threadpool(content)`. If it is an `AsyncIterable` (which `_iterate_openai_stream` and `_iterate_gemini_stream` are), it is stored directly.

**Direct body_iterator iteration feasibility:** Yes. `self.body_iterator` is a public attribute. Tests can directly iterate with `async for chunk in response.body_iterator` without invoking `__call__`, `stream_response`, or any ASGI machinery. This avoids HTTP transport, lifespan, and disconnect handling.

**String-to-bytes encoding:** During `stream_response`, each chunk is checked:
```python
if not isinstance(chunk, (bytes, memoryview)):
    chunk = chunk.encode(self.charset)
```
The default `charset` is `"utf-8"` (inherited from `Response`). Since the generators yield `str`, each chunk will be UTF-8 encoded during HTTP transport. Direct iteration yields `str` (no encoding applied).

**Media-type/charset handling:** The `init_headers` method appends a `content-type` header. For `text/event-stream`, the condition `content_type.startswith("text/")` is true, so `"; charset=utf-8"` is appended. The final header is `content-type: text/event-stream; charset=utf-8`.

**Background-task handling:** If `background` is not None, it is awaited after `stream_response` completes (or after the task group completes for ASGI spec < 2.4). The route wrappers do not pass a `background` argument, so this is not exercised.

**Exception propagation during iteration:** The `stream_response` method does not wrap the `async for` loop in a try/except. Exceptions raised by the generator propagate directly. For ASGI spec >= 2.4, `OSError` is caught and converted to `ClientDisconnect`. Other exceptions propagate. For spec < 2.4, the task group and `collapse_excgroups` handle cancellation. Direct iteration propagates exceptions directly to the test.

**Cleanup on completion or failure:** The generator's `finally` block (if any) executes when the generator is closed or exhausted. Neither `_iterate_openai_stream` nor `_iterate_gemini_stream` has a `finally` block. The `stream_response` method sends a final `{"type": "http.response.body", "body": b"", "more_body": False}` after the generator is exhausted. Direct iteration does not send this.

---

## 3. Authentication Dependency

### 3.1 `verify_api_key_flexible`

**Location:** `src/core/auth.py`, lines 44–62

**Signature:**
```python
async def verify_api_key_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    key: Optional[str] = Query(None),
) -> str:
```

**Config/database/service reads:**
- Reads `config.api_key` (from `src/core/config.py`) via `AuthManager.verify_api_key(api_key)`.
- `config` is a module-level singleton that may be populated from environment variables or a database at startup.
- No database query during verification; comparison is in-memory.

**Whether a test-local dependency override is safe:**
Yes. FastAPI's `Depends` system supports `app.dependency_overrides[verify_api_key_flexible] = lambda: "test-key"`. This returns a fixed key without invoking the real security checks. The override is local to the test app instance and does not affect the production app or module-level state.

**Direct-call behavior with explicit already-resolved api_key:**
When calling the route function directly (not through FastAPI/TestClient), the `api_key` parameter can be passed as a plain string argument:
```python
await create_chat_completion(request, raw_request, api_key="test-key")
```
This supplies the already-resolved dependency parameter explicitly without invoking dependency injection. Authentication behavior is not exercised. The route does not use `api_key` beyond the dependency check; it is not forwarded to the handler or any service.

**Distinction between route characterization and authentication testing:**
- Route characterization tests the conversion, framing, and response shape. Authentication is a precondition, not the subject under test.
- Authentication testing would verify key acceptance/rejection, which is out of scope for streaming transport tests.
- Direct call with explicit `api_key` or dependency override both safely separate authentication from the transport behavior under test.

---

## 4. Exception Timing Map

### Phase 1: Request Validation

**When:** Before route wrapper execution.
**Where:** FastAPI/Pydantic validates `ChatCompletionRequest` or `GeminiGenerateContentRequest`.
**Error emergence:** Pydantic raises `ValidationError`, which FastAPI converts to a 422 response. This occurs before HTTP response start (FastAPI sends the error response).
**Not tested:** This is framework behavior, not route logic.

### Phase 2: Route Wrapper Execution

**When:** After request validation, during the route function body.
**Where:** `create_chat_completion` or `stream_generate_content` begins execution.
**Error emergence:** None at this phase unless the wrapper itself raises immediately (unlikely).

### Phase 3: Handler-Initialization Check

**When:** During `_ensure_generation_handler()`.
**Where:** Called by `_normalize_openai_request` (indirectly via `_collect_non_stream_result` for non-streaming) or by the generator (for streaming).
**Error emergence:** Raises `HTTPException(status_code=500, detail="Generation handler not initialized")`. For streaming routes, this occurs during generator construction (when `_iterate_openai_stream` or `_iterate_gemini_stream` is called), which happens before `StreamingResponse` construction. The exception propagates to the route's try/except, which re-raises it. This occurs before HTTP response start.

### Phase 4: StreamingResponse Construction

**When:** After normalization and base URL extraction succeed.
**Where:** `StreamingResponse(generator, media_type, headers)` is called.
**Error emergence:** None. `StreamingResponse.__init__` does not iterate the generator. Construction is safe and does not raise (assuming valid arguments).

### Phase 5: First Body Iteration

**When:** After the route returns the `StreamingResponse` and the ASGI server calls `response.__call__(scope, receive, send)`.
**Where:** `stream_response(send)` begins iterating `self.body_iterator`.
**Error emergence:** The generator calls `_ensure_generation_handler()` (if not already called during normalization) and then `handler.handle_generation(...)`. Exceptions here occur after HTTP response start (headers have been sent via `send({"type": "http.response.start", ...})`). The first chunk send happens after the first `async for` iteration.

### Phase 6: Partial Output

**When:** After the first chunk has been sent.
**Where:** During subsequent `async for chunk in self.body_iterator` iterations.
**Error emergence:** Exceptions here occur after HTTP response start and after partial body has been sent. The connection may be left in a partial state.

### Phase 7: Exception After Partial Output

**When:** After some chunks have been sent, a subsequent iteration raises.
**Where:** During `async for chunk in self.body_iterator`.
**Error emergence:** The exception propagates from `stream_response` to `__call__`. For ASGI spec >= 2.4, non-OSError exceptions propagate. For spec < 2.4, the task group cancels. The client sees a truncated stream. The server may log the exception. No synthetic error event is emitted by the generator.

### Phase 8: Normal Completion

**When:** The generator is exhausted.
**Where:** After the `async for` loop in `stream_response` completes.
**Error emergence:** None. The method sends `{"type": "http.response.body", "body": b"", "more_body": False}` to signal completion. For OpenAI streaming, the final chunk is `data: [DONE]\n\n`. For Gemini streaming, the generator ends silently.

---

## 5. Headers and Media Types

### 5.1 OpenAI Streaming Media Type

**Explicit:** `media_type="text/event-stream"`

**Starlette behavior:** The `init_headers` method checks `content_type.startswith("text/")` and appends `"; charset=utf-8"`. The final `content-type` header is:
```
content-type: text/event-stream; charset=utf-8
```

### 5.2 Gemini Streaming Media Type

**Explicit:** `media_type="text/event-stream"` (identical to OpenAI)

**Starlette behavior:** Same as OpenAI. Final header:
```
content-type: text/event-stream; charset=utf-8
```

### 5.3 Explicit Route Headers

Both streaming routes set:
```python
headers={
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
```

These are stored in `self.raw_headers` as byte tuples.

### 5.4 Automatically Generated Starlette Headers

**Content-Length:** Not set for `StreamingResponse`. The `init_headers` method checks `getattr(self, "body", None)`, and `StreamingResponse` does not set `self.body` (only `self.body_iterator`). Thus `body` is `None`, and no `content-length` header is added.

**Content-Type:** As described above, `text/event-stream; charset=utf-8`.

### 5.5 Cache-Control and Buffering Headers

**Explicit:** `Cache-Control: no-cache`, `X-Accel-Buffering: no`

**Purpose:** `X-Accel-Buffering: no` is a hint to nginx and similar proxies to disable buffering. `Cache-Control: no-cache` prevents caching.

### 5.6 Server/Proxy Behavior (Undefined)

The following are not tested and remain undefined:
- Actual proxy buffering behavior (nginx, Cloudflare, etc.)
- Connection keep-alive timeout
- Chunked transfer encoding (ASGI server behavior)
- Backpressure and flow control
- Client disconnect detection and propagation

---

## 6. Candidate Test Seams

### Option A: Direct Route Function Call → Direct body_iterator Consumption

**Approach:**
```python
response = await create_chat_completion(request, raw_request, api_key="test-key")
chunks = []
async for chunk in response.body_iterator:
    chunks.append(chunk)
```

**Isolation:** High. No FastAPI app, no lifespan, no TestClient, no ASGI transport.

**Application/lifespan risk:** None. The app is not created.

**Dependency behavior:** Direct route calls supply the already-resolved `api_key` dependency parameter explicitly. Authentication behavior is not exercised. No dependency injection is invoked.

**Production-global initialization:** None. `generation_handler` is patched; no services are instantiated.

**Coverage gained:**
- StreamingResponse construction (media_type, headers, status_code)
- Generator iteration (SSE framing, chunk order, termination)
- Exception propagation before and after partial output
- Header and media type verification

**Cleanup and exception observability:** Direct. Exceptions propagate to the test. Generator cleanup happens when the generator is exhausted or closed.

**Whether it is appropriate for the next sprint:** Yes. This is the narrowest seam with the highest safety and sufficient coverage for transport-level assertions.

### Option B: Minimal Test-Local FastAPI App → Dependency Override → TestClient

**Approach:**
```python
app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_api_key_flexible] = lambda: "test-key"
client = TestClient(app)
response = client.post("/v1/chat/completions", json={...})
```

**Isolation:** Medium. A test-local app is created, but it is separate from the production app.

**Application/lifespan risk:** Low if no lifespan handlers are registered. However, `src.main` registers lifespan handlers that instantiate production services. A test-local app avoids this.

**Dependency behavior:** Overridden via `app.dependency_overrides`. Safe and local.

**Production-global initialization:** None if the test app does not import or invoke `src.main`.

**Coverage gained:**
- Full HTTP transport (headers, status, chunked encoding)
- TestClient streaming iteration
- Dependency override mechanism

**Cleanup and exception observability:** TestClient handles cleanup. Exceptions during streaming may be caught by TestClient or propagated depending on configuration.

**Whether it is appropriate for the next sprint:** Possibly, but adds complexity (app creation, dependency override, TestClient) without significant additional coverage beyond Option A for the first transport sprint.

### Option C: Import/Use src.main

**Approach:**
```python
from src.main import app
client = TestClient(app)
```

**Isolation:** Low. The production app is imported, triggering module-level code.

**Application/lifespan risk:** High. `src.main` registers lifespan handlers that instantiate `GenerationHandler`, `FlowClient`, `TokenManager`, database connections, and other services. Lifespan startup may fail or hang without proper configuration.

**Dependency behavior:** Production dependencies are active. Override is possible but may conflict with lifespan-initialized services.

**Production-global initialization:** Full. Database, services, and configuration are initialized.

**Coverage gained:** Full production behavior, including lifespan, middleware, and all routes.

**Cleanup and exception observability:** Complex. Lifespan shutdown must be managed. TestClient may not properly clean up all resources.

**Whether it is appropriate for the next sprint:** No. This is unsafe for offline, deterministic tests. The production app requires configuration, credentials, and services that are not available in a test environment.

---

## 7. Recommended Seam

**Option A: Direct route function call plus direct `StreamingResponse.body_iterator` consumption.**

### Added Coverage

- `StreamingResponse` construction verification (media_type, headers, status_code)
- Generator iteration at the transport boundary (SSE framing, chunk order, termination)
- Exception propagation before and after partial output
- Header and media type assertions
- Distinction between OpenAI `[DONE]` termination and Gemini silent termination

### Remaining Gaps

- Full HTTP transport (chunked encoding, connection handling)
- Proxy buffering and backpressure
- Client disconnect detection
- ASGI server behavior
- TestClient integration

### Safety

- No FastAPI app creation
- No lifespan startup/shutdown
- No TestClient or ASGI transport
- No production service instantiation
- No network calls
- Deterministic and offline

### Whether OpenAI and Gemini Belong Together

Yes. Both routes use identical `StreamingResponse` construction (same media_type, headers, status). The generators differ (OpenAI emits `[DONE]`, Gemini does not), but the transport seam is the same. Testing both in the same sprint provides comprehensive coverage of the streaming transport boundary.

### Whether Partial-Output Exceptions Belong in the First Transport Sprint

Yes, but with caution. Partial-output exceptions are a critical compatibility boundary: clients may see truncated streams. However, the generator behavior (no synthetic error event, direct exception propagation) is already characterized in Sprint 006G and 006H. The transport-level test should verify that:
- Exceptions before the first chunk prevent HTTP response start (if the route wrapper catches them)
- Exceptions after partial output propagate and truncate the stream
- No synthetic error event is emitted

This is a small number of tests (2–4) and adds significant value.

---

## 8. Proposed Next Test Matrix

### Test List 1: OpenAI Streaming Transport — Happy Path

**Route:** `create_chat_completion`
**Request:** `ChatCompletionRequest(model="text-model", messages=[{"role": "user", "content": "test"}], stream=True)`
**Patched globals:** `src.api.routes.generation_handler` → `FakeStreamingHandler(yield_values=[...])`
**Invocation seam:** Direct function call with `api_key="test-key"`
**Stable assertions:**
- Response is a `StreamingResponse`
- `response.media_type == "text/event-stream"`
- `response.status_code == 200`
- Explicit headers include `Cache-Control`, `Connection`, `X-Accel-Buffering`
- `response.body_iterator` yields SSE frames
- Final frame is `data: [DONE]\n\n`
**Explicit non-coverage:** HTTP transport, TestClient, proxy behavior

### Test List 2: Gemini Streaming Transport — Happy Path

**Route:** `stream_generate_content`
**Request:** `GeminiGenerateContentRequest(contents=[{"role": "user", "parts": [{"text": "test"}]}])`
**Patched globals:** `src.api.routes.generation_handler` → `FakeStreamingHandler(yield_values=[...])`
**Invocation seam:** Direct function call with `model="text-model"`, `api_key="test-key"`
**Stable assertions:**
- Response is a `StreamingResponse`
- `response.media_type == "text/event-stream"`
- `response.status_code == 200`
- Explicit headers include `Cache-Control`, `Connection`, `X-Accel-Buffering`
- `response.body_iterator` yields Gemini-shaped SSE frames
- No `[DONE]` sentinel
**Explicit non-coverage:** HTTP transport, TestClient, proxy behavior

### Test List 3: OpenAI Streaming Transport — Exception Before First Chunk

**Route:** `create_chat_completion`
**Request:** Same as Test List 1
**Patched globals:** `generation_handler = None` (triggers `_ensure_generation_handler` to raise)
**Invocation seam:** Direct function call
**Stable assertions:**
- `HTTPException` is raised before `StreamingResponse` construction
- No response object is returned
**Explicit non-coverage:** HTTP error response shape (framework behavior)

### Test List 4: Gemini Streaming Transport — Exception Before First Chunk

**Route:** `stream_generate_content`
**Request:** Same as Test List 2
**Patched globals:** `generation_handler = None`
**Invocation seam:** Direct function call
**Stable assertions:**
- Exception is caught by the route's try/except
- Response is a `JSONResponse` with Gemini error shape
- Status code is 500
**Explicit non-coverage:** HTTP transport

### Test List 5: OpenAI Streaming Transport — Partial Output Then Exception

**Route:** `create_chat_completion`
**Request:** Same as Test List 1
**Patched globals:** `FakeFailingHandler(yield_values=[chunk1], error=RuntimeError("synthetic failure"))`
**Invocation seam:** Direct function call, iterate `response.body_iterator`
**Stable assertions:**
- First chunk is yielded successfully
- Second iteration raises `RuntimeError`
- No `[DONE]` is emitted
**Explicit non-coverage:** HTTP partial response, client disconnect

### Test List 6: Gemini Streaming Transport — Partial Output Then Exception

**Route:** `stream_generate_content`
**Request:** Same as Test List 2
**Patched globals:** `FakeFailingHandler(yield_values=[chunk1], error=RuntimeError("synthetic failure"))`
**Invocation seam:** Direct function call, iterate `response.body_iterator`
**Stable assertions:**
- First chunk is yielded successfully
- Second iteration raises `RuntimeError`
- No synthetic error event is emitted
**Explicit non-coverage:** HTTP partial response, client disconnect

---

## 9. Deferred Behaviors

The following behaviors are explicitly deferred and not tested in the next sprint:

- **Full HTTP transport:** Chunked encoding, connection handling, ASGI server behavior
- **Proxy buffering:** nginx, Cloudflare, and other proxy behavior
- **Backpressure:** Flow control and buffer management
- **Client disconnect:** Detection and propagation
- **TestClient integration:** Full HTTP request/response cycle
- **Lifespan behavior:** Startup/shutdown handlers
- **Production services:** Database, token manager, flow client, etc.
- **Network calls:** Upstream service interaction
- **Media retrieval:** Image/video download and conversion

---

## 10. Commands and Results

### Baseline Verification

```bash
git status --short
# Result: worktree contains only intended Sprint 006I changes and no unrelated changes

git log -5 --oneline
# Result:
# 7913a5a test(gemini): add 41 mocked Gemini streaming generator contract tests
# 2dde91f test(generation): add mocked OpenAI streaming generator contract tests
# 4fd6189 test(compatibility): add mocked OpenAI image-result route contract tests
# 8085205 test: characterize non-streaming generation routes
# 7257afe docs: map mocked generation route seam

python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Result: Ran 285 tests in 0.084s — OK
```

### Import Safety

```bash
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Result: OK
```

### No Runtime Source Changes

```bash
git diff -- src
# Result: (no output)
```

---

## 11. Confirmation

- No generation routes were invoked.
- No `StreamingResponse` was constructed or consumed.
- No HTTP transport was exercised.
- No TestClient or ASGI transport was used.
- No FastAPI app was created.
- No dependencies were overridden.
- No authentication was tested.
- No `src.main` was imported.
- No lifespan was run.
- No production services were instantiated.
- No network calls were made.
- No media was retrieved.
- No runtime source (`src/`) was modified.
- No fixtures were added.
- No dependencies were added.
- No commits or pushes were performed.

---

## 12. Final Status

**Sprint 006I — HTTP Streaming Transport Seam Discovery: Completed**

All discovery and documentation objectives achieved. The narrowest safe seam for
streaming transport testing has been identified and documented. The next
implementation sprint (Sprint 006J) can proceed with confidence using the
recommended seam and proposed test matrix.
