# Sprint 006K — Direct ASGI StreamingResponse Send-Loop Characterization

## Status

✅ Completed (corrected in Sprint 006K.1)

## Scope

Characterize the streaming route responses via direct `StreamingResponse.__call__`
invocation with deterministic synthetic ASGI scope/receive/send callables.
Assert on `http.response.start`, `http.response.body`, header encoding,
byte encoding, `more_body` flags, normal completion, and exception behavior
without constructing a FastAPI app or using TestClient, HTTPX, or network
transport.

## Approach

### Seam

**Direct `StreamingResponse.__call__` invocation with synthetic ASGI callables.**

The route function is called directly to obtain a `StreamingResponse`, which
is then invoked as `await response(scope, receive, send)` with minimal
synthetic ASGI scope, receive, and send callables. This exercises Starlette's
`stream_response` send loop: response-start emission, header encoding,
string-to-byte encoding, body-message framing, and final empty-body message.

Direct route calls supply the already-resolved `api_key` dependency parameter
explicitly. Authentication behavior is not exercised.

### Starlette Version and Implementation

**Starlette 0.48.0** (anyio 4.13.0)

`StreamingResponse.__call__` checks `scope["asgi"]["spec_version"]`:

- If `spec_version >= (2, 4)`: calls `await self.stream_response(send)` directly,
  catching `OSError` and converting to `ClientDisconnect`. No task group or
  disconnect listener is used.
- If `spec_version < (2, 4)`: uses `anyio.create_task_group()` with concurrent
  `stream_response` and `listen_for_disconnect` tasks.

This sprint uses `spec_version "2.4"` to exercise the simple path, avoiding
the anyio task-group and disconnect-listener entirely. This prevents any risk
of deadlock or non-deterministic cancellation from the synthetic receive callable.

### `stream_response` Behavior (Starlette 0.48.0)

1. Sends `http.response.start` with `status`, `raw_headers` (before iteration).
2. Iterates `body_iterator` with `async for`.
3. For each chunk: if not `bytes` or `memoryview`, encodes with `self.charset`
   (utf-8). Sends `http.response.body` with `body=chunk, more_body=True`.
4. After iteration completes: sends `http.response.body` with
   `body=b"", more_body=False`.
5. If an exception occurs during iteration: it propagates through `__call__`.
   The final empty-body message is NOT sent.

### Header Encoding

Headers are stored as `raw_headers`: list of `(bytes, bytes)` tuples.
Keys are lowercased and encoded as `latin-1`. Values are encoded as `latin-1`.
For `text/event-stream` media type, Starlette appends `; charset=utf-8` to
the content-type header.

### Safety Gate

**PASSED.** Direct response invocation is:

- Deterministic (no task group, no timing dependency)
- No FastAPI app construction
- No TestClient, HTTPX, or network
- No lifespan, production services, database, browser, captcha, proxy
- No hanging or deadlock risk (spec_version 2.4 bypasses disconnect listener)
- No `src/` modification

## Tests Created

**File:** `tests/compatibility/test_streaming_response_asgi_send_loop.py`

**Test count:** 6 tests across 6 test classes

### Test Cases

1. **test_openai_successful_asgi_send_loop** (Case 1)
   - Calls `create_chat_completion` with `stream=True` and a non-ASCII text
     payload (`Xin chào — 世界`) to prove UTF-8 byte encoding.
   - Invokes returned response with synthetic ASGI callables.
   - Asserts message 0 is `http.response.start` with status 200.
   - Asserts all raw header keys and values are `bytes` objects.
   - Asserts expected header keys present in lowercase byte form:
     `b"content-type"`, `b"cache-control"`, `b"connection"`, `b"x-accel-buffering"`.
   - Asserts `content-type` is exactly `b"text/event-stream; charset=utf-8"`.
   - Asserts exactly 5 body messages: 3 chunk bodies + 1 `[DONE]` body + 1 final.
   - Asserts each content body has `more_body=True` and exact byte values
     computed from the expected JSON with `ensure_ascii=False` and UTF-8 encoding.
   - Asserts `data: [DONE]\n\n` is a separate ASGI body message (message 4).
   - Asserts non-ASCII UTF-8 bytes appear in the first content body.
   - Asserts final message is exactly `http.response.body` with `body=b""`,
     `more_body=False`.
   - Asserts overall message count is 6 (1 start + 4 content + 1 final).
   - Asserts handler called once.

2. **test_gemini_successful_asgi_send_loop** (Case 2)
   - Calls `stream_generate_content` with Gemini request and a non-ASCII
     text payload (`Xin chào — 世界`) to prove UTF-8 byte encoding.
   - Asserts message 0 is `http.response.start` with status 200.
   - Asserts header byte type, lowercase keys, and exact values.
   - Asserts exactly 4 body messages: 3 Gemini event bodies + 1 final.
   - Asserts each content body has `more_body=True`.
   - Asserts non-ASCII UTF-8 bytes appear in the first content body.
   - Parses Gemini event payloads and verifies order:
     - Event 1: text event with non-ASCII content, no `finishReason`.
     - Event 2: text event with `" Gemini"`, no `finishReason`.
     - Event 3: finish-reason event with `finishReason=STOP`, no `content`.
   - Asserts no `[DONE]` sentinel in any body message.
   - Asserts final message is exactly `http.response.body` with `body=b""`,
     `more_body=False`.
   - Asserts overall message count is 5 (1 start + 3 content + 1 final).
   - Asserts handler called once.

3. **test_openai_exception_before_first_chunk** (Case 3)
   - Fake handler raises immediately (no yield values).
   - Asserts response.start IS sent (Starlette sends it before iteration).
   - Asserts original `RuntimeError` propagates.
   - Asserts no content body messages.
   - Asserts no `[DONE]` in any message.
   - Characterizes final `more_body=False` as ABSENT (exception interrupts send loop).

4. **test_gemini_exception_before_first_event** (Case 4)
   - Fake handler raises immediately for Gemini route.
   - Asserts response.start IS sent.
   - Asserts original exception propagates.
   - Asserts no synthesized Gemini event.
   - Asserts no `[DONE]` in any message.
   - Characterizes final `more_body=False` as ABSENT.

5. **test_openai_partial_output_then_exception** (Case 5)
   - Fake handler yields one chunk then raises.
   - Asserts response.start sent.
   - Asserts one encoded content body with `more_body=True`.
   - Asserts original exception propagates.
   - Asserts no final `[DONE]` in any body message.
   - Asserts no synthesized SSE error event.
   - Characterizes final `more_body=False` as ABSENT.

6. **test_gemini_partial_output_then_exception** (Case 6)
   - Fake handler yields one Gemini-shaped event then raises.
   - Asserts one encoded Gemini body event with `more_body=True`.
   - Asserts original exception propagates.
   - Asserts no synthetic error event.
   - Asserts no OpenAI `[DONE]` sentinel.
   - Characterizes final `more_body=False` as ABSENT.

## Synthetic ASGI Harness

The test file contains small test-local helpers:

### `_make_asgi_scope(path, method)`

Returns a minimal HTTP ASGI scope dict with `asgi.spec_version = "2.4"`.

### `_make_receive()`

Returns an async callable that yields `{"type": "http.disconnect"}`.
With spec_version 2.4, this callable is never invoked by
`StreamingResponse.__call__`, but it is provided for signature compatibility.

### `_make_send_recorder()`

Returns `(send, messages)` where `send` is an async callable that appends
each message dict to the `messages` list.

### `_get_start_message(messages)`

Extracts the single `http.response.start` message from the recorded list.

### `_get_body_messages(messages)`

Extracts all `http.response.body` messages in order.

### `_headers_to_dict(raw_headers)`

Decodes raw ASGI header pairs `(bytes, bytes)` to a `{str: str}` dict.

## Fake Handlers

Test-local `FakeStreamingHandler` and `FakeFailingHandler` classes:

- Accept `yield_values` to yield during iteration.
- Accept an optional `error` exception to raise after yielding.
- Record all calls for assertion.
- Do not make network calls, read credentials, or touch services.

Patching: `unittest.mock.patch` on `src.api.routes.generation_handler`,
restored after every test via context manager.

## Findings

### Response-Start Timing

**`http.response.start` is always sent before body iteration begins.**

Starlette's `stream_response` sends the start message before entering the
`async for chunk in self.body_iterator` loop. This means even when the
generator raises immediately (before first yield), the start message has
already been sent.

### Header Encoding

The route tests directly assert:

- Every raw header key and value is a `bytes` object.
- Expected header keys are present in lowercase byte form
  (`b"content-type"`, `b"cache-control"`, `b"connection"`, `b"x-accel-buffering"`).
- Content-type is exactly `b"text/event-stream; charset=utf-8"`.
- Cache-control is `b"no-cache"`, connection is `b"keep-alive"`,
  x-accel-buffering is `b"no"`.

**Starlette implementation observation (not directly asserted by route tests):**
Starlette 0.48.0 encodes header keys and values using `latin-1` during
`raw_headers` initialization. Since the route header used in these tests
contain only ASCII characters, the latin-1 encoding is observationally
equivalent to ASCII/UTF-8 for these values. The route assertions prove
that headers are `bytes` with the expected values; they do not independently
prove latin-1 encoding. Non-ASCII header values would be needed to
distinguish latin-1 from other encodings.

### Byte Encoding

All body chunks yielded by the body_iterator are strings. Starlette's
`stream_response` encodes non-bytes chunks using `self.charset` (utf-8).
The recorded body messages contain `bytes` objects with the UTF-8 encoded
SSE frames.

**Directly asserted by route tests:** Both successful tests use a non-ASCII
text value (`Xin chào — 世界`) containing Vietnamese diacritics and CJK
characters. The tests assert that the exact UTF-8 byte sequence for this
value appears in the first content body message, proving that Starlette
encodes string chunks as UTF-8 bytes rather than escaping non-ASCII
characters.

### Body Message Framing

- Each content chunk is sent as a separate `http.response.body` message
  with `more_body=True`. This is directly asserted by verifying exact body
  message counts (4 for OpenAI, 3 for Gemini) and positional message indices.
- The `[DONE]` sentinel (OpenAI only) is a separate body message, not
  coalesced with the preceding chunk.
- The final message has `body=b""` and `more_body=False`.
- No batching or coalescing occurs.

### Normal Completion

On successful stream completion:
1. One `http.response.start` message.
2. N `http.response.body` messages with `more_body=True` (one per chunk).
3. One final `http.response.body` with `body=b""`, `more_body=False`.

### Exception Behavior

When the body_iterator raises during iteration:
1. `http.response.start` has already been sent.
2. Any chunks yielded before the exception are sent as `http.response.body`
   with `more_body=True`.
3. The original exception propagates through `StreamingResponse.__call__`.
4. The final `more_body=False` message is NOT sent.
5. No synthesized error event or `[DONE]` sentinel is emitted.

### Disconnect-Listener Handling

With `spec_version >= (2, 4)`, the disconnect listener is NOT started.
The `receive` callable is never invoked. This avoids any risk of
deadlock or non-deterministic cancellation from the synthetic harness.

## Dependency Parameter Framing

Direct route calls supply the already-resolved `api_key` dependency parameter
explicitly:

```python
await create_chat_completion(request, raw_request, api_key="test-key")
await stream_generate_content(model=..., request=..., raw_request=..., alt=None, api_key="test-key")
```

Authentication behavior is not exercised.

## Explicit Absence of Coverage

- FastAPI app construction
- TestClient or HTTPX
- Network calls or HTTP transport
- Lifespan startup/shutdown
- Dependency override
- Authentication testing
- Client disconnect or cancellation (beyond minimal harness signature)
- Backpressure or slow consumers
- Background tasks
- Server/proxy buffering
- Media streaming
- Runtime source modification

## Verification

```bash
# Test file
python3 -m unittest tests.compatibility.test_streaming_response_asgi_send_loop -v
# Result: Ran 6 tests — OK

# Existing wrapper tests (Sprint 006J)
python3 -m unittest tests.compatibility.test_streaming_response_wrappers -v
# Result: Ran 8 tests — OK

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# Result: Ran 299 tests — OK
# 299 = Sprint 006B (67) + Sprint 006C (95) + Sprint 005B (8) + Sprint 005D (12)
#       + Sprint 006E (6) + Sprint 006F (5) + Sprint 006G (18) + Sprint 006H (41)
#       + Sprint 006J (8) + Sprint 006K (6) + other earlier tests (33)

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Result: OK

# No runtime source changes
git diff -- src
# Result: (no output)

# No whitespace errors
git diff --check
# Result: (no output)
```

## Confirmation

- `StreamingResponse.__call__` was invoked directly with synthetic ASGI callables.
- ASGI `send`/`receive` were used (synthetic, test-local).
- `http.response.start` and `http.response.body` were recorded and asserted.
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
| `tests/compatibility/test_streaming_response_asgi_send_loop.py` | 6 ASGI send-loop characterization tests |
| `docs/SPRINTS/SPRINT-006K-direct-asgi-streaming-response-send-loop-characterization.md` | This sprint document |

## Documents Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006K to sprint history, current sprint, what-is-not-yet-done |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006K ASGI send-loop characterization note |
| `docs/SPRINTS/README.md` | Added Sprint 006K to sprint index |
| `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | Added Sprint 006K implementation note |

## What This Sprint Does NOT Cover

- FastAPI app construction or TestClient integration
- HTTPX or ASGI transport
- Real HTTP transport (chunked encoding, connection handling)
- Client disconnect detection and propagation
- Cancellation behavior
- Backpressure and flow control
- Background tasks
- Server or proxy buffering
- Network calls
- Media retrieval
- Runtime source modification
- New dependencies
- Commits or pushes

## Recommendation for Next Sprint

The next sprint should consider:

1. **TestClient integration** — Construct a minimal test-local FastAPI app
   with dependency override, use TestClient to verify full HTTP transport
   (status, headers, chunked encoding, SSE parsing by client).

2. **Cancellation behavior** — Test client disconnect propagation and
   generator cleanup when the connection is dropped mid-stream, using
   `spec_version < (2, 4)` to exercise the task-group path.

3. **Backpressure and buffering** — Characterize behavior when the client
   reads slower than the generator produces.

All tests are offline, deterministic, and consistent with the existing test
patterns established in Sprint 006E–006J.

---

## Sprint 006K.1 — Strengthened Assertions and Documentation Corrections

Sprint 006K.1 is a narrow correction sprint that strengthens the successful
OpenAI and Gemini ASGI send-loop tests and corrects documentation claims
that exceeded what the original assertions directly proved.

### Test Strengthening

- **Case 1 (OpenAI):** Now uses non-ASCII text (`Xin chào — 世界`), asserts
  exact ASGI message count (6), exact body message count (5), exact content-body
  byte values, one body message per stream event, `[DONE]` as a separate body
  message, header bytes type, and non-ASCII UTF-8 byte preservation.
- **Case 2 (Gemini):** Now uses non-ASCII text, asserts exact ASGI message
  count (5), exact body message count (4), parses and verifies Gemini event
  payload order (2 text events + 1 finish-reason event), header bytes type,
  and non-ASCII UTF-8 byte preservation.
- **Cases 3–6 (exception tests):** Preserved unchanged.

### Documentation Corrections

- Header Encoding findings now distinguish route-level byte assertions from
  the observed Starlette latin-1 implementation.
- Byte Encoding findings now note non-ASCII UTF-8 assertion.
- Body Message Framing now notes per-chunk separation is directly asserted.
- Verification section: removed stale `git status --short` and
  `git diff --stat` output; corrected 299-test explanation.
- All claims now match the actual test assertions.

### Files Modified by Sprint 006K.1

| File | Change |
|------|--------|
| `tests/compatibility/test_streaming_response_asgi_send_loop.py` | Strengthened Cases 1 and 2 with exact message sequence, byte, and UTF-8 assertions |
| `docs/SPRINTS/SPRINT-006K-direct-asgi-streaming-response-send-loop-characterization.md` | This document — corrected claims and added 006K.1 section |
| `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | Removed `wait, let me re-check` text and corrected 299-test explanation |
| `docs/TEST_HARNESS_PLAN.md` | Corrected Sprint 006K description to reflect strengthened assertions |
| `docs/PROJECT_STATE.md` | Updated Sprint 006K description in history and what-is-not-yet-done |
