# Sprint 006K.1 — Strengthen ASGI Send-Loop Assertions and Correct Documentation

## Status

✅ Completed

## Scope

Narrow correction sprint applied to the existing Sprint 006K direct-ASGI
`StreamingResponse` send-loop tests. Strengthen the successful OpenAI and
Gemini tests so that assertions match the documentation claims, correct
documentation that overstated what the original assertions proved, and
track this correction as a distinct sprint.

## Test Strengthening

### Case 1 — OpenAI Successful Send Loop

- Use non-ASCII text (`Xin chào — 世界`) in the first handler chunk.
- Assert exact ASGI message order: 1 `http.response.start` + 4 content
  bodies + 1 final empty body = 6 messages total.
- Assert exact content-body byte values computed from expected JSON with
  `json.dumps(payload, ensure_ascii=False)` and `.encode("utf-8")`.
- Assert `data: [DONE]\n\n` is a separate ASGI body message (message 4).
- Assert non-ASCII UTF-8 bytes appear in the first content body.
- Assert header keys and values are all `bytes` objects.
- Assert expected header keys present in lowercase byte form.
- Assert `content-type` is exactly `b"text/event-stream; charset=utf-8"`.
- Assert final message via exact dictionary equality:
  `{"type": "http.response.body", "body": b"", "more_body": False}`.

### Case 2 — Gemini Successful Send Loop

- Use non-ASCII text (`Xin chào — 世界`) in the first handler chunk.
- Construct exact expected Gemini payloads for 3 events:
  - Event 1: model text `Xin chào — 世界` (no `finishReason`).
  - Event 2: model text ` Gemini` (no `finishReason`).
  - Event 3: `finishReason: "STOP"` with no `content`.
- Serialize each with `json.dumps(payload, ensure_ascii=False)` and wrap
  as `f"data: {serialized}\n\n".encode("utf-8")`.
- Assert exact byte equality of all content bodies against expected list.
- Assert non-ASCII UTF-8 bytes appear in the first content body.
- Parse event payloads and verify order semantically after the byte assertion.
- Assert header keys and values are all `bytes` objects.
- Assert final message via exact dictionary equality.
- Assert exact ASGI message count: 1 start + 3 content + 1 final = 5.

### Cases 3–6 — Exception Tests

Preserved unchanged. Continue proving:
- `http.response.start` was already emitted.
- Immediate failures emit no content body.
- Partial failures emit exactly the already-produced content body.
- The original exception propagates.
- No synthesized error event is added.
- No `[DONE]` is added after OpenAI failure.
- No final `more_body=False` message is emitted after failure.

## Documentation Corrections

- **299-test explanation:** Replaced incorrect breakdown
  (`Sprint 005B (8) + Sprint 005D (12) + other earlier tests (33)`) with
  the correct breakdown:
  `Static fixture compatibility suite after Sprint 005D (53)`.
  Calculation: 53 + 67 + 95 + 6 + 5 + 18 + 41 + 8 + 6 = 299.
- **Authentication wording:** Replaced "already tested implicitly" with
  "Not exercised. Direct route calls supply the already-resolved `api_key`
  dependency parameter explicitly."
- **Header encoding:** SPRINT-006K findings section already corrected to
  distinguish route-level byte assertions from Starlette latin-1 implementation.
- **Stale verification output:** Already removed `git status --short` and
  `git diff --stat` from SPRINT-006K in prior correction pass.

## Files Changed

| File | Change |
|------|--------|
| `tests/compatibility/test_streaming_response_asgi_send_loop.py` | Added `expected_gemini_bodies` exact byte assertion; replaced field-by-field final message assertions with exact dict equality in both Cases 1 and 2 |
| `docs/SPRINTS/SPRINT-006K.1-strengthen-asgi-send-loop-assertions.md` | This sprint document |
| `docs/SPRINTS/SPRINT-006K-direct-asgi-streaming-response-send-loop-characterization.md` | Corrected 299-test explanation |
| `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | Corrected 299-test explanation and authentication wording |
| `docs/TEST_HARNESS_PLAN.md` | Updated Sprint 006K description (from prior pass) |
| `docs/PROJECT_STATE.md` | Added distinct Sprint 006K.1 row to sprint history |
| `docs/SPRINTS/README.md` | Added distinct Sprint 006K.1 row to sprint index |

## Verification

```bash
python3 -m unittest tests.compatibility.test_streaming_response_asgi_send_loop -v
# Expected: 6 tests, OK

python3 -m unittest tests.compatibility.test_streaming_response_wrappers -v
# Expected: 8 tests, OK

python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# Expected: 299 tests, OK
# 299 = Static fixture compatibility suite after Sprint 005D (53)
#       + Sprint 006B (67) + Sprint 006C (95)
#       + Sprint 006E (6) + Sprint 006F (5) + Sprint 006G (18) + Sprint 006H (41)
#       + Sprint 006J (8) + Sprint 006K (6)
# Calculation: 53 + 67 + 95 + 6 + 5 + 18 + 41 + 8 + 6 = 299

python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Expected: OK

git diff -- src
# Expected: (no output)

git diff --check
# Expected: (no output)
```

## Out of Scope

Same as Sprint 006K: no FastAPI app, TestClient, HTTPX, network, ASGI
pre-2.4, disconnect listeners, cancellation, backpressure, authentication,
dependency overrides, production services, runtime fixes, dependency upgrades,
commits, or pushes.
