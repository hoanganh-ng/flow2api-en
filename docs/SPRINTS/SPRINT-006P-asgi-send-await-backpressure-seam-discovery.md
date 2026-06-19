# Sprint 006P — ASGI Send-Await Backpressure Seam Discovery

## Overview

| Field | Value |
|-------|-------|
| **Sprint** | 006P |
| **Name** | ASGI Send-Await Backpressure Seam Discovery |
| **Type** | Documentation-only discovery |
| **Predecessor** | Sprint 006O — Receive-Side Streaming Disconnect Characterization |
| **Status** | ✅ Completed |

## Objective

Discover the narrowest safe seam for testing application-level ASGI
send-await flow control — the property that Starlette
`StreamingResponse.stream_response` awaits `send()` for one body before
requesting the next iterator value.

This sprint does NOT prove TCP backpressure, socket buffer behavior,
client read speed, HTTP transfer behavior, proxy buffering, or deployed
Uvicorn behavior.

## Scope

### In Scope

- Inspect `starlette.responses.StreamingResponse.stream_response` and
  `starlette.responses.StreamingResponse.__call__`.
- Inspect `src.api.routes._iterate_openai_stream` and
  `_iterate_gemini_stream`.
- Compare six candidate test seams (A–F).
- Evaluate a synchronized probe design using `asyncio.Event`.
- Execute a disposable, uncommitted probe.
- Recommend exactly one seam for the next implementation sprint.
- Propose exactly one future compatibility test.

### Out of Scope

- Adding committed tests.
- Modifying runtime source code.
- TCP, socket, proxy, or client-level backpressure.
- Disconnect or cancellation behavior (handled by Sprints 006N/006O).
- ASGI spec 2.0 task-group backpressure.
- Production lifespan, authentication, or network calls.

## Approach

### Source Inspection

Inspected Starlette 0.48.0 `StreamingResponse.stream_response` (lines
246–259) and `__call__` (lines 261–281). Identified the send-await
flow-control property: `await send(...)` is sequential — the `async for`
loop does not request the next value until `send()` returns.

### Candidate Comparison

Compared six candidate approaches (A–F). See
[STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md](../STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md)
for the full comparison table.

### Disposable Probe

Built and executed a disposable probe using:

- ASGI `spec_version` `"2.4"` (sequential `stream_response` path)
- Direct route invocation → `StreamingResponse`
- `asyncio.create_task` for response invocation
- Gated `send()` that blocks on `release_first_body_send` event
- Gated fake handler that sets `second_chunk_requested` and blocks on
  `release_second_chunk`
- No `sleep()`, timeout, polling, or probabilistic ordering

**Probe result:** While the first `send()` was blocked, `second_chunk_requested`
was NOT set. After releasing, the handler advanced normally. Stream completed
with expected ASGI messages (1 start + 3 content bodies + 1 final).

### Recommended Seam

**Candidate A: Direct StreamingResponse invocation with ASGI spec_version
"2.4" and a gated send callable.**

Rationale:

1. Exercises the real Starlette send-await boundary.
2. Fully deterministic with `asyncio.Event`.
3. Isolates backpressure from disconnect/cancellation.
4. Exercises the full route generator and handler chain.
5. Offline and deterministic.

### Proposed Test

**One test: OpenAI send-await backpressure characterization.**

A Gemini test adds no new information — both generators use the same
`stream_response` send-await loop.

## Deliverables

| Deliverable | Path | Status |
|-------------|------|--------|
| Seam discovery document | `docs/STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md` | ✅ Created |
| Sprint document | `docs/SPRINTS/SPRINT-006P-asgi-send-await-backpressure-seam-discovery.md` | ✅ Created |
| PROJECT_STATE.md update | `docs/PROJECT_STATE.md` | ✅ Updated |
| SPRINTS/README.md update | `docs/SPRINTS/README.md` | ✅ Updated |
| TEST_HARNESS_PLAN.md update | `docs/TEST_HARNESS_PLAN.md` | ✅ Updated |
| STREAMING_TRANSPORT_TEST_PLAN.md update | `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | ✅ Updated |
| STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md cross-reference | `docs/STREAMING_DISCONNECT_CANCELLATION_SEAM_DISCOVERY.md` | ✅ Updated |
| Committed tests | — | None (documentation-only) |

## Verification

```bash
python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# Expected baseline: 302 tests, OK

git diff -- src
# Expected: no output

git diff -- tests
# Expected: no output

git diff -- requirements.txt pyproject.toml
# Expected: no output

git diff --check
# Expected: no output
```

## Key Findings

1. **Blocked `send()` deterministically prevents handler advancement.**
   Starlette 0.48.0 `stream_response` awaits `send()` sequentially —
   the `async for` loop pauses until `send()` returns.

2. **ASGI spec_version "2.4" is the narrowest seam** because it avoids
   receive-side cancellation and task-group scheduling, isolating the
   sequential send-await loop.

3. **One OpenAI test is sufficient.** Gemini shares the same
   `StreamingResponse` send-await path. The generators differ in framing
   and terminal sentinel, not in the send-await contract.

4. **Gemini adds no distinct send-await contract.** Both generators use
   `async for` on the handler and yield strings to `stream_response`.
   The backpressure chain is structurally identical.

## Terminology

- **ASGI send-await flow control:** The property that `stream_response`
  awaits `send()` for each body chunk before requesting the next
  iterator value.
- **Application-level backpressure propagation:** The effect of ASGI
  send-await flow control on the route generator and handler — when
  `send()` blocks, the entire chain pauses.

## Explicitly Deferred

- Disconnect and cancellation (Sprints 006N/006O).
- TCP, socket, proxy, or client-level backpressure.
- ASGI spec 2.0 task-group path backpressure.
- Production lifespan and authentication.

## Confirmation

- No runtime source (`src/`) was modified.
- No tests were added or modified.
- No fixtures were added.
- No dependencies were added.
- No commits or pushes were performed.
- The disposable probe was created, executed, and deleted.
- Disconnect/cancellation remains a separate concern from backpressure.
