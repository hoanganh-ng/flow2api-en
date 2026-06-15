# Sprint 006G — Mocked OpenAI Streaming Generator Contract

## Status

✅ Completed

## Scope

Characterize the internal OpenAI async streaming generator (`_iterate_openai_stream`)
using a deterministic fake handler. Cover SSE framing, reasoning-content progress,
ordering, empty-stream behavior, and exact `[DONE]` termination without constructing
`StreamingResponse` or exercising HTTP transport.

## Approach

### Target function

- **Function name:** `_iterate_openai_stream`
- **Location:** `src/api/routes.py`, lines 717–737
- **Signature:** `async def _iterate_openai_stream(normalized: NormalizedGenerationRequest, base_url_override: Optional[str] = None)`
- **Type:** async generator (yields `str`)

### How the generator works

1. Calls `_ensure_generation_handler()` to obtain the module-level `generation_handler` global.
2. Iterates `handler.handle_generation(model=..., prompt=..., images=..., stream=True, base_url_override=..., video_media_id=...)`.
3. For each chunk yielded by the handler:
   - If the chunk already starts with `"data: "`, it is yielded unchanged (passthrough).
   - Otherwise, the chunk is parsed as JSON via `_parse_handler_result` and re-framed as `data: {json}\n\n`.
4. After all handler chunks are consumed, yields `"data: [DONE]\n\n"` unconditionally.

### Error behavior

The generator contains **no try/except/finally block**. Errors from the handler
propagate directly to the caller. This is documented but not tested as a
generator-level contract because the error behavior is undefined at the
generator level (it depends on the HTTP transport layer's exception handling).

### Mutable state

- Reads module-level `generation_handler` global via `_ensure_generation_handler()`.
- Does not modify any global metrics, locks, or configuration.
- No cleanup logic (no `finally` block).

## Safety Gate

**PASSED.** The generator can be iterated without:

- FastAPI app creation
- Lifespan startup/shutdown
- `StreamingResponse` construction or consumption
- HTTP/ASGI transport
- Real `GenerationHandler` (patched with fake)
- `FlowClient`, `TokenManager`, database, network, media retrieval
- Browser/captcha/proxy/session behavior

## Fake Handler

### Class: `FakeStreamingHandler`

- **Location:** `tests/compatibility/test_generation_stream_openai.py`
- **Constructor:** `__init__(self, yield_values: list[str] | None = None)`
- **Method:** `async def handle_generation(self, model, prompt, images=None, stream=False, base_url_override=None, video_media_id=None)` — async generator yielding the configured `yield_values`.
- **Records:** All calls in `self.calls: list[dict]`.
- **Does not:** Make network calls, read credentials, touch a database, create services, retrieve media.

### Class: `FakeFailingHandler`

- **Location:** `tests/compatibility/test_generation_stream_openai.py`
- **Constructor:** `__init__(self, yield_values: list[str] | None = None, error: Exception | None = None)`
- **Method:** `async def handle_generation(...)` — async generator yielding configured values then raising the configured error.
- **Records:** All calls in `self.calls: list[dict]`.
- **Default error:** `RuntimeError("synthetic handler failure")`

### Patching

- Patches `src.api.routes.generation_handler` via `unittest.mock.patch.object`.
- Guaranteed restoration per test (patch context manager).

## Iteration Method

Tests use a helper `_collect_stream(generator)` that consumes the async generator
with `async for` and collects all yielded strings into a list. No `StreamingResponse`,
`TestClient`, or ASGI transport is involved.

## Test Cases

### 1. Text-Delta SSE Framing (2 tests)

| Test | Description |
|------|-------------|
| `test_raw_json_gets_sse_framing` | Raw JSON handler output is wrapped in `data: {json}\n\n`. JSON is valid and text is preserved. No `[DONE]` before the chunk. |
| `test_already_prefixed_chunk_passed_through` | Chunks already starting with `data: ` are yielded unchanged. |

### 2. Reasoning-Content Progress (2 tests)

| Test | Description |
|------|-------------|
| `test_reasoning_content_preserved` | A chunk with `delta.reasoning_content` is framed and the field is preserved. |
| `test_reasoning_content_matches_fx_os_002_semantics` | Generator output is consistent with FX-OS-002 fixture reasoning_content values. Direct async-generator characterization, not HTTP transport. |

### 3. [DONE] Termination (4 tests)

| Test | Description |
|------|-------------|
| `test_done_emitted_exactly_once` | After consuming a finite stream, `data: [DONE]\n\n` appears exactly once. |
| `test_done_is_final_event` | `data: [DONE]\n\n` is the last yielded value. |
| `test_done_exact_framing` | The [DONE] event has exact framing: `data: [DONE]\n\n`. |
| `test_done_matches_fx_os_003_semantics` | Generator [DONE] output matches the last line of the FX-OS-003 fixture. |

### 4. Multiple-Chunk Ordering (3 tests)

| Test | Description |
|------|-------------|
| `test_ordering_preserved` | Two chunks are yielded in the same order as the handler. |
| `test_no_duplication` | Each handler yield produces exactly one output chunk. |
| `test_handler_called_once` | The handler's `handle_generation` is invoked exactly once. |

### 5. Empty Handler Stream (2 tests)

| Test | Description |
|------|-------------|
| `test_empty_stream_emits_only_done` | When the handler yields nothing, only `data: [DONE]\n\n` is emitted. |
| `test_empty_stream_handler_called` | The handler is still invoked even when it yields nothing. |

### 6. Mutable State and Cleanup (3 tests)

| Test | Description |
|------|-------------|
| `test_handler_restored_after_patch` | After exiting the patch context, the original handler is restored. |
| `test_handler_arguments_forwarded` | All `NormalizedGenerationRequest` fields are forwarded to the handler correctly. |
| `test_empty_images_becomes_none` | When `images` is an empty list, the handler receives `None` (source: `images if images else None`). |

### 7. Handler Exception Propagation (2 tests)

`_iterate_openai_stream` contains no local exception conversion. Exceptions
raised by the handler propagate directly to the caller and interrupt normal
stream termination, so the generator does not emit its final `[DONE]` event.
Client-visible HTTP/StreamingResponse handling of the propagated exception
remains out of scope.

| Test | Description |
|------|-------------|
| `test_exception_before_first_chunk` | Exception before any yield propagates. Original type and message preserved. No `[DONE]` or SSE error event emitted. Handler invoked once. `generation_handler` restored. |
| `test_exception_after_one_chunk` | First chunk emitted with correct SSE framing, then exception propagates. No `[DONE]` emitted. No SSE error payload synthesized. Ordering before exception preserved. Handler invoked once. |

## SSE Framing Summary

| Handler yield format | Generator output |
|---------------------|-----------------|
| Raw JSON string (no prefix) | `data: {json}\n\n` |
| String starting with `data: ` | Yielded unchanged |
| After all chunks | `data: [DONE]\n\n` |

## FX-OS-002 Coverage Status

- **Fixture:** `tests/fixtures/generation/openai-streaming/reasoning-progress.sse.txt`
- **Coverage:** Direct async-generator characterization. The generator preserves
  `reasoning_content` values from FX-OS-002 fixture payloads.
- **Not covered:** HTTP transport, StreamingResponse, cancellation, client-disconnect.

## FX-OS-003 Coverage Status

- **Fixture:** `tests/fixtures/generation/openai-streaming/done-termination.sse.txt`
- **Coverage:** Direct async-generator characterization. The generator emits
  `data: [DONE]\n\n` matching the last line of the FX-OS-003 fixture.
- **Not covered:** HTTP transport, StreamingResponse, cancellation, client-disconnect.

## What This Sprint Does NOT Cover

- HTTP endpoint calls (no `create_chat_completion` through transport)
- `StreamingResponse` construction or consumption
- `TestClient` or ASGI transport
- Headers, disconnects, cancellation, backpressure, partial closure
- Gemini streaming
- Image/video/media streams
- `extend://` scheme
- Production service instantiation
- Network calls
- Runtime source modification
- New dependencies

## Files Created

| File | Purpose |
|------|---------|
| `tests/compatibility/test_generation_stream_openai.py` | 18 offline streaming generator contract tests (including 2 handler-exception propagation tests) |
| `docs/SPRINTS/SPRINT-006G-mocked-openai-streaming-generator-contract.md` | This sprint document |

## Files Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006G to sprint history, current sprint, what-is-documented, and next-steps |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006G streaming generator test coverage note |
| `docs/SPRINTS/README.md` | Added Sprint 006G to sprint index |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Updated FX-OS-002 and FX-OS-003 tested status |

## Verification

```
# New test file
python3 -m unittest tests.compatibility.test_generation_stream_openai -v
# Result: 18 tests, OK

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Result: 244 tests (226 existing + 18 new), OK

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Result: OK

# No runtime source changes
git diff -- src
# Result: (no output)
```

## Confirmation

- No `StreamingResponse`, HTTP transport, network, or media retrieval was exercised.
- No runtime source (`src/`) was changed.
- All 226 existing tests continue to pass.
- 18 new tests added, all passing.
- Combined suite: 244 tests, all passing.

## Recommendation for Next Sprint

Sprint 006H should consider:

1. **Gemini streaming generator** (`_iterate_gemini_stream`) characterization
   using the same fake-handler approach.
2. **HTTP-level streaming tests** for OpenAI (using `TestClient` with
   `StreamingResponse` body iteration) — requires careful safety gating.
3. **Error propagation tests** at the HTTP transport level.
