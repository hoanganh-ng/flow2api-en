# Sprint 006N — Streaming Disconnect and Cancellation Seam Discovery

| Field | Value |
|-------|-------|
| Sprint ID | 006N |
| Type | Documentation-only (discovery) |
| Predecessor | Sprint 006M |
| Status | Completed |

---

## 1. Objective

Map the Starlette `StreamingResponse` disconnect and cancellation paths,
compare six candidate test approaches (A–F), determine whether a coordinated
receive-side disconnect design is deterministic, and recommend exactly one
seam with exactly one test for the next implementation sprint.

This sprint adds **no tests and no runtime changes**. It produces two
documentation files and updates four existing project documents.

---

## 2. Scope

### In scope

- Inspect installed Starlette 0.48.0 source for:
  - `StreamingResponse.__call__`
  - `StreamingResponse.listen_for_disconnect`
  - `StreamingResponse.stream_response`
  - `starlette._utils.collapse_excgroups`
  - AnyIO task-group and cancellation behavior
- Inspect httpx 0.28.1 `ASGITransport` scope construction.
- Inspect five existing streaming test files for patterns and coverage gaps.
- Map two ASGI spec paths separately:
  - Spec below 2.4: receive-side `http.disconnect`, task-group cancellation,
    stream iterator cancellation-driven unwinding.
  - Spec 2.4 or newer: send raises OSError, conversion to ClientDisconnect,
    resulting iterator behavior.
- Compare six candidates (A–F) across twelve evaluation criteria.
- Analyze determinism of coordinated receive-side disconnect with gated
  fake handlers.
- Clearly distinguish: disconnect detection, cancellation of
  `stream_response`, cancellation-driven unwinding of route async
  generator, cancellation-driven unwinding of fake handler async
  generator, test-harness cleanup vs. application resource cleanup.
- Recommend exactly one seam.
- Recommend exactly one test (OpenAI route).
- Create two new documentation files.
- Update four existing documentation files.

### Out of scope

- Adding disconnect tests (deferred to next implementation sprint)
- Runtime source changes
- Test file changes
- Backpressure and flow control
- Proxy buffering
- TCP behavior
- Live server behavior
- Production lifespan
- Authentication and request validation
- Runtime fixes
- Dependency upgrades
- Committing or pushing

---

## 3. Prerequisites Verified

| Check | Result |
|-------|--------|
| Branch | `main` |
| Sprint 006M committed | **Yes** — committed and pushed (commit `9df3666`) |
| Worktree unrelated changes | None |
| Compatibility suite baseline | 301 tests, OK |
| `git diff -- src` | No output |
| `git diff -- tests` | No output |
| `git diff -- requirements.txt pyproject.toml` | No output |

Sprint 006M is committed and pushed. Sprint 006N does not modify
or interfere with Sprint 006M files.

---

## 4. Framework Source Inspection

### 4.1 Starlette 0.48.0 `StreamingResponse.__call__`

The `__call__` method evaluates `scope.get("asgi", {}).get("spec_version",
"2.0")` and branches:

- **spec_version < (2, 4):** Creates an `anyio` task group with two tasks:
  `stream_response(send)` started via `start_soon` and
  `listen_for_disconnect(receive)` awaited directly. Both are wrapped in
  `wrap()`, which cancels the scope when either task completes.
  `collapse_excgroups()` unwraps single-exception groups.

- **spec_version >= (2, 4):** Calls `await self.stream_response(send)`
  directly, catches `OSError`, raises `ClientDisconnect`.

### 4.2 `listen_for_disconnect`

Loops calling `await receive()` until `message["type"] ==
"http.disconnect"`, then returns. In the task-group path, returning
triggers `wrap()` → `cancel_scope.cancel()` → cancellation of
`stream_response`.

### 4.3 `stream_response`

Sends `http.response.start`, iterates `self.body_iterator` sending each
chunk as `http.response.body` with `more_body=True`, then sends a final
empty body with `more_body=False`. If interrupted, the final message is
never sent.

### 4.4 `collapse_excgroups`

Context manager that unwraps `BaseExceptionGroup` instances containing
exactly one exception. Prevents single-cancellation exceptions from
appearing wrapped in an ExceptionGroup to the caller.

### 4.5 ASGI Spec Version in Test Transports

- **Starlette TestClient:** Does not set `spec_version` in its ASGI scope.
- **HTTPX ASGITransport (0.28.1):** Sets `"asgi": {"version": "3.0"}` but
  does NOT set `"spec_version"`.
- Both default to `"2.0"` → both use the **task-group path**.

---

## 5. Route Generator Inspection

### 5.1 `_iterate_openai_stream` (routes.py lines 717–737)

- No `try/finally` blocks.
- Iterates `handler.handle_generation(...)` with `async for`.
- After loop completes, yields `"data: [DONE]\n\n"`.
- On cancellation: `CancelledError` propagates through the `async for`
  chain at await points. Cancellation-driven unwinding terminates the
  handler's active frame. No `[DONE]` emitted. Starlette 0.48.0 does
  NOT explicitly call `aclose()`; no separate explicit or implicit
  `aclose()` invocation is claimed.

### 5.2 `_iterate_gemini_stream` (routes.py lines 740–785)

- No `try/finally` blocks.
- Iterates handler with `async for`.
- No terminal sentinel after loop.
- Error payload path: explicit `return` after yielding Gemini error event.
- On cancellation: same cancellation-driven unwinding chain as OpenAI.

### 5.3 Route Functions

- `create_chat_completion` (lines 851–889): Returns `StreamingResponse`
  wrapping `_iterate_openai_stream`. Route try/except catches exceptions
  from request processing but NOT from generator iteration.
- `stream_generate_content` (lines 940–973): Returns `StreamingResponse`
  wrapping `_iterate_gemini_stream`. Route try/except catches exceptions
  from request processing but NOT from generator iteration.

---

## 6. Existing Test Coverage

### 6.1 Sprint 006G — OpenAI Streaming Generator Contract (18 tests)

Tests `_iterate_openai_stream` directly. Covers SSE framing, [DONE]
termination, handler exception propagation. Does NOT test disconnect,
cancellation, or `StreamingResponse.__call__`.

### 6.2 Sprint 006H — Gemini Streaming Generator Contract (41 tests)

Tests `_iterate_gemini_stream` directly. Covers Gemini event framing,
finish-reason mapping, error payload conversion. Does NOT test disconnect
or cancellation.

### 6.3 Sprint 006J — StreamingResponse Wrapper (8 tests)

Tests `StreamingResponse` construction and `body_iterator` consumption.
Does NOT test `__call__`, disconnect, or cancellation.

### 6.4 Sprint 006K — ASGI Send-Loop (6 tests)

Tests `StreamingResponse.__call__` with ASGI spec 2.4 scope. Uses the
simple `stream_response` path. Does NOT test `listen_for_disconnect`,
task-group cancellation, or disconnect detection.

### 6.5 Sprint 006M — HTTP-Level Streaming Routes (2 tests)

Tests via TestClient (fully buffered). Does NOT test disconnect,
cancellation, or incremental delivery.

### 6.6 Coverage Gap

No existing test covers:
- `listen_for_disconnect` behavior.
- Task-group cancellation of `stream_response`.
- `CancelledError` propagation through route generators during disconnect.
- Handler cancellation-driven unwinding during disconnect.
- Post-disconnect emission absence (no `[DONE]`, no `more_body=False`).

---

## 7. Candidate Comparison Summary

See [STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md](../STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md)
Section 4 for the full comparison table.

**Recommended:** Candidate A — Direct StreamingResponse invocation with ASGI
spec 2.0, coordinated receive-side disconnect, and gated fake handler.

**Rationale:** Exercises the actual flow2api route, proves both disconnect
detection and iterator cancellation, is deterministic with gated handlers,
and exercises the default Starlette path used by TestClient and HTTPX.

---

## 8. Determinism Findings

The coordinated receive-side disconnect design **is deterministic** when
using gated fake handlers:

1. `asyncio.Event` gates `receive()` — it blocks until `send()` has
   recorded a selected content body.
2. A second `asyncio.Event` gates the handler — it blocks before each
   yield after the first, ensuring the handler is at a known await point
   when cancellation arrives.
3. No `sleep()`, timeout guesses, or probabilistic ordering.

Without gated handlers, the design is **not fully deterministic** because
the fast in-memory handler may yield all chunks before the event loop
schedules `listen_for_disconnect`.

---

## 9. Recommended Seam and Test Matrix

### 9.1 Recommended Seam

Direct `StreamingResponse` invocation with:
- ASGI spec 2.0 (or omitted spec_version).
- Coordinated `receive()` using `asyncio.Event` gate.
- Recording `send()` that signals `receive()` after first content body.
- Gated `FakeStreamingHandler` with try/finally markers.
- Fake handler blocks on `asyncio.Event` before each yield after the first.

### 9.2 Proposed Test (exactly 1)

**Test: OpenAI disconnect after first chunk**

- Route: `create_chat_completion`
- Gated handler yields 2+ chunks with try/finally markers
- Assertions:
  - Exactly 1 content body sent
  - No `[DONE]` in any sent message
  - No `more_body=False` sent
  - Route generator finalized (try/finally marker set)
  - Handler generator finalized (try/finally marker set)
  - Handler called exactly once
  - `__call__` returns normally

**No Gemini test.** OpenAI and Gemini share the same `StreamingResponse`
receive-side cancellation path. Both use `async for` on the handler,
neither has try/finally, and both are unwound by `CancelledError`
propagating through the same `async for` chain. Gemini adds no distinct
transport contract for this sprint.

---

## 10. Deliverables

| Deliverable | Status |
|-------------|--------|
| docs/STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md | Created |
| docs/SPRINTS/SPRINT-006N-streaming-disconnect-cancellation-seam-discovery.md | Created |
| docs/PROJECT_STATE.md updated | Updated |
| docs/SPRINTS/README.md updated | Updated |
| docs/TEST_HARNESS_PLAN.md updated | Updated |
| docs/STREAMING_TRANSPORT_TEST_PLAN.md updated | Updated |
| No src/ changes | Confirmed |
| No tests/ changes | Confirmed |
| No requirements.txt/pyproject.toml changes | Confirmed |

---

## 11. Verification

```
python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# Expected: 301 tests, OK

git diff -- src
# Expected: no output

git diff -- tests
# Expected: no output

git diff -- requirements.txt pyproject.toml
# Expected: no output

git diff --check
# Expected: no output
```

---

## 12. Explicitly Deferred

- Backpressure and flow control
- Proxy buffering
- TCP behavior
- Live server behavior
- Production lifespan
- Authentication and request validation
- Runtime fixes
- ASGI spec 2.4 disconnect path testing
- Client disconnect test implementation (deferred to next sprint)
- Any test file modifications

---

## 13. Disposable Probe Observations

A synchronized probe was executed during this sprint to verify
cancellation and finalization behavior. The probe used direct invocation
of `StreamingResponse` with ASGI spec `"2.0"`, `asyncio.Event`
synchronization, a gated fake handler, and no `sleep()` or timeout.

### Key Findings

| Observation | Result |
|---|---|
| `response.__call__` return | Returns normally |
| Exception type inside handler | `asyncio.CancelledError` (NOT `GeneratorExit`) |
| Handler `finally` block | Ran |
| Route generator `finally` block | Ran |
| Body iterator post-call `__anext__()` | Raises `StopAsyncIteration` |
| Content body count | Exactly 1 |
| `[DONE]` present | No |
| `more_body=False` present | No |

### Corrected Cancellation Model

1. Cancel scope sends `CancelledError` into `stream_response`.
2. `CancelledError` propagates through the active `async for` chain at
   await points.
3. Handler receives `CancelledError` (not `GeneratorExit`).
4. Cancellation-driven unwinding terminates the active frames of the
   handler and route generators as `CancelledError` propagates through
   the `async for` chain. Starlette 0.48.0 does NOT explicitly call
   `aclose()` on `body_iterator`; no separate explicit or implicit
   `aclose()` invocation is claimed.
5. Cancel scope suppresses `CancelledError`. `__call__` returns normally.

See [STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md](../STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md)
Section 12 for full probe details and ASGI message sequence.
