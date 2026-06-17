# Streaming Disconnect and Cancellation Seam Discovery

> **Sprint 006N — Streaming Disconnect and Cancellation Seam Discovery**
> This document maps the Starlette disconnect and cancellation paths,
> compares six candidate test approaches, analyzes determinism of a
> coordinated receive-side design, and recommends exactly one seam for
> the next implementation sprint.

---

## 1. Repository State at Sprint Start

| Item | Status |
|------|--------|
| Branch | `main` |
| Sprint 006M committed | **Yes** — Sprint 006M committed and pushed (commit `9df3666`) |
| Worktree | Clean |
| Installed Starlette | 0.48.0 |
| Installed httpx | 0.28.1 |
| Existing compatibility tests | 301 (all passing) |

**Note:** Sprint 006M was committed before Sprint 006N restoration. Sprint 006N
work does not modify or interfere with Sprint 006M files.

---

## 2. Installed Framework Behavior Inspected

### 2.1 Starlette `StreamingResponse.__call__` (0.48.0)

Source: `starlette/responses.py` lines 261–281.

```python
async def __call__(self, scope, receive, send):
    spec_version = tuple(map(int, scope.get("asgi", {}).get("spec_version", "2.0").split(".")))
    if spec_version >= (2, 4):
        try:
            await self.stream_response(send)
        except OSError:
            raise ClientDisconnect()
    else:
        with collapse_excgroups():
            async with anyio.create_task_group() as task_group:
                async def wrap(func):
                    await func()
                    task_group.cancel_scope.cancel()
                task_group.start_soon(wrap, partial(self.stream_response, send))
                await wrap(partial(self.listen_for_disconnect, receive))
    if self.background is not None:
        await self.background()
```

Two distinct code paths:

- **ASGI spec < 2.4 (default):** Task-group with `listen_for_disconnect` and
  `stream_response` racing. Whichever finishes first cancels the other.
- **ASGI spec >= 2.4:** Simple sequential `stream_response(send)` with
  OSError-to-ClientDisconnect conversion.

### 2.2 `StreamingResponse.listen_for_disconnect`

```python
async def listen_for_disconnect(self, receive):
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
```

Polls `receive()` until an `http.disconnect` message arrives, then returns.
In the task-group path, returning causes `wrap()` to cancel the scope, which
cancels `stream_response`.

### 2.3 `StreamingResponse.stream_response`

```python
async def stream_response(self, send):
    await send({"type": "http.response.start", "status": ..., "headers": ...})
    async for chunk in self.body_iterator:
        if not isinstance(chunk, (bytes, memoryview)):
            chunk = chunk.encode(self.charset)
        await send({"type": "http.response.body", "body": chunk, "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})
```

Sends response headers, iterates the body iterator, sends the final
`more_body=False` message. If the body iterator is cancelled mid-iteration,
the final message is never sent.

### 2.4 `starlette._utils.collapse_excgroups`

```python
@contextmanager
def collapse_excgroups():
    try:
        yield
    except BaseException as exc:
        if has_exceptiongroups:
            while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
                exc = exc.exceptions[0]
        raise exc
```

Unwraps single-exception `ExceptionGroup`/`BaseExceptionGroup` instances.
When the task group exits with a single cancellation exception, this strips
the group wrapper so the test sees the raw exception.

### 2.5 ASGI Spec Version in TestClient and HTTPX ASGITransport

- **Starlette TestClient:** Does not set `asgi.spec_version` in its scope.
- **HTTPX ASGITransport (0.28.1):** Sets `"asgi": {"version": "3.0"}` but
  does NOT set `"spec_version"`.
- **Both default to spec_version "2.0"** when `StreamingResponse.__call__`
  evaluates `scope.get("asgi", {}).get("spec_version", "2.0")`.

**Conclusion:** TestClient, HTTPX ASGITransport, and direct invocation
with no `spec_version` or `spec_version = "2.0"` all take the **task-group
path** with `listen_for_disconnect`. Sprint 006K's tests used
`spec_version = "2.4"` to deliberately bypass this path.

---

## 3. ASGI Spec Version Path Analysis

### 3.1 Path 1: ASGI Spec Below 2.4 (Task-Group Path)

Used by: TestClient, HTTPX ASGITransport, direct invocation with
`spec_version < "2.4"` or no spec_version.

**Disconnect mechanism:**
1. `receive()` returns `{"type": "http.disconnect"}`.
2. `listen_for_disconnect` returns.
3. `wrap(listen_for_disconnect)` calls `task_group.cancel_scope.cancel()`.
4. The cancel scope sends `CancelledError` into `stream_response` at its
   next await point (a `send()` call or `__anext__()` call).
5. `CancelledError` propagates through the `async for` chain: from the
   current checkpoint through `body_iterator.__anext__()` into the route
   generator, reaching the deepest active await point in the handler
   generator.
6. The handler receives `CancelledError` at its current await checkpoint.
   `try/finally` blocks (if present) execute during unwinding.
7. `CancelledError` propagates back through the route generator and
   `stream_response`. The cancel scope suppresses the cancellation.
8. Task group exits. `collapse_excgroups` unwraps any single exception.

**Stream iterator behavior:**
- `CancelledError` propagates through the `async for` chain: from the
  current checkpoint in `stream_response` through `body_iterator.__anext__()`
  into the route generator, reaching the deepest active await point in
  the handler generator.
- The handler receives `CancelledError` at its current await checkpoint.
  `try/finally` blocks (if present) execute during unwinding.
- Because the gated fake handler is awaiting inside the active `__anext__`
  chain, `CancelledError` propagates through the handler and route
  generators. This cancellation-driven unwinding terminates their active
  frames. Test-only `finally` markers execute as part of that unwinding.
- Starlette 0.48.0 does not explicitly call `aclose()` on
  `response.body_iterator` in the pre-2.4 disconnect path.
- The production `_iterate_openai_stream` and `_iterate_gemini_stream`
  generators have no `try/finally` blocks. A probe-only route-layer
  `finally` marker proves only test instrumentation behavior, not
  production cleanup.

**Finalization chain (cancellation-driven unwinding, not explicit closure):**
- Cancel scope sends `CancelledError` into `stream_response` →
  `CancelledError` propagates through `body_iterator.__anext__()` →
  route generator → handler at its await checkpoint →
  cancellation-driven unwinding terminates the active frames of the
  handler and route generators → cancel scope suppresses the
  cancellation.
- Starlette 0.48.0 does NOT explicitly call `aclose()` on `body_iterator`
  in the pre-2.4 disconnect path. No separate explicit or implicit
  `aclose()` invocation is claimed. The post-call `StopAsyncIteration`
  result proves the returned body iterator is terminated.

**Key property:** The `more_body=False` final message is NOT sent. No
additional SSE events, `[DONE]`, or Gemini events appear after the
cancellation.

### 3.2 Path 2: ASGI Spec 2.4 or Newer

Used by: Direct invocation with `spec_version = "2.4"`, real Uvicorn
(when it sets spec_version >= 2.4).

**Disconnect mechanism:**
1. `send()` raises `OSError` (e.g., `ConnectionResetError`) when the
   client disconnects.
2. The `await send(...)` in `stream_response` propagates the OSError.
3. `async for chunk in self.body_iterator` is interrupted by the
   exception.
4. The body iterator is abandoned (not explicitly closed).
5. `stream_response` propagates the exception.
6. `__call__` catches `OSError` and raises `ClientDisconnect`.

**Stream iterator behavior:**
- The body iterator is not explicitly cancelled or finalized by
  `stream_response`. It is abandoned.
- Python's garbage collector eventually finalizes the abandoned async
  generator (non-deterministic timing).
- The route generator and fake handler are finalized by GC, not by
  explicit cancellation.

**Key property:** The `more_body=False` final message is NOT sent. The
`ClientDisconnect` exception propagates from `__call__`.

---

## 4. Candidate Approach Comparison

### Candidate A: Direct StreamingResponse Invocation — ASGI Spec 2.0 with Coordinated Receive/Send

**Description:** Invoke the `StreamingResponse` object returned by a flow2api
route directly with synthetic ASGI scope (`spec_version = "2.0"` or omitted),
a coordinated `receive()` callable, and a `send()` callable.

**Disconnect mechanism simulated:** `receive()` returns
`{"type": "http.disconnect"}` after coordination with `send()`.

**Flow2api route exercised:** Yes — the full route function is called to
produce the `StreamingResponse`, then the response is invoked with
synthetic ASGI callables.

**Proves disconnect detection:** Yes — `listen_for_disconnect` processes the
`http.disconnect` message.

**Proves iterator cancellation:** Yes — the task-group cancel scope cancels
`stream_response`, which interrupts the body iterator.

**Deterministic coordination:** Achievable with `asyncio.Event` gates:
- `receive()` blocks on an event until `send()` has recorded a selected
  content body.
- `send()` sets the event after recording.
- No `sleep()`, timeout guesses, or probabilistic ordering.
- **Risk:** If the handler generator has multiple yield points with no
  intervening await, multiple chunks may be sent before the cancellation
  takes effect. A gated handler (one that blocks on an event before each
  yield) eliminates this risk entirely.

**Race and scheduling risks:** Low with gated handlers. Without gated
handlers, the fast in-memory handler may yield multiple chunks before the
event loop schedules `listen_for_disconnect`.

**Exception/cancellation behavior:** `CancelledError` propagates through
`stream_response`. `collapse_excgroups` unwraps single-exception groups.

**Fake handler and route-generator finally blocks:** The handler's
`try/finally` marker runs during cancellation-driven unwinding, proving
test-harness finalization, not production application-resource cleanup.
The route-layer `try/finally` marker is probe-only instrumentation; the
production `_iterate_openai_stream` generator has no `finally` block.
`CancelledError` propagates through the active `async for` chain at
await points, terminating the active frames of both generators.

**Post-disconnect emissions:** No additional SSE events, `[DONE]`, final
Gemini events, or `more_body=False` can appear after cancellation.

**Cleanup behavior:** Cancel scope suppresses the `CancelledError`.
Both generators are finalized via cancellation-driven unwinding through
the active `async for` chain. Starlette 0.48.0 does not explicitly call
`aclose()` on `body_iterator`; no separate explicit or implicit `aclose()`
invocation is claimed.

**Framework coupling:** Coupled to Starlette 0.48.0 task-group internals.
May change in future Starlette versions.

**Suitability for compatibility tests:** High. Tests the actual route
generator and handler cancellation-driven unwinding chain. Most thorough
approach for characterizing disconnect and cancellation behavior.

### Candidate B: Direct Invocation — ASGI Spec 2.4 with OSError-Raising Send

**Description:** Invoke the `StreamingResponse` directly with
`spec_version = "2.4"` and a `send()` callable that raises `OSError`
(e.g., `ConnectionResetError`) after recording selected content.

**Disconnect mechanism simulated:** `send()` raises `OSError` simulating a
broken socket.

**Flow2api route exercised:** Yes.

**Proves disconnect detection:** Indirectly — the OSError is caught and
converted to `ClientDisconnect`.

**Proves iterator cancellation:** Partially — the iterator is interrupted by
the exception. The generator is abandoned and finalized by GC. No
`aclose()` invocation is claimed in this path.

**Deterministic coordination:** Fully deterministic. `send()` raises at a
specific call count.

**Race and scheduling risks:** None.

**Exception/cancellation behavior:** `OSError` propagates through
`stream_response` to `__call__`, converted to `ClientDisconnect`.

**Fake handler and route-generator finally blocks:** Non-deterministic.
The generators are abandoned (not explicitly closed). Finalization depends
on garbage collection timing.

**Post-disconnect emissions:** None.

**Cleanup behavior:** No explicit generator cleanup. GC-dependent.

**Framework coupling:** Coupled to Starlette 0.48.0 spec_version 2.4 path.

**Suitability for compatibility tests:** Moderate. Simpler than A but does
not prove deterministic generator cleanup.

### Candidate C: Test-Local FastAPI with TestClient

**Description:** Build a test-local FastAPI app, use TestClient to make an
HTTP request, and attempt to simulate disconnect.

**Disconnect mechanism simulated:** Cannot be simulated. TestClient fully
buffers the response before delivery. There is no way to interrupt the
response mid-stream.

**Flow2api route exercised:** Yes — through the full HTTP path.

**Proves disconnect detection:** No.

**Proves iterator cancellation:** No.

**Deterministic coordination:** Not applicable.

**Race and scheduling risks:** Not applicable.

**Exception/cancellation behavior:** Not applicable.

**Fake handler and route-generator finally blocks:** Normal completion
only.

**Post-disconnect emissions:** Not applicable.

**Cleanup behavior:** Normal completion.

**Framework coupling:** Low — uses standard FastAPI + TestClient.

**Suitability for compatibility tests:** None for disconnect testing.
TestClient is fundamentally incompatible with disconnect simulation.

### Candidate D: HTTPX ASGITransport

**Description:** Use `httpx.AsyncClient(transport=httpx.ASGITransport(app))`
to make an async request.

**Disconnect mechanism simulated:** Cannot be simulated. ASGITransport
fully buffers the response before delivery, same as TestClient.

**Flow2api route exercised:** Yes.

**Proves disconnect detection:** No.

**Proves iterator cancellation:** No.

**Suitability for compatibility tests:** None for disconnect testing.

### Candidate E: Direct Starlette-Helper Testing Without a Flow2api Route

**Description:** Create a plain `StreamingResponse` with a fake async
generator (not a flow2api route) and invoke it with synthetic ASGI
callables.

**Disconnect mechanism simulated:** Same as Candidate A or B, depending on
spec_version.

**Flow2api route exercised:** No.

**Proves disconnect detection:** Yes — tests Starlette's disconnect
mechanism.

**Proves iterator cancellation:** Yes — but only for the fake generator,
not the route generator.

**Deterministic coordination:** Same as Candidate A or B.

**Race and scheduling risks:** Same as Candidate A or B.

**Exception/cancellation behavior:** Same as Candidate A or B.

**Fake handler and route-generator finally blocks:** Only the fake
generator finalizes. The route generator is not involved.

**Post-disconnect emissions:** None.

**Cleanup behavior:** Same as Candidate A or B.

**Framework coupling:** Coupled to Starlette. No coupling to flow2api
routes.

**Suitability for compatibility tests:** Low for flow2api-specific
behavior. Useful as a Starlette-behavior probe but does not exercise the
route generator's cancellation chain.

### Candidate F: Live Uvicorn/Socket Testing

**Description:** Start a real Uvicorn server, connect with a real HTTP
client, and disconnect the socket mid-stream.

**Disconnect mechanism simulated:** Real TCP socket close.

**Flow2api route exercised:** Yes — full production path.

**Proves disconnect detection:** Yes.

**Proves iterator cancellation:** Yes.

**Deterministic coordination:** Not deterministic. Depends on OS scheduling,
TCP buffering, Uvicorn internals.

**Race and scheduling risks:** High. Non-deterministic timing.

**Exception/cancellation behavior:** Real Uvicorn behavior.

**Fake handler and route-generator finally blocks:** Both execute (in
the live server context, not a controlled test environment).

**Post-disconnect emissions:** None (in theory).

**Cleanup behavior:** Full production cleanup.

**Framework coupling:** Coupled to Uvicorn version, OS, TCP stack.

**Suitability for compatibility tests:** None. Non-deterministic, requires
live server, not offline.

### 4.1 Comparison Summary

| Criterion | A | B | C | D | E | F |
|-----------|---|---|---|---|---|---|
| Route exercised | Yes | Yes | Yes | Yes | No | Yes |
| Disconnect proved | Yes | Indirect | No | No | Yes | Yes |
| Iterator cancellation proved | Yes | Partial | No | No | Partial | Yes |
| Deterministic | Yes (gated) | Yes | N/A | N/A | Yes (gated) | No |
| Generator finalization proved | Yes | No (GC) | N/A | N/A | Partial | Yes |
| Post-disconnect emission check | Yes | Yes | N/A | N/A | Yes | Partial |
| Offline | Yes | Yes | Yes | Yes | Yes | No |
| Framework coupling | High | High | Low | Low | High | Highest |
| Suitability | **High** | Moderate | None | None | Low | None |

---

## 5. Coordinated Receive-Side Disconnect Design — Determinism Analysis

### 5.1 Proposed Design

```
Invoke the returned StreamingResponse directly.
Use ASGI spec 2.0 (or omit spec_version).
receive() waits on an explicit synchronization event.
send() triggers that event only after recording a selected content body.
receive() then returns {"type": "http.disconnect"}.
Fake async generators with try/finally markers.
No sleep(), timeout guesses, or probabilistic ordering.
```

### 5.2 Synchronization Mechanism

```python
async def test_disconnect():
    chunk_recorded = asyncio.Event()
    handler_yield_gate = asyncio.Event()
    handler_yield_gate.set()  # Allow first yield
    sent_bodies = []
    route_gen_finalized = False
    handler_finalized = False

    async def fake_handler(model, prompt, **kwargs):
        nonlocal handler_finalized
        try:
            await handler_yield_gate  # Wait for permission to yield first chunk
            yield chunk_1
            handler_yield_gate.clear()  # Block before second yield
            await handler_yield_gate  # This await is the cancellation point
            yield chunk_2
        finally:
            handler_finalized = True

    async def receive():
        await chunk_recorded
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                sent_bodies.append(body)
            if len(sent_bodies) == 1:
                chunk_recorded.set()

    scope = {"type": "http", "asgi": {"spec_version": "2.0"}, ...}
    response = await route_function(...)
    await response(scope, receive, send)
    # Assertions:
    # - len(sent_bodies) == 1
    # - handler_finalized == True
    # - route_gen_finalized == True
    # - No more_body=False sent
```

### 5.3 Execution Trace

1. `__call__` creates task group, starts `stream_response` and
   `listen_for_disconnect`.
2. `stream_response` sends `http.response.start` (headers).
3. `stream_response` enters `async for chunk in body_iterator`.
4. Body iterator calls handler. Handler awaits `handler_yield_gate` (set,
   passes through).
5. Handler yields chunk_1. Route generator processes it, yields SSE-framed
   string.
6. `stream_response` calls `send(body_bytes_1)`.
7. `send()` appends to `sent_bodies` (len=1), sets `chunk_recorded`.
8. `send()` returns.
9. **Event loop scheduling point:** `stream_response` continues to `async
   for` next iteration. Meanwhile, `listen_for_disconnect` (which was
   awaiting `chunk_recorded`) is now unblocked.
10. **Race condition:** If `stream_response` reaches the next body_iterator
    `__anext__()` call before `listen_for_disconnect` runs, the handler may
    try to yield chunk_2. But `handler_yield_gate` was cleared after the
    first yield, so the handler blocks on `await handler_yield_gate`.
11. `listen_for_disconnect` runs: `receive()` returns immediately (event
    already set), returns `http.disconnect`, `listen_for_disconnect`
    breaks, `wrap()` calls `cancel_scope.cancel()`.
12. `CancelledError` propagates through the `async for` chain at await
    points: from `stream_response` through `body_iterator.__anext__()`
    into the route generator, reaching the handler at its
    `await handler_yield_gate.wait()` checkpoint.
13. Handler catches `CancelledError` (via `except BaseException`),
    re-raises it. Handler `finally` block executes.
14. `CancelledError` propagates back through the route generator. The
    route generator's `async for` over the handler exits due to the
    cancellation. The route generator's probe-only `finally` marker
    executes (test instrumentation, not production behavior).
15. Task group exits. Cancel scope suppresses the `CancelledError`.
    `collapse_excgroups` unwraps any single exception if needed.
    `__call__` returns normally.

### 5.4 Determinism Verdict

**The design is deterministic** when using a gated handler that blocks
before each yield after the first. The gate ensures:

- Only one content body is sent before the disconnect signal.
- The handler is at a known await point when cancellation arrives.
- No timing-dependent behavior exists.

**Without a gated handler**, the design is **not fully deterministic**
because the fast in-memory handler may yield all chunks before the event
loop schedules `listen_for_disconnect`. The number of content bodies sent
before cancellation would vary.

**Key synchronization primitives:**
- `asyncio.Event` for `chunk_recorded` (receive-side gate).
- `asyncio.Event` for `handler_yield_gate` (handler-side gate).
- No `asyncio.sleep()`, no `time.sleep()`, no timeout, no probabilistic
  ordering.

### 5.5 Distinctions

| Concept | What happens |
|---------|-------------|
| **Disconnect detection** | `listen_for_disconnect` receives `http.disconnect` and returns |
| **Cancellation of `stream_response`** | Task-group cancel scope sends `CancelledError` at the next await checkpoint |
| **Cancellation-driven unwinding** | `CancelledError` propagates through `async for` chain at await points; cancellation terminates the active frames; test-only `finally` markers execute during unwinding |
| **No `aclose()` invocation claimed** | Starlette 0.48.0 does not explicitly call `aclose()` on `body_iterator`; no separate explicit or implicit `aclose()` invocation is claimed; post-call `StopAsyncIteration` proves the iterator is terminated |
| **Test-harness finalization vs. application cleanup** | Proves synthetic `finally` blocks execute; does not prove application resource cleanup (no DB, network, tokens in test) |

---

## 6. Cancellation and Finalization Findings

### 6.1 Route Generators Have No try/finally

Inspection of `_iterate_openai_stream` (lines 717–737) and
`_iterate_gemini_stream` (lines 740–785) in `src/api/routes.py`:

- Neither generator has `try/finally` blocks.
- When cancelled, `CancelledError` propagates through the route generator
  at its current await point (inside the `async for` over the handler or
  at the `yield` suspension point).
- Cancellation-driven unwinding terminates the handler's active frame
  as `CancelledError` propagates through the `async for` chain.
- No cleanup code runs because there is none to run.
- The production `_iterate_openai_stream` and `_iterate_gemini_stream`
  generators have no `try/finally` blocks.

### 6.2 Fake Handlers Have No try/finally (Standard)

The `FakeStreamingHandler` and `FakeFailingHandler` used in Sprint
006G/006H tests have no `try/finally` blocks. For disconnect testing,
**gated fake handlers with try/finally markers** are needed to prove
cancellation-driven unwinding.

### 6.3 Cancellation-Driven Unwinding Is Deterministic for Path 1

In the task-group path (ASGI spec < 2.4):
- Cancel scope cancels `stream_response`.
- `CancelledError` propagates through the active `async for` chain at
  await points: from `stream_response` through `body_iterator.__anext__()`
  into the route generator, reaching the handler at its await checkpoint.
- The handler receives `CancelledError` (not `GeneratorExit`) at its
  current await point. `try/finally` blocks execute during unwinding.
- Cancellation-driven unwinding terminates the active frames of the
  handler and route generators as `CancelledError` propagates back
  through the `async for` chain.
- Starlette 0.48.0 does NOT explicitly call `aclose()` on `body_iterator`.
  No separate explicit or implicit `aclose()` invocation is claimed.
- With a gated handler at a known await point, both handler and route
  generator finalize deterministically.

### 6.4 Cleanup Is NOT Deterministic for Path 2

In the spec_version >= 2.4 path:
- `send()` raises `OSError`.
- `stream_response` propagates the exception.
- The body iterator is **abandoned** (not explicitly closed).
- Python's garbage collector eventually finalizes the abandoned generator.
- Timing is non-deterministic.

### 6.5 No Post-Disconnect Emissions

In both paths:
- The `more_body=False` final message is NOT sent after cancellation.
- No additional SSE events, `[DONE]`, or Gemini events appear.
- The response stream is incomplete from the client's perspective.

---

## 7. Recommended Seam for Next Implementation Sprint

**Candidate A: Direct StreamingResponse invocation with ASGI spec 2.0,
coordinated receive-side disconnect, and gated fake handler.**

### Rationale

1. **Exercises the full route:** The flow2api route function produces the
   `StreamingResponse`, which is then invoked with synthetic ASGI callables.
2. **Proves both disconnect detection and iterator cancellation:** The
   task-group path exercises both `listen_for_disconnect` and the cancel
   scope that interrupts `stream_response`.
3. **Deterministic with gated handlers:** Using `asyncio.Event` gates
   ensures exact control over when the handler yields and when the
   disconnect signal arrives.
4. **Proves cancellation-driven unwinding:** `CancelledError` propagates
   through the `async for` chain at await points. Cancellation terminates
   the active frames of the handler and route generators. Starlette 0.48.0
   does not explicitly call `aclose()` on the body iterator; no separate
   explicit or implicit `aclose()` invocation is claimed. The post-call
   `StopAsyncIteration` proves the returned body iterator is terminated.
5. **Exercises the default Starlette path:** TestClient, HTTPX
   ASGITransport, and real ASGI servers without spec_version 2.4 all use
   this path. Testing it ensures compatibility with the broadest deployment
   scenarios.
6. **Offline and deterministic:** No live server, no network, no timing
   dependency.

### Seam Construction

```python
# 1. Call the route function to get StreamingResponse
response = await create_chat_completion(request, raw_request, api_key=FAKE_API_KEY)

# 2. Invoke with ASGI spec 2.0 scope
scope = {"type": "http", "asgi": {"spec_version": "2.0"}, ...}
await response(scope, receive, send)

# 3. receive() blocks until send() signals, then returns http.disconnect
# 4. send() records bodies, signals receive() after first content body
# 5. Gated handler blocks before second yield
```

---

## 8. Proposed Test Matrix for Next Implementation Sprint

### 8.1 Test Count: One Test

The sprint recommends **exactly one test** on the OpenAI route. OpenAI and
Gemini share the same `StreamingResponse` receive-side cancellation path.
Gemini adds no distinct transport contract for this sprint. A second
Gemini test would duplicate the same Starlette cancel-scope behavior
without discovering any flow2api-specific difference.

### 8.2 Disconnect Contract Comparison: OpenAI vs. Gemini

| Aspect | OpenAI (`_iterate_openai_stream`) | Gemini (`_iterate_gemini_stream`) |
|--------|----------------------------------|----------------------------------|
| try/finally | No | No |
| Terminal sentinel | `data: [DONE]\n\n` after loop | None |
| Error payload handling | Propagates exception | Converts to Gemini error event, returns |
| Handler iteration | `async for` same pattern | `async for` same pattern |
| StreamingResponse path | Same cancel-scope + `async for` chain | Same cancel-scope + `async for` chain |

The disconnect contract is **structurally identical** for both generators:
neither has try/finally, both use `async for` on the handler, and both
are unwound by `CancelledError` propagating through the same `async for`
chain. The terminal sentinel (`[DONE]` vs. none) is irrelevant because
cancellation interrupts the loop before the sentinel is reached.

**Recommendation:** One test on the OpenAI route. A Gemini test adds no
new information about disconnect behavior.

### 8.3 Proposed Test: OpenAI Disconnect After First Chunk

**Route:** `create_chat_completion`
**Request:** Standard OpenAI streaming request
**Handler:** Gated `FakeStreamingHandler` with try/finally markers
**ASGI spec:** 2.0

**Assertions:**
- Exactly one content body sent (the first SSE-framed chunk).
- `more_body=False` NOT sent (no final empty body message).
- No `[DONE]` in any sent message.
- Route generator finalized (proved via try/finally marker).
- Handler generator finalized (proved via try/finally marker).
- `listen_for_disconnect` processed the `http.disconnect` message.
- Handler called exactly once.
- `__call__` returns normally (cancel scope suppresses cancellation).

**Explicit non-coverage:**
- Gemini disconnect (same structural contract, same StreamingResponse
  receive-side cancellation path — no distinct transport contract).
- ASGI spec 2.4 path.
- Backpressure.

---

## 9. Explicitly Deferred Behaviors

The following are explicitly out of scope for the next implementation sprint:

- **Backpressure and flow control:** Separate concern, deferred per sprint
  mandate.
- **Proxy buffering:** nginx, Cloudflare, and other proxy behavior.
- **TCP behavior:** Socket-level disconnect, half-close, RST packets.
- **Live server behavior:** Uvicorn, Gunicorn, or other ASGI server
  disconnect handling.
- **Production lifespan:** Startup/shutdown handlers.
- **Authentication and request validation:** Not exercised. Direct route
  calls supply the already-resolved `api_key` dependency parameter
  explicitly.
- **Runtime fixes:** No source code changes.
- **ASGI spec 2.4 path testing:** May be added in a future sprint as a
  separate concern.
- **Backpressure-induced cancellation:** Distinct from client disconnect.

---

## 10. Disposable Probe Guidance

A disposable uncommitted probe was executed during this sprint to
confirm cancellation and finalization behavior. See Section 12 for
probe observations and the corrected cancellation model.

---

## 11. Version Sensitivity

All findings are specific to:

- Starlette 0.48.0
- AnyIO 4.x (used by Starlette 0.48.0)
- Python 3.12 (async generator protocol)
- httpx 0.28.1 (ASGITransport scope construction)

Future Starlette versions may change:
- The `__call__` implementation
- The spec_version threshold
- The task-group or cancel-scope behavior
- The `listen_for_disconnect` implementation

Tests should document their Starlette version coupling.

---

## 12. Disposable Probe Observations

A synchronized probe was executed during this sprint using direct invocation
of a `StreamingResponse` wrapping a route generator with a gated fake
handler, ASGI spec_version `"2.0"`, `asyncio.Event` synchronization, and
no `sleep()` or timeout-based ordering.

### 12.1 Probe Configuration

- **ASGI spec_version:** `"2.0"` (task-group path)
- **Synchronization:** Two `asyncio.Event` instances — `chunk_recorded`
  (receive-side gate) and `handler_yield_gate` (handler-side gate)
- **Gated handler:** First yield passes (gate set), second yield blocked
  (gate cleared after first yield, then `await gate.wait()`)
- **Route generator:** `async for` over handler, SSE framing, `[DONE]`
  after loop, with `try/finally` marker
- **Handler:** `try/except BaseException/finally` with exception type
  capture and finalization marker

### 12.2 Observed Results

| Observation | Result |
|---|---|
| `response.__call__` return | Returns normally (no exception propagated) |
| Exception type inside handler | `asyncio.CancelledError` |
| Handler `finally` block | Ran |
| Route generator `finally` block | Ran |
| `response.body_iterator` post-call: `ag_frame` | `None` |
| `response.body_iterator` post-call: `ag_running` | `False` |
| `response.body_iterator.__anext__()` post-call | Raises `StopAsyncIteration` (behavioral confirmation of closure) |
| ASGI messages recorded | 2 total |
| `http.response.start` sent | Yes |
| Content body count (non-empty, `more_body=True`) | Exactly 1 |
| `[DONE]` present | No |
| Final `more_body=False` present | No |

### 12.3 ASGI Message Sequence

| Index | Type | Status | more_body | Body |
|-------|------|--------|-----------|------|
| 0 | `http.response.start` | 200 | — | — |
| 1 | `http.response.body` | — | `True` | `data: {"id": "chunk-1", "choices": [{"delta": {"content": "Hello"}}]}\n\n` |

### 12.4 Corrected Cancellation Model

Based on probe observations, the corrected model is:

1. `listen_for_disconnect` receives `http.disconnect` and returns.
2. The `wrap()` function cancels the task-group cancel scope.
3. The cancel scope sends `CancelledError` into the `stream_response`
   task at its next await checkpoint.
4. `CancelledError` propagates through the active `async for` chain:
   from `stream_response` through `body_iterator.__anext__()` into the
   route generator, reaching the handler at its await checkpoint.
5. The handler receives `CancelledError` (NOT `GeneratorExit`) at its
   current await point. The handler's `except BaseException` catches it,
   records the type, re-raises. The handler's `finally` block executes.
6. `CancelledError` propagates back through the route generator. The
   route generator's `async for` over the handler exits due to the
   cancellation. The route generator's probe-only `finally` marker
   executes (test instrumentation, not production behavior).
7. `CancelledError` reaches `stream_response`'s `async for` over
   `body_iterator`, which exits due to the cancellation.
8. The cancel scope suppresses the `CancelledError`. The task group
   exits. `__call__` returns normally.

### 12.5 Key Corrections from Probe

The following claims from initial source inspection were corrected
based on probe observations:

| Initial Claim | Corrected |
|---|---|
| `GeneratorExit` is the exception thrown into the handler | `CancelledError` is observed inside the handler |
| Starlette explicitly calls `aclose()` on `body_iterator` | Starlette 0.48.0 does NOT call `aclose()` on `body_iterator` in the pre-2.4 disconnect path; no separate explicit or implicit `aclose()` invocation is claimed |
| `GeneratorExit` is the normal exception for task-group cancellation | `CancelledError` is the primary exception observed; no `aclose()` invocation is claimed in the observed cancellation path |
| Generators finalize via explicit `GeneratorExit` injection | Generators are unwound by `CancelledError` propagating through the active `async for` chain |

### 12.6 Implications for Test Design

- **Proves cancellation-driven unwinding, not explicit closure:** The
  test demonstrates that `CancelledError` propagates through the chain
  and `finally` blocks execute. It does NOT prove that Starlette manages
  generator lifecycle.
- **Proves test-harness cleanup, not application cleanup:** The synthetic
  fake handler's `finally` block executes because `CancelledError` passes
  through it. This does not prove that real application resources (DB
  connections, network sockets, tokens) would be cleaned up.
- **Deterministic only with gated handlers:** The handler must have a
  deliberate await checkpoint for cancellation to arrive at a known
  location. Without gating, multiple chunks may be sent before the
  cancel scope takes effect.
- **Body iterator is behaviorally closed after `__call__`:** Post-call
  `__anext__()` raises `StopAsyncIteration`, confirming the generator
  is exhausted/closed. `ag_frame=None` and `ag_running=False` are
  supplemental observations.
