# Streaming Backpressure Seam Discovery

> **Sprint 006P — ASGI Send-Await Backpressure Seam Discovery**
> This document maps the Starlette send-await flow-control boundary,
> compares six candidate test approaches, analyzes a synchronized
> backpressure probe design, and recommends exactly one seam for
> the next implementation sprint.
>
> **Scope:** Application-level ASGI send-await flow control — the
> property that `StreamingResponse.stream_response` awaits `send()`
> for one body before requesting the next iterator value. This is
> termed "ASGI send-await flow control" or "application-level
> backpressure propagation."
>
> **Not in scope:** TCP backpressure, socket buffer behavior, client
> read speed, HTTP transfer behavior, proxy buffering, or deployed
> Uvicorn behavior.

---

## 1. Repository State at Sprint Start

| Item | Status |
|------|--------|
| Branch | `main` |
| Sprint 006O committed | **Yes** — Sprint 006O and correction commit present (commit `55efea5`) |
| Worktree | Clean |
| Installed Starlette | 0.48.0 |
| Installed httpx | 0.28.1 |
| Existing compatibility tests | 302 (all passing) |

---

## 2. Installed Framework Behavior Inspected

### 2.1 Starlette `StreamingResponse.stream_response` (0.48.0)

Source: `starlette/responses.py` lines 246–259.

```python
async def stream_response(self, send: Send) -> None:
    await send({
        "type": "http.response.start",
        "status": self.status_code,
        "headers": self.raw_headers,
    })
    async for chunk in self.body_iterator:
        if not isinstance(chunk, (bytes, memoryview)):
            chunk = chunk.encode(self.charset)
        await send({"type": "http.response.body", "body": chunk, "more_body": True})
    await send({"type": "http.response.body", "body": b"", "more_body": False})
```

**Send-await flow control property:** The `await send(...)` call for each
body chunk is a sequential await point. The `async for` loop does not
request the next value from `self.body_iterator` until `await send(...)`
returns. If `send()` blocks, the entire iteration pauses — the route
generator and handler generator cannot advance.

This is the application-level ASGI send-await flow-control boundary. It
is distinct from TCP-level, socket-level, or proxy-level flow control.

### 2.2 Starlette `StreamingResponse.__call__` (0.48.0)

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

**Two paths:**

- **spec_version >= 2.4:** Sequential `stream_response(send)`. No
  task-group, no disconnect listener. The send-await flow control is
  the only concurrency mechanism.
- **spec_version < 2.4:** Task-group with `listen_for_disconnect` racing
  against `stream_response`. The cancel scope may interrupt the send
  loop at any await point.

**For backpressure testing, spec_version "2.4" is the narrowest seam**
because it avoids receive-side cancellation and task-group scheduling,
isolating the sequential send-await loop.

### 2.3 Route Generators

**`_iterate_openai_stream`** (routes.py lines 717–737):

```python
async def _iterate_openai_stream(normalized, base_url_override=None):
    handler = _ensure_generation_handler()
    async for chunk in handler.handle_generation(..., stream=True, ...):
        if chunk.startswith("data: "):
            yield chunk
            continue
        payload = _parse_handler_result(chunk)
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
```

**`_iterate_gemini_stream`** (routes.py lines 740–786):

```python
async def _iterate_gemini_stream(normalized, response_model, base_url_override=None):
    handler = _ensure_generation_handler()
    async for chunk in handler.handle_generation(..., stream=True, ...):
        # ... conversion and framing ...
        if event:
            yield event
```

Both generators:
- Use `async for` on `handler.handle_generation(...)`.
- Have no `try/finally` blocks.
- Yield strings that `stream_response` encodes to bytes.

**Backpressure chain:** `stream_response` awaits `send()` → `send()`
blocks → `async for chunk in body_iterator` pauses → route generator
`yield` suspension is not resumed → `async for chunk in handler.handle_generation(...)`
pauses → handler generator `yield` suspension is not resumed.

The entire chain is frozen at the `await send(...)` boundary.

---

## 3. Candidate Approach Comparison

### Candidate A: Direct StreamingResponse Invocation — ASGI Spec 2.4 with Gated Send

**Description:** Invoke the `StreamingResponse` returned by a flow2api
route directly with `spec_version = "2.4"`, a gated `send()` callable
that blocks on the first content body, and a gated fake handler that
blocks before yielding the second chunk.

**Flow2api route exercised:** Yes — the full route function produces the
`StreamingResponse`.

**Starlette's real `await send(...)` boundary exercised:** Yes —
`stream_response` calls the test-supplied `send()` through the real
Starlette code path.

**Disconnect/cancellation involved:** No — spec_version "2.4" bypasses
the task-group and disconnect listener entirely.

**Downstream blocking deterministic:** Yes — `send()` blocks on an
`asyncio.Event`. No timing, sleep, or polling.

**Handler advancement observable:** Yes — a second `asyncio.Event`
(`second_chunk_requested`) is set by the handler when the generator
is asked for the next value after the first yield.

**Proves:** Blocked `send()` prevents the body_iterator and handler
from advancing. When `send()` is released, the iteration resumes
normally.

**Cannot prove:** TCP backpressure, socket buffer behavior, client
read speed, HTTP transfer behavior, proxy buffering, deployed Uvicorn
behavior.

**Race or scheduling concerns:** None. The `asyncio.Event` provides
exact synchronization. The event loop scheduling does not affect the
ordering because the handler blocks on an explicit await.

**Cleanup behavior:** Normal completion. The generator exhausts,
`stream_response` sends the final `more_body=False` message,
`__call__` returns normally.

**Version coupling:** Coupled to Starlette 0.48.0 `stream_response`
implementation and the spec_version "2.4" code path.

**Suitability for offline compatibility tests:** High.

### Candidate B: Direct Invocation — ASGI Spec 2.0 with Gated Send and Blocked Receive

**Description:** Same as Candidate A but with `spec_version = "2.0"`,
activating the task-group path. `receive()` remains blocked on an
event (never returns `http.disconnect`).

**Flow2api route exercised:** Yes.

**Starlette's real `await send(...)` boundary exercised:** Yes.

**Disconnect/cancellation involved:** Yes — the task-group and
`listen_for_disconnect` are active. If `receive()` blocks indefinitely,
the task-group waits for either `stream_response` or
`listen_for_disconnect` to complete.

**Downstream blocking deterministic:** Yes, but the task-group adds
complexity. The `listen_for_disconnect` coroutine is also running,
consuming event-loop scheduling time.

**Handler advancement observable:** Yes.

**Proves:** Same as A, plus confirms that backpressure works in the
default task-group path.

**Cannot prove:** Same as A.

**Race or scheduling concerns:** Low. The task-group path introduces
`listen_for_disconnect` as a concurrent coroutine. While this does not
affect the send-await ordering, it adds scheduling complexity that is
not relevant to the backpressure question.

**Cleanup behavior:** Normal completion when `stream_response` finishes
first, the `wrap()` function cancels the scope, and
`listen_for_disconnect` is cancelled.

**Version coupling:** Coupled to Starlette 0.48.0 task-group internals.

**Suitability for offline compatibility tests:** Moderate. The task-group
path is the default but adds complexity not needed for the backpressure
question.

### Candidate C: Direct body_iterator Iteration with Gated Test Consumer

**Description:** Iterate `response.body_iterator` directly with a test
consumer that blocks between iterations.

**Flow2api route exercised:** Yes — the route function produces the
`StreamingResponse`.

**Starlette's real `await send(...)` boundary exercised:** **No.**
Direct iteration bypasses `stream_response` and `__call__` entirely.
The `send()` callable is not involved.

**Disconnect/cancellation involved:** No.

**Downstream blocking deterministic:** Yes — the test consumer controls
iteration timing.

**Handler advancement observable:** Yes — the generator suspension is
observable.

**Proves:** The route generator and handler pause when the consumer
does not request the next value.

**Cannot prove:** That `send()` is the actual blocking point in the
real Starlette send loop. This tests generator suspension, not ASGI
send-await flow control.

**Race or scheduling concerns:** None.

**Cleanup behavior:** Generator exhausts normally.

**Version coupling:** Low — no Starlette internals exercised.

**Suitability for offline compatibility tests:** Low for the
backpressure question. Does not exercise the `send()` boundary.

### Candidate D: Test-Local FastAPI + TestClient

**Description:** Build a test-local FastAPI app and use TestClient.

**Flow2api route exercised:** Yes.

**Starlette's real `await send(...)` boundary exercised:** Partially —
TestClient's internal send callable fully buffers the response. The
`send()` callable returns immediately for each message because it writes
to an in-memory `BytesIO`.

**Disconnect/cancellation involved:** No disconnect mechanism.

**Downstream blocking deterministic:** **No.** TestClient cannot create
downstream blocking. All sends complete immediately.

**Handler advancement observable:** **No.** All chunks are produced and
buffered before the response is returned.

**Proves:** Complete response content.

**Cannot prove:** Backpressure, flow control, send-blocking behavior.

**Race or scheduling concerns:** Not applicable.

**Cleanup behavior:** Normal completion.

**Version coupling:** Low.

**Suitability for offline compatibility tests:** None for backpressure.

### Candidate E: HTTPX ASGITransport

**Description:** Use `httpx.AsyncClient(transport=httpx.ASGITransport(app))`.

**Flow2api route exercised:** Yes.

**Starlette's real `await send(...)` boundary exercised:** Partially —
ASGITransport's send callable records messages in a list and returns
immediately. No blocking is possible.

**Disconnect/cancellation involved:** No.

**Downstream blocking deterministic:** **No.** Same as TestClient —
sends complete immediately.

**Handler advancement observable:** **No.**

**Proves:** Complete response content.

**Cannot prove:** Backpressure or flow control.

**Race or scheduling concerns:** Not applicable.

**Cleanup behavior:** Normal completion.

**Version coupling:** Low.

**Suitability for offline compatibility tests:** None for backpressure.

### Candidate F: Live Uvicorn/Socket Testing

**Description:** Start a real Uvicorn server and use a real HTTP client.

**Flow2api route exercised:** Yes — full production path.

**Starlette's real `await send(...)` boundary exercised:** Yes — real
Uvicorn send callable with real TCP socket behavior.

**Disconnect/cancellation involved:** Potentially — real socket
disconnect, half-close, RST.

**Downstream blocking deterministic:** **No.** Depends on OS scheduling,
TCP buffering, kernel socket buffers, Uvicorn internals.

**Handler advancement observable:** **Not deterministically.** Timing
depends on the full stack.

**Proves:** Real deployed behavior.

**Cannot prove:** Deterministic causality between send-blocking and
handler pausing.

**Race or scheduling concerns:** High. Non-deterministic.

**Cleanup behavior:** Real server cleanup.

**Version coupling:** Coupled to Uvicorn version, OS, TCP stack.

**Suitability for offline compatibility tests:** None. Non-deterministic,
requires live server, not offline.

### 3.1 Comparison Summary

| Criterion | A | B | C | D | E | F |
|-----------|---|---|---|---|---|---|
| Route exercised | Yes | Yes | Yes | Yes | Yes | Yes |
| Real `await send()` exercised | Yes | Yes | No | Partial | Partial | Yes |
| Disconnect/cancellation involved | No | Yes | No | No | No | Maybe |
| Downstream blocking deterministic | Yes | Yes | Yes | No | No | No |
| Handler advancement observable | Yes | Yes | Yes | No | No | No |
| Proves send-await flow control | **Yes** | Yes | No | No | No | Partially |
| Offline | Yes | Yes | Yes | Yes | Yes | No |
| Framework coupling | High | Highest | Low | Low | Low | Highest |
| Suitability | **High** | Moderate | Low | None | None | None |

---

## 4. Synchronized Backpressure Design — Evaluation

### 4.1 Proposed Design

```
Use ASGI spec_version "2.4" to isolate sequential stream_response.
Directly call the OpenAI streaming route and obtain its StreamingResponse.
Start response(scope, receive, send) in an async task.
Fake handler yields a first deterministic chunk.
Code after that first yield sets second_chunk_requested.
The fake handler then blocks on release_second_chunk.
send() records response.start normally.
On the first non-empty body, send():
  - records the message
  - sets first_body_send_entered
  - blocks on release_first_body_send
Test orchestration waits for first_body_send_entered.
While the first send is blocked, verify second_chunk_requested is NOT set.
Release release_first_body_send.
Verify second_chunk_requested becomes set.
Release release_second_chunk and allow normal stream completion.
```

### 4.2 Synchronization Mechanism

```python
async def test_backpressure():
    first_body_send_entered = asyncio.Event()
    release_first_body_send = asyncio.Event()
    second_chunk_requested = asyncio.Event()
    release_second_chunk = asyncio.Event()

    async def gated_handler(model, prompt, **kwargs):
        yield first_chunk
        second_chunk_requested.set()
        await release_second_chunk.wait()
        yield second_chunk

    async def gated_send(message):
        messages.append(message)
        if message["type"] == "http.response.body" and more_body and first:
            first_body_send_entered.set()
            await release_first_body_send.wait()

    response_task = asyncio.create_task(response(scope, receive, send))
    await first_body_send_entered.wait()
    assert not second_chunk_requested.is_set()  # KEY ASSERTION
    release_first_body_send.set()
    await second_chunk_requested.wait()
    release_second_chunk.set()
    await response_task
```

### 4.3 Execution Trace

1. `asyncio.create_task` starts `response.__call__`.
2. `__call__` (spec_version 2.4) calls `stream_response(send)`.
3. `stream_response` sends `http.response.start` — `send()` records it
   normally.
4. `stream_response` enters `async for chunk in body_iterator`.
5. Body iterator calls `_iterate_openai_stream.__anext__()`.
6. `_iterate_openai_stream` calls `handler.handle_generation(...)`.
7. Handler yields `first_chunk`.
8. `_iterate_openai_stream` processes the chunk, yields an SSE-framed string.
9. `stream_response` encodes the string to bytes.
10. `stream_response` calls `await send(body_bytes)`.
11. `send()` records the message, sets `first_body_send_entered`, blocks
    on `release_first_body_send`.
12. **At this point, `stream_response` is paused at `await send(...)`.**
13. Test orchestration checks `second_chunk_requested` — **NOT set.**
14. Test releases `release_first_body_send`.
15. `send()` returns.
16. `stream_response` continues to the next `async for` iteration.
17. `_iterate_openai_stream` requests the next handler value.
18. Handler code after the first yield executes: `second_chunk_requested.set()`.
19. Handler blocks on `release_second_chunk.wait()`.
20. Test observes `second_chunk_requested` is now set.
21. Test releases `release_second_chunk`.
22. Handler yields `second_chunk`.
23. Normal stream completion: [DONE], final `more_body=False`.

### 4.4 Determinism Verdict

**The design is fully deterministic.** All ordering is controlled by
`asyncio.Event` instances. No `sleep()`, timeout, polling, or
probabilistic ordering is involved.

### 4.5 Probe Results

A disposable probe was executed using this design. Results:

| Observation | Result |
|---|---|
| `second_chunk_requested` set while send blocked | **No** |
| `second_chunk_requested` set after send released | **Yes** |
| Total ASGI messages | 5 (1 start + 3 content + 1 final) |
| Content bodies | 3 (2 handler chunks + [DONE]) |
| Final `more_body=False` | Present |
| Handler calls | 1 |
| Normal completion | Yes |

**Finding:** Blocked `send()` deterministically prevents the route
generator and handler iterator from advancing. This confirms
application-level ASGI send-await flow control in Starlette 0.48.0.

---

## 5. Recommended Seam

**Candidate A: Direct StreamingResponse invocation with ASGI spec_version
"2.4" and a gated send callable.**

### Rationale

1. **Exercises the real Starlette send-await boundary:** The test-supplied
   `send()` is called through the real `stream_response` code path.
2. **Deterministic:** `asyncio.Event` provides exact synchronization.
3. **Isolates the backpressure question:** spec_version "2.4" avoids
   task-group, disconnect listener, and receive-side cancellation.
4. **Exercises the full route:** The flow2api route function produces the
   `StreamingResponse`, exercising the route generator and handler chain.
5. **Offline and deterministic:** No live server, no network, no timing
   dependency.
6. **Minimal complexity:** No task-group, no cancel scope, no
   `listen_for_disconnect`.

### Seam Construction

```python
# 1. Call the route function to get StreamingResponse
response = await create_chat_completion(request, raw_request, api_key="test-key")

# 2. Invoke with ASGI spec 2.4 scope
scope = {"type": "http", "asgi": {"spec_version": "2.4"}, ...}
response_task = asyncio.create_task(response(scope, receive, send))

# 3. send() blocks on first content body via asyncio.Event
# 4. Handler blocks before second yield via asyncio.Event
# 5. Test verifies handler not advanced while send blocked
# 6. Release gates and verify normal completion
```

---

## 6. Proposed Test Matrix for Next Implementation Sprint

### 6.1 Test Count: One Test

The sprint recommends **exactly one test** on the OpenAI route.

### 6.2 OpenAI vs. Gemini Send-Await Contract

| Aspect | OpenAI (`_iterate_openai_stream`) | Gemini (`_iterate_gemini_stream`) |
|--------|----------------------------------|----------------------------------|
| Generator type | async generator | async generator |
| Handler iteration | `async for` same pattern | `async for` same pattern |
| Send-await chain | Same `stream_response` path | Same `stream_response` path |
| Terminal sentinel | `data: [DONE]\n\n` | None |
| Framing | SSE `data:` prefix | SSE `data:` prefix |

The send-await backpressure contract is **structurally identical** for both
generators: both use `async for` on the handler, both yield strings to
`stream_response`, and both are subject to the same `await send(...)` pause.
The terminal sentinel and framing differences do not affect the send-await
flow-control behavior.

**Recommendation:** One test on the OpenAI route. A Gemini test adds no
new information about send-await flow control.

### 6.3 Proposed Test: OpenAI Send-Await Backpressure

**Route:** `create_chat_completion`
**Request:** Standard OpenAI streaming request
**Handler:** Gated fake handler with `second_chunk_requested` and
`release_second_chunk` events
**ASGI spec:** 2.4

**Assertions:**
- While the first `send()` is blocked, `second_chunk_requested` is NOT set.
- After releasing the first `send()`, `second_chunk_requested` becomes set.
- Stream completes normally after releasing all gates.
- `http.response.start` sent with status 200.
- Expected content bodies sent (handler chunks + [DONE]).
- Final `more_body=False` sent.
- Handler called exactly once.

**Explicit non-coverage:**
- Gemini send-await (same structural contract, same StreamingResponse
  send loop).
- ASGI spec 2.0 task-group path.
- TCP, socket, proxy, or client-level backpressure.
- Disconnect or cancellation behavior.

---

## 7. Explicitly Deferred Behaviors

The following are explicitly out of scope for the next implementation sprint:

- **Disconnect and cancellation:** Separate concern, handled by Sprint 006N
  (seam discovery) and Sprint 006O (implementation). Backpressure is a
  distinct concept from client disconnect.
- **TCP backpressure:** Socket-level flow control.
- **Proxy buffering:** nginx, Cloudflare, and other proxy behavior.
- **Client read speed:** How fast a client consumes the response.
- **HTTP transfer behavior:** Chunked encoding, HTTP/2 flow control.
- **Deployed Uvicorn behavior:** Real server send-blocking.
- **ASGI spec 2.0 backpressure:** May be added in a future sprint.
- **Production lifespan:** Startup/shutdown handlers.
- **Authentication and request validation:** Not exercised.

---

## 8. Version Sensitivity

All findings are specific to:

- Starlette 0.48.0
- AnyIO 4.x (used by Starlette 0.48.0)
- Python 3.12 (async generator protocol)

Future Starlette versions may change:
- The `stream_response` implementation
- The `__call__` implementation
- The spec_version threshold

Tests should document their Starlette version coupling.

---

## 9. Relationship to Other Streaming Concerns

| Concern | Sprint | Mechanism |
|---------|--------|-----------|
| Send-loop message sequence | 006K/006K.1 | `stream_response` sends start, body, final |
| Disconnect/cancellation | 006N/006O | `listen_for_disconnect` + cancel scope |
| **Send-await backpressure** | **006P** | **`await send(...)` pauses iteration** |

These three concerns are independent:
- Sprint 006K proved what messages are sent and in what order.
- Sprint 006O proved how disconnect interrupts the send loop.
- Sprint 006P proves that the send loop pauses when `send()` blocks.

---

## 10. Confirmation

- No generation routes were invoked during discovery (source inspection only).
- No `StreamingResponse` was constructed or consumed (except the disposable probe).
- No FastAPI app was created.
- No TestClient or ASGI transport was used.
- No production services were instantiated.
- No network calls were made.
- No runtime source (`src/`) was modified.
- No fixtures were added.
- No dependencies were added.
- No commits or pushes were performed.
- The disposable probe was created, executed, and deleted.
