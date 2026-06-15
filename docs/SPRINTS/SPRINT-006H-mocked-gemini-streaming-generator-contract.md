# Sprint 006H — Mocked Gemini Streaming Generator Contract

## Status

✅ Completed

## Scope

Characterize the internal Gemini async streaming generator (`_iterate_gemini_stream`)
using a deterministic fake handler. Cover Gemini event framing, text conversion,
finish-reason mapping, reasoning-content behavior, empty/non-emitting chunks,
handler error-payload conversion, exception propagation, and the no-`[DONE]`
termination contract without constructing `StreamingResponse` or exercising
HTTP transport.

## Approach

### Target function

- **Function name:** `_iterate_gemini_stream`
- **Location:** `src/api/routes.py`, lines 740–786
- **Signature:** `async def _iterate_gemini_stream(normalized: NormalizedGenerationRequest, response_model: str, base_url_override: Optional[str] = None)`
- **Type:** async generator (yields `str`)

### How the generator works

1. Calls `_ensure_generation_handler()` to obtain the module-level `generation_handler` global.
2. Iterates `handler.handle_generation(model=..., prompt=..., images=..., stream=True, base_url_override=..., video_media_id=...)`.
3. For each chunk yielded by the handler, two code paths exist:

   **Path A — `data:`-prefixed chunks:**
   - Strips the `"data: "` prefix.
   - If the stripped payload is `"[DONE]"`, skips it (continues to next chunk).
   - Otherwise, parses the JSON via `_parse_handler_result`.
   - If `"error"` is in the payload, builds a Gemini error event using `_build_gemini_error_payload` and `_get_error_status_code`, yields it, and **returns** (terminates early).
   - Otherwise, converts through `_convert_openai_stream_chunk_to_gemini_event` and yields the result if non-None.

   **Path B — non-prefixed chunks:**
   - Parses the JSON via `_parse_handler_result`.
   - If `"error"` is in the payload, builds a Gemini error event and **returns**.
   - Otherwise, converts through `_convert_openai_stream_chunk_to_gemini_event` and yields the result if non-None.

4. After all handler chunks are consumed, the generator ends **without emitting any terminal sentinel**.

### Error behavior

The generator has an **explicit local error-payload conversion path**: when a
handler-yielded JSON chunk contains an `"error"` key, the generator converts it
to a Gemini error event using `_build_gemini_error_payload` and terminates via
`return`. This is distinct from Python exceptions, which propagate directly
(no try/except wrapping around the handler iteration).

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

- **Location:** `tests/compatibility/test_generation_stream_gemini.py`
- **Constructor:** `__init__(self, yield_values: list[str] | None = None)`
- **Method:** `async def handle_generation(self, model, prompt, images=None, stream=False, base_url_override=None, video_media_id=None)` — async generator yielding the configured `yield_values`.
- **Records:** All calls in `self.calls: list[dict]`.
- **Does not:** Make network calls, read credentials, touch a database, create services, retrieve media.

### Class: `FakeFailingHandler`

- **Location:** `tests/compatibility/test_generation_stream_gemini.py`
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

### 1. Text Delta — Gemini Event Framing (5 tests)

| Test | Description |
|------|-------------|
| `test_raw_json_produces_gemini_event` | Raw JSON handler output is converted to a Gemini-shaped event with `candidates[0].content.parts[0].text` and `modelVersion`. |
| `test_no_done_termination` | Gemini stream does not emit `data: [DONE]` after text deltas. |
| `test_no_openai_wrapper_leak` | The Gemini event does not contain OpenAI-specific wrapper fields (`id`, `object`, `created`, `choices`). |
| `test_prefixed_chunk_converted_to_gemini_event` | A `data:`-prefixed chunk is stripped, parsed, and converted to Gemini shape. |
| `test_text_preserved_exactly` | Text content including special characters is preserved without transformation. |

### 2. Multiple Chunks — Ordering (4 tests)

| Test | Description |
|------|-------------|
| `test_ordering_preserved` | Two text chunks are yielded in the same order as the handler. |
| `test_no_duplication` | Each handler yield produces at most one Gemini event. |
| `test_handler_called_once` | The handler's `handle_generation` is invoked exactly once. |
| `test_normal_iteration_ends_without_done` | Normal iteration ends without any `[DONE]` sentinel. |

### 3. Finish Reason (4 tests)

| Test | Description |
|------|-------------|
| `test_stop_mapped_to_stop` | OpenAI `stop` is mapped to Gemini `STOP`. Finish-only chunk has no `content` key. |
| `test_length_mapped_to_max_tokens` | OpenAI `length` is mapped to Gemini `MAX_TOKENS`. |
| `test_content_filter_mapped_to_safety` | OpenAI `content_filter` is mapped to Gemini `SAFETY`. |
| `test_finish_with_text_produces_both` | A chunk with both text and finish_reason produces content + finishReason. |

### 4. Reasoning Content (2 tests)

| Test | Description |
|------|-------------|
| `test_reasoning_content_appears_as_text` | `reasoning_content` is placed into Gemini `candidates[0].content.parts[0].text`. |
| `test_reasoning_content_preferred_over_content` | When both `reasoning_content` and `content` are present, `reasoning_content` wins (source: `or` chain in conversion helper). |

### 5. Empty Handler Stream (3 tests)

| Test | Description |
|------|-------------|
| `test_empty_stream_yields_nothing` | When the handler yields nothing, the generator yields nothing (no terminal event). |
| `test_empty_stream_handler_called` | The handler is still invoked even when it yields nothing. |
| `test_empty_stream_no_terminal_event` | No terminal event of any kind is emitted on an empty stream. |

### 6. Non-Emitting Chunk (3 tests)

| Test | Description |
|------|-------------|
| `test_non_emitting_chunk_skipped` | A chunk with empty delta and no finish_reason produces no event (conversion helper returns None). |
| `test_valid_chunks_after_non_emitting_still_appear` | A valid chunk after a non-emitting one is still yielded. |
| `test_multiple_non_emitting_chunks_all_skipped` | Multiple non-emitting chunks are all skipped silently. |

### 7. Handler Error Payload (4 tests)

The generator has an explicit local error-payload conversion path. When the
handler yields a JSON payload with an `"error"` key, the generator builds a
Gemini error event using `_build_gemini_error_payload` and terminates via `return`.

| Test | Description |
|------|-------------|
| `test_error_payload_converted_to_gemini_error_event` | An error JSON chunk is converted to a Gemini-shaped error event with `error.code`, `error.message`, `error.status`. |
| `test_error_payload_terminates_stream` | After an error event, the generator returns; subsequent chunks are never reached. |
| `test_prefixed_error_payload_converted` | A `data:`-prefixed error chunk follows the same conversion path (prefix stripped, error converted). |
| `test_error_payload_no_done` | No `[DONE]` is emitted after the error event. |

### 8. Data-Prefix [DONE] Handling (2 tests)

| Test | Description |
|------|-------------|
| `test_done_chunk_skipped` | A `data: [DONE]` handler yield is silently skipped; no event is emitted. |
| `test_done_between_valid_chunks` | A `data: [DONE]` between valid chunks is skipped; both valid chunks appear. |

### 9. Exception Before First Chunk (2 tests)

`_iterate_gemini_stream` contains no try/except wrapping around handler
iteration. Exceptions propagate directly to the caller.

| Test | Description |
|------|-------------|
| `test_exception_propagates` | Exception before any yield propagates with original type and message. Handler invoked once. `generation_handler` restored. |
| `test_no_gemini_event_on_exception` | No Gemini event or `[DONE]` is emitted when handler raises immediately. |

### 10. Exception After One Event (2 tests)

| Test | Description |
|------|-------------|
| `test_first_event_then_exception` | First event emitted as valid Gemini event, then handler exception propagates. Original type and message preserved. |
| `test_no_synthetic_error_event` | No synthetic error event or `[DONE]` is emitted after exception. |

### 11. Argument Forwarding (5 tests)

| Test | Description |
|------|-------------|
| `test_basic_arguments_forwarded` | Model, prompt, stream=True, and base_url_override are forwarded correctly. |
| `test_empty_images_becomes_none` | When `images` is an empty list, the handler receives `None` (source: `images if images else None`). |
| `test_images_forwarded` | Non-empty images list is forwarded as-is. |
| `test_video_media_id_forwarded` | `video_media_id` from the normalized request is forwarded. |
| `test_base_url_override_none_by_default` | When `base_url_override` is not passed, handler receives `None`. |

### 12. Mutable State and Cleanup (2 tests)

| Test | Description |
|------|-------------|
| `test_handler_restored_after_patch` | After exiting the patch context, the original handler is restored. |
| `test_no_metrics_or_config_mutation` | Running the generator does not alter module-level state beyond the handler patch lifecycle. |

### 13. Termination Contract (3 tests)

| Test | Description |
|------|-------------|
| `test_normal_termination_is_silent` | After all handler chunks, the generator ends without any terminal event. |
| `test_error_terminates_early` | An error payload causes early termination via `return`. |
| `test_gemini_vs_openai_done_comparison` | Documents the observable difference: Gemini stream never emits `[DONE]`; OpenAI stream always does. |

## Gemini Event Framing Summary

| Handler yield format | Generator output |
|---------------------|-----------------|
| Raw JSON string (no prefix) | `data: {gemini_event_json}\n\n` (via conversion helper) or skipped if conversion returns None |
| String starting with `data: ` | Prefix stripped, JSON parsed, converted to Gemini event or skipped |
| `data: [DONE]` | Silently skipped (no event emitted) |
| Error payload (contains `"error"` key) | Gemini error event `data: {error_json}\n\n`, then `return` (early termination) |
| After all chunks (normal end) | No terminal event — generator ends silently |

## Comparison with OpenAI Stream Generator

| Aspect | `_iterate_openai_stream` | `_iterate_gemini_stream` |
|--------|--------------------------|--------------------------|
| Terminal sentinel | `data: [DONE]\n\n` always emitted | No terminal sentinel |
| Event format | OpenAI SSE (`data: {openai_json}\n\n`) | Gemini event (`data: {gemini_json}\n\n`) |
| Error-payload handling | No local conversion; passed through | Converted to Gemini error event; early `return` |
| Passthrough chunks | `data:`-prefixed yielded unchanged | `data:`-prefixed stripped and converted |
| `[DONE]` from handler | N/A (generator emits its own) | Silently skipped |
| Exception propagation | Direct (no try/except) | Direct (no try/except) |

## FX-GS-001 Coverage Status

- **Fixture ID:** FX-GS-001 (Gemini streaming text chunks)
- **Status:** No static Gemini streaming fixture file exists.
- **Coverage:** Generator-level only. The generator converts OpenAI-shaped chunks
  to Gemini-shaped events using `_convert_openai_stream_chunk_to_gemini_event`.
- **Not covered:** HTTP transport, StreamingResponse, cancellation, client-disconnect, fixture-level verification.

## FX-GS-002 Coverage Status

- **Fixture ID:** FX-GS-002 (Gemini stream termination without [DONE])
- **Status:** No static Gemini streaming fixture file exists.
- **Coverage:** Generator-level only. The generator never emits `[DONE]`.
  The termination contract is: the generator ends silently when the handler
  iteration completes.
- **Not covered:** HTTP transport, StreamingResponse, cancellation, client-disconnect.

## What This Sprint Does NOT Cover

- HTTP endpoint calls (no `stream_generate_content` through transport)
- `StreamingResponse` construction or consumption
- `TestClient` or ASGI transport
- Headers, disconnects, cancellation, backpressure, partial closure
- Image/video/media streams
- `extend://` scheme
- Production service instantiation
- Network calls
- Runtime source modification
- New dependencies

## Files Created

| File | Purpose |
|------|---------|
| `tests/compatibility/test_generation_stream_gemini.py` | 41 offline Gemini streaming generator contract tests |
| `docs/SPRINTS/SPRINT-006H-mocked-gemini-streaming-generator-contract.md` | This sprint document |

## Files Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006H to sprint history, current sprint, what-is-not-yet-done, and next-steps |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006H Gemini streaming generator test coverage note |
| `docs/SPRINTS/README.md` | Added Sprint 006H to sprint index |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Updated header with Sprint 006H progress; added FX-GS-001/FX-GS-002 generator-level note |

## Verification

```
# New test file
python3 -m unittest tests.compatibility.test_generation_stream_gemini -v
# Result: 41 tests, OK

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Result: 285 tests (244 existing + 41 new), OK

# Individual modules
python3 -m unittest tests.compatibility.test_static_generation_fixtures -v   # 53 tests, OK
python3 -m unittest tests.compatibility.test_route_conversion_helpers -v    # 67 tests, OK
python3 -m unittest tests.compatibility.test_model_catalog_routes -v        # 95 tests, OK
python3 -m unittest tests.compatibility.test_generation_routes_non_streaming -v  # 6 tests, OK
python3 -m unittest tests.compatibility.test_generation_route_image_result -v    # 5 tests, OK
python3 -m unittest tests.compatibility.test_generation_stream_openai -v    # 18 tests, OK
python3 -m unittest tests.compatibility.test_generation_stream_gemini -v    # 41 tests, OK

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
- All 244 existing tests continue to pass.
- 41 new tests added, all passing.
- Combined suite: 285 tests, all passing.

## Recommendation for Next Sprint

Sprint 006I should consider:

1. **HTTP-level streaming tests** for OpenAI and/or Gemini (using `TestClient`
   with `StreamingResponse` body iteration) — requires careful safety gating.
2. **Error propagation tests** at the HTTP transport level.
3. **Gemini streaming static fixture** (FX-GS-001/FX-GS-002) if a runtime
   capture or carefully constructed fixture becomes available.
