# HTTP-Level Streaming Test Seam Discovery

> **Sprint 006L — HTTP-Level Streaming Test Seam Discovery**
> **Sprint 006M — HTTP-Level Streaming Route Characterization (Implementation)**
> This document analyzes candidate seams for exercising streaming generation
> routes through a full HTTP request path (FastAPI routing, Pydantic validation,
> dependency injection, and an in-process HTTP client) while remaining fully
> offline and deterministic.
>
> Sprint 006M implemented the recommended seam (Candidate A) with 2 HTTP-level
> streaming route characterization tests. See
> [SPRINT-006M](SPRINTS/SPRINT-006M-http-level-streaming-route-characterization.md)
> and `tests/compatibility/test_http_streaming_routes.py` for details.

---

## 1. Installed Dependency Versions

| Package   | Installed Version |
|-----------|-------------------|
| Python    | 3.12.3            |
| FastAPI   | 0.119.0           |
| Starlette | 0.48.0            |
| HTTPX     | 0.28.1            |
| AnyIO     | 4.13.0            |

---

## 2. Why src.main.app Is Unsafe

`src.main` constructs production singletons at module import time:

- `Database()`, `ProxyManager(db)`, `FlowClient(proxy_manager, db)`
- `TokenManager(db, flow_client)`, `ConcurrencyManager()`
- `LoadBalancer(token_manager, concurrency_manager)`
- `GenerationHandler(flow_client, token_manager, load_balancer, db, ...)`

The `lifespan` async context manager performs database initialization, token
snapshot loading, browser captcha service startup, warmup-tab allocation,
concurrency-manager initialization, remote-browser prefill, and an
auto-unban background task.

Importing `src.main.app` would:

1. Execute module-level service construction (database file access, config reads).
2. Register the production lifespan that cannot complete without a real environment.
3. Share module-level singletons across test cases, creating state leakage.

Therefore, importing `src.main.app` is excluded.

---

## 3. The routes.router Module Boundary

`src.api.routes` exposes an `APIRouter` that is independent of `src.main`:

- It is a plain `APIRouter()` with no lifespan, middleware, or state.
- It depends on `verify_api_key_flexible` (a FastAPI `Depends` callable).
- It reads the module-level `generation_handler` global via `_ensure_generation_handler()`.
- `set_generation_handler(handler)` sets this global.
- No module-level side effects occur on import beyond symbol resolution.

This makes `routes.router` safe to mount on a test-local `FastAPI` instance.

---

## 4. Authentication Override via dependency_overrides

`verify_api_key_flexible` is imported from `src.core.auth`:

```python
async def verify_api_key_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security),
    x_goog_api_key: Optional[str] = Header(None, alias="x-goog-api-key"),
    key: Optional[str] = Query(None),
) -> str:
```

FastAPI's `app.dependency_overrides[verify_api_key_flexible]` replaces this
callable entirely. A simple sync or async function returning a fixed test key
bypasses all authentication without touching `AuthManager`, `config.api_key`,
or any database/config state.

---

## 5. Generation Handler Patching

The `generation_handler` in `src.api.routes` is a module-level global set via
`set_generation_handler()`. For HTTP-level tests, two patching strategies exist:

1. **Direct assignment:** `routes_module.generation_handler = fake_handler` in
   `setUp`, restored to `None` or the original in `tearDown`.
2. **`unittest.mock.patch`:** `patch("src.api.routes.generation_handler", fake_handler)`
   as a context manager or decorator.

Both are safe and deterministic. `unittest.mock.patch` is preferred because
it provides automatic cleanup on test failure.

---

## 6. Candidate Seam Comparison

### Candidate A — Test-local FastAPI + routes.router + TestClient

| Dimension | Finding |
|-----------|---------|
| Lifespan isolation | `routes.router` has no lifespan. The test-local `FastAPI()` can omit the `lifespan` parameter entirely. |
| Production-global initialization risk | None. `src.main` is never imported. |
| Authentication override | `app.dependency_overrides[verify_api_key_flexible]` works correctly with `APIRouter` mounted on `FastAPI`. |
| Response buffering | **Fully buffered.** `_TestClientTransport` collects all `http.response.body` messages into an `io.BytesIO()`, then wraps the entire buffer as `httpx.ByteStream(raw_kwargs["stream"].read())`. The entire response body is delivered as a single chunk. `client.stream()` and `iter_bytes()` are not incremental. |
| Original streaming chunk boundaries visible | **No.** All SSE events are concatenated into a single bytes payload. Boundaries are recoverable by splitting on `\n\n`, but transport-level framing is lost. |
| client.stream() / iter_bytes() / iter_lines() genuinely incremental | **No.** The body is fully buffered before the response object is returned. `iter_bytes()` and `iter_lines()` iterate over the already-complete buffer. |
| Effective ASGI scope and spec_version | Scope has no `asgi` key. `spec_version` defaults to `"2.0"`. |
| Starlette disconnect-listener/task-group path used | **Yes.** Since `spec_version < (2, 4)`, `StreamingResponse.__call__` uses the `anyio.create_task_group()` path with `listen_for_disconnect`. |
| Exception before response start | FastAPI's exception handler converts it to a JSON 500 response before `StreamingResponse` is constructed. |
| Exception after partial output | Propagates through the task group. No final `more_body=False` is sent. The transport's `assert response_complete.is_set()` fails, causing the test client call to raise. |
| Cleanup and determinism | Fully deterministic. No threads, sockets, or background tasks. |
| Required dependencies | `fastapi`, `starlette`, `httpx`, `anyio` (all already installed). |

### Candidate B — Test-local FastAPI + httpx.AsyncClient + ASGITransport

| Dimension | Finding |
|-----------|---------|
| Lifespan isolation | Same as A. |
| Production-global initialization risk | None. |
| Authentication override | Same as A. |
| Response buffering | **Fully buffered.** `ASGITransport` collects all `body` chunks into `body_parts: list[bytes]`, then `ASGIResponseStream.__aiter__` yields `b"".join(body_parts)` as a single chunk. |
| Original streaming chunk boundaries visible | **No.** Same concatenation behavior as A. |
| client.stream() / iter_bytes() / iter_lines() genuinely incremental | **No.** `ASGIResponseStream` yields the full joined body in a single iteration step. |
| Effective ASGI scope and spec_version | Scope has `"asgi": {"version": "3.0"}` but no `spec_version` key. Defaults to `"2.0"`. |
| Starlette disconnect-listener/task-group path used | **Yes.** Same `spec_version < (2, 4)` path as A. |
| Exception before response start | `raise_app_exceptions=True` (default) re-raises. `raise_app_exceptions=False` returns a synthetic 500. |
| Exception after partial output | `response_complete` may not be set. `assert response_complete.is_set()` fails, raising `AssertionError`. |
| Cleanup and determinism | Fully deterministic. Requires `async with` client lifecycle. |
| Required dependencies | Same as A. |

**Advantage over A:** Provides a native async context (useful for async test
frameworks like `pytest-asyncio`). No portal/thread overhead.

**Disadvantage vs. A:** Requires async test setup. Slightly more complex
exception behavior with `raise_app_exceptions`.

### Candidate C — Test-only ASGI wrapper altering asgi.spec_version

| Dimension | Finding |
|-----------|---------|
| Lifespan isolation | Depends on the wrapped app. |
| Production-global initialization risk | Depends on the wrapped app. |
| Authentication override | Depends on the wrapped app. |
| Response buffering | The wrapper itself doesn't buffer; buffering is determined by the transport (TestClient or ASGITransport). |
| Original streaming chunk boundaries visible | Same as the underlying transport. |
| Effective ASGI scope and spec_version | The wrapper injects `spec_version` into the `asgi` dict. If set to `>= "2.4"`, `StreamingResponse.__call__` uses the simpler `stream_response(send)` path without the task group. |
| Starlette disconnect-listener/task-group path used | **No** when `spec_version >= (2, 4)`. The simpler path is used. |
| Exception behavior | With `spec_version >= (2, 4)`, exceptions propagate through `stream_response(send)` directly. `OSError` is caught and converted to `ClientDisconnect`. |
| Cleanup and determinism | Deterministic. |
| Required dependencies | None beyond A or B. |

**Assessment:** This is a supplementary technique, not a standalone seam. It
can be combined with A or B to control which `StreamingResponse.__call__`
code path is exercised. However, the default `spec_version` "2.0" path (task
group with disconnect listener) is the path exercised when neither transport
sets `asgi.spec_version`. Adding a spec_version wrapper tests an alternative
code path, reducing the test's fidelity relative to the default transport
behavior.

### Candidate D — Importing src.main.app

| Dimension | Finding |
|-----------|---------|
| Lifespan isolation | **None.** The production lifespan is registered on `app`. Even without entering the context manager, `TestClient(app)` as a context manager triggers lifespan startup/shutdown. |
| Production-global initialization risk | **Critical.** Module import constructs `Database()`, `ProxyManager`, `FlowClient`, `TokenManager`, `LoadBalancer`, `GenerationHandler`, `ConcurrencyManager`. These access the filesystem, config files, and potentially network interfaces. |
| Authentication override | `dependency_overrides` could work, but the production handler is already wired to real services. |
| Response buffering | Same as A or B (depends on client). |
| Cleanup and determinism | **Not deterministic.** Lifespan startup depends on database state, token availability, and config. |
| Required dependencies | Full production dependencies including database, config files. |

**Verdict: Excluded.** Importing `src.main.app` violates the offline,
deterministic, no-production-services constraint.

### Candidate E — Live Uvicorn/socket server

| Dimension | Finding |
|-----------|---------|
| Lifespan isolation | Full production lifespan would execute. |
| Production-global initialization risk | **Critical.** Same as D, plus actual socket binding. |
| Authentication override | Not applicable without modifying production code. |
| Response buffering | Real TCP buffering; non-deterministic chunk delivery. |
| Original streaming chunk boundaries visible | Potentially yes, but depends on TCP segmentation, Nagle's algorithm, and kernel buffering. Non-deterministic. |
| Cleanup and determinism | **Not deterministic.** Port conflicts, socket cleanup, process lifecycle. |
| Required dependencies | `uvicorn`, network stack. |

**Verdict: Excluded.** Violates offline, deterministic, no-network,
no-production-services constraints.

---

## 7. Buffering and Chunk-Visibility Summary

| Seam | Transport buffers? | SSE boundaries recoverable? | Incremental client delivery? |
|------|--------------------|-----------------------------|------------------------------|
| TestClient (A) | Yes, fully into `BytesIO` | Yes, by splitting on `\n\n` | **No** |
| ASGITransport (B) | Yes, fully into `list[bytes]` join | Yes, by splitting on `\n\n` | **No** |
| ASGI wrapper (C) | Depends on underlying transport | Same as underlying | **No** |

**Critical finding:** Neither Starlette `TestClient` nor httpx
`ASGITransport` provides genuinely incremental streaming delivery to the
client. Both fully buffer the response body before returning it. This means:

1. Tests cannot assert that chunk N was delivered before chunk N+1 at the
   transport level.
2. Tests cannot assert inter-chunk timing or backpressure.
3. Tests **can** assert the fully reassembled SSE body, parse all events,
   verify their order, and verify their content.

The reassembled body is sufficient for compatibility contract assertions
because SSE clients parse the full stream sequentially anyway.

---

## 8. Effective ASGI Spec Behavior

Both `TestClient` and `ASGITransport` result in `spec_version` defaulting to
`"2.0"` (neither sets `asgi.spec_version` in the scope). Starlette 0.48.0
therefore applies its default, and `StreamingResponse.__call__` uses the
`else` branch:

```python
with collapse_excgroups():
    async with anyio.create_task_group() as task_group:
        async def wrap(func):
            await func()
            task_group.cancel_scope.cancel()
        task_group.start_soon(wrap, partial(self.stream_response, send))
        await wrap(partial(self.listen_for_disconnect, receive))
```

This observation does not prove equivalence with a deployed Uvicorn server's
streaming, disconnect, cancellation, scheduling, or socket behavior. The
installed Uvicorn source has not been inspected for this sprint, and no
claims are made about the `spec_version` value that a production Uvicorn
supplies.

---

## 9. Recommended Seam

**Candidate A: Test-local FastAPI + routes.router + TestClient**

Rationale:

1. **Simplest setup.** Synchronous `TestClient` works with standard
   `unittest.TestCase` without async infrastructure.
2. **No production risk.** `src.main` is never imported.
3. **Dependency override works.** `app.dependency_overrides[verify_api_key_flexible]`
   cleanly replaces authentication.
4. **Handler patching works.** `unittest.mock.patch("src.api.routes.generation_handler")`
   or direct assignment provides a deterministic fake handler.
5. **Full HTTP contract.** Route matching, Pydantic validation, request
   parsing, dependency injection, status codes, headers, and SSE body are
   all exercised.
6. **Fully buffered body is acceptable.** Since neither transport provides
   incremental delivery, the fully buffered body is the correct assertion
   target. SSE events are recoverable by parsing the complete body text.

`AsyncClient` with `ASGITransport` (Candidate B) is a valid alternative for
async test frameworks but provides no additional coverage for the proposed
test matrix. It should be considered only if future sprints require async
test infrastructure.

---

## 10. Proposed Next-Sprint Implementation Matrix

### Test 1: OpenAI HTTP-level streaming response

- **Endpoint:** `POST /v1/chat/completions` with `stream: true`
- **Fake handler:** Yields 2 deterministic `data:` prefixed SSE strings
- **Assertions:**
  - Status code 200
  - `content-type: text/event-stream`
  - `cache-control: no-cache`
  - `x-accel-buffering: no`
  - Fully reassembled body contains the expected SSE events in order
  - Final event is `data: [DONE]\n\n`
  - Each event is parseable (JSON after `data:` prefix, except `[DONE]`)

### Test 2: Gemini HTTP-level streaming response

- **Endpoint:** `POST /v1beta/models/{model}:streamGenerateContent`
- **Fake handler:** Yields 2 deterministic OpenAI-format JSON chunks
- **Assertions:**
  - Status code 200
  - `content-type: text/event-stream`
  - Fully reassembled body contains Gemini-formatted SSE events
  - Each event has `candidates[0].content.role == "model"`
  - `modelVersion` matches the request model
  - No `data: [DONE]` sentinel at end (Gemini contract)

These two tests are sufficient for the first HTTP-level streaming
implementation slice. The successful-path tests already prove that the
test-local `dependency_overrides[verify_api_key_flexible]` is wired
correctly and that the patched `generation_handler` is invoked through the
full FastAPI routing and Pydantic validation chain.

A 401 (authentication failure) test belongs to a separate authentication
characterization sprint. A 422 (request validation failure) test primarily
characterizes generic FastAPI/Pydantic validation behavior and is not needed
for the first HTTP-level streaming implementation slice.

---

## 11. Explicitly Deferred

The following are out of scope for the next implementation sprint:

- Original ASGI body-message boundaries (covered by Sprint 006K/006K.1)
- True incremental client delivery (impossible with current transports)
- Client disconnect behavior
- Cancellation propagation
- Backpressure
- Proxy buffering
- TCP or transfer-encoding behavior
- Production lifespan behavior
- `spec_version` manipulation (Candidate C)
- Async client testing (Candidate B)
- Authentication characterization (401 path)
- Request-validation characterization (422 path)
