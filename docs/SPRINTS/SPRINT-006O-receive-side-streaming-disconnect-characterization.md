# Sprint 006O — Receive-Side Streaming Disconnect Characterization

| Field | Value |
|-------|-------|
| Sprint ID | 006O |
| Type | Implementation (test) |
| Predecessor | Sprint 006N |
| Status | Completed |

---

## 1. Objective

Implement exactly one test characterizing receive-side `http.disconnect`
and cancellation-driven stream termination for Starlette 0.48.0's
pre-2.4 `StreamingResponse` path on the OpenAI streaming route.

This sprint proves:

- Exactly one content body was sent before disconnect.
- The route body iterator terminated.
- The fake handler observed `asyncio.CancelledError`.
- The handler's test-only `finally` block ran.
- `response.__call__` returned normally.

This sprint does **not** prove real TCP disconnection, deployed-server
behavior, or production resource cleanup.

---

## 2. Scope

### In scope

- One test: `test_openai_receive_side_disconnect_after_first_body`
- Patching `src.api.routes.generation_handler` with a deterministic
  gated fake handler
- Calling `create_chat_completion` directly with a valid request,
  synthetic `Request`, and explicitly supplied `api_key`
- Invoking the returned `StreamingResponse` directly with:
  - HTTP ASGI scope with `spec_version` `"2.0"`
  - A coordinated `receive` callable
  - A recording `send` callable
- Explicit `asyncio.Event` synchronization (no `sleep` or timing guesses)
- Assertions on exact ASGI message sequence, cancellation behavior,
  handler instrumentation, and post-call iterator termination

### Out of scope

- Gemini disconnect test (shares the same `StreamingResponse`
  cancellation path; no distinct transport contract)
- Immediate-disconnect test
- ASGI spec 2.4 `OSError` test
- Backpressure and flow control
- Proxy buffering
- TCP behavior
- Live server behavior
- Production lifespan
- Authentication and request validation
- Runtime source changes
- Dependency upgrades
- TestClient, HTTPX, or any HTTP transport
- Committing or pushing

---

## 3. Prerequisites Verified

| Check | Result |
|-------|--------|
| Branch | `main` |
| Sprint 006N committed | **Yes** — committed (commit `eb6e81c`) |
| Worktree unrelated changes | None |
| Compatibility suite baseline | 301 tests, OK |
| `git diff -- src` | No output |
| `git diff -- requirements.txt pyproject.toml` | No output |

---

## 4. Test Design

### 4.1 Synchronization Sequence

Three `asyncio.Event` instances coordinate the test deterministically:

| Event | Purpose |
|-------|---------|
| `first_body_sent` | Set by `send()` after recording the first content body |
| `handler_waiting_for_next` | Set by the fake handler after yielding the first chunk, before blocking |
| `handler_continue` | Never released; the handler blocks here until cancellation arrives |

**Execution trace:**

1. The fake handler yields one deterministic OpenAI JSON chunk
   containing `Xin chào — 世界`.
2. `_iterate_openai_stream` parses the handler result, re-serializes
   it with `ensure_ascii=False`, and yields an SSE-framed Python string.
3. `StreamingResponse.stream_response` encodes that string using
   UTF-8 before passing the `http.response.body` message to `send()`.
   The recorded ASGI body is therefore bytes.
4. `send()` records the message and signals `first_body_sent`.
5. `stream_response` asks the body iterator for another value.
6. The body iterator asks the handler for its next yield.
7. The handler signals `handler_waiting_for_next` and blocks awaiting
   `handler_continue`.
8. `receive()` waits for both `first_body_sent` and
   `handler_waiting_for_next`.
9. `receive()` returns `{"type": "http.disconnect"}`.
10. `listen_for_disconnect` returns, `wrap()` cancels the task-group
    cancel scope.
11. `CancelledError` propagates through the `async for` chain at await
    points, reaching the handler at its `await handler_continue.wait()`
    checkpoint.
12. The handler records `asyncio.CancelledError`, re-raises it, and its
    `finally` block runs.
13. The cancel scope suppresses the `CancelledError`. `__call__`
    returns normally.

### 4.2 Fake Handler Instrumentation

`GatedFakeStreamingHandler` records:

- All invocation arguments (`model`, `prompt`, `images`, `stream`,
  `base_url_override`, `video_media_id`).
- The exact cancellation exception type observed (via
  `except asyncio.CancelledError`).
- Whether its test-only `finally` block ran.

### 4.3 Non-ASCII Content

The first chunk uses `Xin chào — 世界` (Vietnamese greeting with CJK
characters) to prove UTF-8 byte encoding in the SSE content body.

### 4.4 Expected SSE Bytes

Expected bytes are constructed independently using:
```python
expected_payload = json.loads(first_chunk_json)
expected_sse_bytes = (
    f"data: {json.dumps(expected_payload, ensure_ascii=False)}\n\n"
).encode("utf-8")
```

This avoids relying on the handler's own JSON serialization and
proves the route re-serializes with `ensure_ascii=False`.

---

## 5. Assertions

| Assertion | Expected |
|-----------|----------|
| `response.__call__` returns | Normally (no exception) |
| Total ASGI messages | 2 |
| Message 0 `type` | `http.response.start` |
| Message 0 `status` | 200 |
| Message 1 `type` | `http.response.body` |
| Message 1 `more_body` | `True` |
| Message 1 `body` | Exact independently built UTF-8 SSE bytes |
| Non-ASCII bytes in body | Present |
| Additional body messages | None |
| `data: [DONE]\n\n` | Not present |
| `more_body=False` message | Not present |
| Handler cancellation type | `asyncio.CancelledError` |
| Handler `finally_ran` | `True` |
| Post-call `body_iterator.__anext__()` | Raises `StopAsyncIteration` |
| Handler call count | 1 |
| Handler call `model` | Expected model |
| Handler call `prompt` | Expected prompt |
| Handler call `stream` | `True` |
| Handler call `images` | `None` |
| Handler call `base_url_override` | `"http://test.local"` (derived from request) |
| Handler call `video_media_id` | `None` |

---

## 6. Deliverables

| Deliverable | Status |
|-------------|--------|
| tests/compatibility/test_streaming_response_disconnect_cancellation.py | Created |
| docs/SPRINTS/SPRINT-006O-receive-side-streaming-disconnect-characterization.md | Created |
| docs/PROJECT_STATE.md updated | Updated |
| docs/SPRINTS/README.md updated | Updated |
| docs/TEST_HARNESS_PLAN.md updated | Updated |
| docs/STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md updated | Updated |
| docs/STREAMING_TRANSPORT_TEST_PLAN.md updated | Updated |
| No src/ changes | Confirmed |
| No requirements.txt/pyproject.toml changes | Confirmed |

---

## 7. Verification

```
python3 -m unittest tests.compatibility.test_streaming_response_disconnect_cancellation -v
# Expected: 1 test, OK

python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# Expected: 302 tests, OK

git diff -- src
# Expected: no output

git diff -- requirements.txt pyproject.toml
# Expected: no output

grep -n "async def test_" tests/compatibility/test_streaming_response_disconnect_cancellation.py
# Expected: exactly one test method

git diff --check
# Expected: no output
```

---

## 8. Explicitly Deferred

- Backpressure and flow control
- Proxy buffering
- TCP behavior
- Live server behavior
- Production lifespan
- Authentication and request validation
- Runtime fixes
- ASGI spec 2.4 disconnect path testing
- Gemini disconnect test (same structural contract, no distinct transport)
- Immediate-disconnect test
- Any additional tests beyond the single OpenAI test

---

## 9. What This Test Does and Does Not Prove

### Proves

- Receive-side `http.disconnect` triggers cancellation-driven stream
  termination in Starlette 0.48.0's pre-2.4 path.
- Exactly one content body is sent before disconnect.
- The route body iterator terminates after cancellation.
- The fake handler observes `asyncio.CancelledError` (not `GeneratorExit`).
- Test-only `finally` blocks run during cancellation-driven unwinding.
- `response.__call__` returns normally (cancel scope suppresses the
  `CancelledError`).
- No `[DONE]` sentinel or `more_body=False` message is emitted after
  cancellation.
- The test is deterministic with explicit `asyncio.Event` synchronization
  and no `sleep()` or timing guesses.

### Does Not Prove

- Real TCP disconnection behavior.
- Deployed-server behavior with Uvicorn, Gunicorn, or other ASGI servers.
- Production application resource cleanup (no DB, network, tokens in test).
- Backpressure or flow control behavior.
- Starlette explicitly or implicitly calls `aclose()` on `body_iterator`
  — no such invocation is claimed.
