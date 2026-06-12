# Generation Route Test Plan

> **Sprint 006A — Route Test Seam Discovery**
> Proposed route-level test stages and Sprint 006B recommended scope.
> This plan is advisory and subject to revision based on implementation findings.

---

## Purpose

This document proposes a staged approach to route-level generation compatibility
testing, building on the static fixture shape assertions established in
Sprints 005B/005D and the seam analysis in [ROUTE_TEST_SEAM_DISCOVERY.md](ROUTE_TEST_SEAM_DISCOVERY.md).

The goal is to verify that the route layer correctly transforms requests and
responses at the HTTP boundary — without calling upstream services, triggering
runtime side effects, or requiring real credentials.

---

## Proposed Route-Level Test Stages

### Stage 1: Conversion-layer unit tests

**Scope:** Test pure conversion functions in `src/api/routes.py` directly.

**Safety:** Highest — no HTTP, no mocking, no side effects.

**Functions to test:**

| Function | Purpose | Assertion focus |
|----------|---------|-----------------|
| `_sanitize_media_prompt` | Strip agent/tool scaffolding | Tool blocks removed, preamble lines dropped |
| `_build_gemini_error_payload` | Construct Gemini error envelope | `error.code`, `error.message`, `error.status` mapping |
| `_normalize_finish_reason` | Map finish reason strings | `stop`→`STOP`, `length`→`MAX_TOKENS`, `None`→`None` |
| `_extract_openai_message_content` | Extract content from OpenAI payload | Handles string and missing choices |
| `_extract_url_from_openai_payload` | Extract URL from payload | Direct URL, markdown image, HTML video patterns |
| `_enrich_payload_with_direct_url` | Add `url` field to payload | Only adds if not already present |
| `_build_video_parts_from_uri` | Build Gemini video parts | `fileData.mimeType`, `fileData.fileUri` |
| `_detect_image_mime_type` | Detect image MIME from bytes | JPEG, PNG, GIF, WebP magic bytes |
| `_should_ignore_media_system_instruction` | Detect ignorable instructions | Long text, tool markers |
| `_coerce_gemini_contents` | Coerce Gemini content list | Dict→GeminiContent conversion |
| `_convert_openai_stream_chunk_to_gemini_event` | Stream chunk conversion | Candidate shape, finishReason mapping (async) |
| `_build_gemini_parts_from_output` | Build Gemini parts from text/image/video | Text-only, markdown image, HTML video (async) |

**Test pattern:**

```python
# Conceptual — not implemented in Sprint 006A
from src.api.routes import _sanitize_media_prompt, _normalize_finish_reason

class SanitizeMediaPromptTests(unittest.TestCase):
    def test_strips_tool_block(self):
        result = _sanitize_media_prompt("Hello <tools>...</tools> world")
        self.assertNotIn("<tools>", result)
        self.assertIn("Hello", result)

    def test_strips_preamble_patterns(self):
        result = _sanitize_media_prompt("You are a function calling AI model.\nDraw a cat.")
        self.assertNotIn("function calling", result)
        self.assertIn("Draw a cat.", result)
```

### Stage 2: Model listing route tests

**Scope:** Test `list_models`, `list_model_aliases`, `get_gemini_model`, `list_gemini_models`
route handlers.

**Safety:** High — these handlers read `MODEL_CONFIG` (module-level dict) and
`get_base_model_aliases()` (pure function). No generation, no upstream calls.

**Auth handling:** Call the route functions directly, passing `api_key="test-key"`
as a keyword argument to satisfy the already-resolved dependency parameter,
without exercising auth behavior.

**Assertions:**

- `/v1/models` response matches `FX-ML-001` shape (reuse `assert_openai_model_list_shape`)
- `/v1/models/aliases` response has `is_alias: true` on each entry
- `/v1beta/models` response has Gemini model resource shape
- `/v1beta/models/{model}` returns 404 for unknown model
- Model count matches `MODEL_CONFIG` entries

**Fixture IDs to use:** `FX-ML-001` (existing static fixture)

### Stage 3: Non-streaming generation route tests with mocked handler

**Scope:** Test `create_chat_completion` (non-streaming) and `generate_content`
with `routes.generation_handler` set to a mock.

**Safety:** Medium-High — requires mocking `generation_handler.handle_generation()`
to return fixture-based responses. No upstream calls if mock is correct.

**Mocking strategy:**

```python
# Conceptual — not implemented in Sprint 006A
from unittest.mock import AsyncMock, MagicMock
from src.api import routes
from src.services.generation_handler import GenerationHandler

# Create a mock handler
mock_handler = MagicMock(spec=GenerationHandler)

async def fake_handle_generation(model, prompt, images, stream, base_url_override, video_media_id):
    # Yield a fixture-based response
    yield json.dumps(fixture_response)

mock_handler.handle_generation = fake_handle_generation

# Set the module global
routes.generation_handler = mock_handler
```

**Assertions:**

- Non-streaming OpenAI response matches `FX-ON-001` shape
- Non-streaming Gemini response matches `FX-GN-001` shape
- Error responses use correct envelope (OpenAI vs. Gemini)
- Empty prompt returns 400

**Fixture IDs to use:** `FX-ON-001`, `FX-ON-002`, `FX-GN-001` (existing static fixtures)

### Stage 4: Streaming generation route tests with mocked handler

**Scope:** Test `create_chat_completion` (streaming) and `stream_generate_content`.

**Safety:** Medium — streaming iteration requires async generator mocking.

**Mocking strategy:** Mock `handle_generation()` to yield fixture-based SSE chunks.

**Assertions:**

- OpenAI stream ends with `data: [DONE]`
- Gemini stream does NOT end with `[DONE]`
- Each chunk has correct envelope shape
- `reasoning_content` chunks are converted to Gemini `parts`

**Fixture IDs to use:** `FX-OS-001`, `FX-OS-002`, `FX-OS-003` (existing static fixtures)

### Stage 5: Auth and error path tests

**Scope:** Test auth failure, unknown model, and error handling.

**Safety:** Medium — requires `TestClient` or direct `Request` construction.

**Assertions:**

- Missing API key returns 401
- Invalid API key returns 401
- Unknown model returns appropriate error
- Handler exception returns 500 with correct envelope

**Defer to Sprint 006C or later** — requires more infrastructure setup.

---

## Import Safety Caution

Before implementing any route-level tests, Sprint 006B must first verify that
importing `src.api.routes` alone does not construct `Database`, `FlowClient`,
`GenerationHandler`, start lifespan logic, initialize browser/captcha/session
services, or call upstream services. If importing `src.api.routes` has side
effects (e.g., via transitive imports of `src.core.config` which may read
`setting.toml` at module level), Sprint 006B should fall back to an even
narrower conversion-helper extraction/testing strategy — testing only the pure
functions that can be isolated without triggering any module-level initialization.

---

## Sprint 006B Recommended Scope

Based on the seam analysis, Sprint 006B should target **Stage 1 and Stage 2**:

### Stage 1: Conversion-layer unit tests

- Import `src.api.routes` conversion functions directly
- Test 8–12 pure functions with 2–3 test cases each
- No mocking required
- Use `unittest.TestCase` (consistent with existing tests)
- Reuse shape assertion helpers from `tests/compatibility/helpers/shape_assertions.py`

### Stage 2: Model listing route tests

- Import `src.api.routes` and call `list_models`, `list_model_aliases`, `get_gemini_model` directly
- Pass `api_key="test-key"` to satisfy the already-resolved dependency parameter (no auth behavior exercised)
- Compare response shape against existing static fixtures
- Use `unittest.IsolatedAsyncioTestCase` for async handlers

### What to include

- Test file: `tests/compatibility/test_route_conversion_layer.py` (Stage 1)
- Test file: `tests/compatibility/test_route_model_listing.py` (Stage 2)
- Reuse existing fixture loader and shape assertions
- No new dependencies
- No new fixture files (use existing Sprint 005A/005C fixtures)

### What to exclude

- Streaming route tests (defer to Stage 4)
- Generation route tests with mocked handler (defer to Stage 3)
- Auth-layer tests (defer to Stage 5)
- `TestClient`-based HTTP tests (defer to Sprint 006C or later)
- Image/video generation tests (require image loading mocks)
- Error path tests (require handler error simulation)

---

## Fixture IDs to Use First

| Fixture ID | File | Sprint created | Stage |
|------------|------|----------------|-------|
| `FX-ML-001` | `generation/model-list/openai-model-list.json` | 005A | Stage 2 |
| `FX-ON-001` | `generation/openai-non-streaming/text-basic-request.json` | 005A | Stage 3 |
| `FX-ON-001` | `generation/openai-non-streaming/text-basic-response.json` | 005A | Stage 3 |
| `FX-ON-002` | `generation/openai-non-streaming/image-result-request.json` | 005C | Stage 3 |
| `FX-ON-002` | `generation/openai-non-streaming/image-result-response.json` | 005C | Stage 3 |
| `FX-GN-001` | `generation/gemini-non-streaming/text-basic-request.json` | 005C | Stage 3 |
| `FX-GN-001` | `generation/gemini-non-streaming/text-basic-response.json` | 005C | Stage 3 |
| `FX-OS-002` | `generation/openai-streaming/reasoning-progress.sse.txt` | 005C | Stage 4 |
| `FX-OS-003` | `generation/openai-streaming/done-termination.sse.txt` | 005A | Stage 4 |

Sprint 006B should primarily use `FX-ML-001` for Stage 2. Stage 1 (conversion
tests) does not require fixture files — it tests function behavior directly.

---

## Mocking Strategy

### Stage 1 (conversion-layer): No mocking required

Pure functions are tested directly. No dependencies to mock.

### Stage 2 (model listing): Minimal mocking

The model listing handlers use `Depends(verify_api_key_flexible)` for auth.
When calling the handler function directly, pass `api_key="test-key"` as a
keyword argument. The `Depends()` wrapper is not invoked because the function
is called directly as a plain async function, not through FastAPI's dependency
injection. This satisfies the parameter without exercising auth behavior.

### Stage 3 (generation with mocked handler): Handler mocking

Set `routes.generation_handler` to a `MagicMock` or custom stub that yields
fixture-based responses from `handle_generation()`. Reset in `tearDown`.

### Stage 4 (streaming): Async generator mocking

Similar to Stage 3, but the mock `handle_generation()` must be an async
generator that yields SSE-formatted strings.

### Stage 5 (auth/error): Dependency override or TestClient

Use `app.dependency_overrides[verify_api_key_flexible]` to control auth
behavior, or construct a minimal `Request` object for direct invocation.

---

## What to Assert

### Stage 1 assertions

- Function output matches expected shape (string, dict, list)
- Edge cases handled (empty input, missing fields, None values)
- Known patterns transformed correctly (tool blocks stripped, URLs extracted)

### Stage 2 assertions

- Response is a dict with correct top-level keys
- Model list matches `assert_openai_model_list_shape` (reuse existing helper)
- Gemini model resource has `supportedGenerationMethods`
- Unknown model returns 404 JSONResponse
- Model count matches `MODEL_CONFIG` entries

### Stage 3 assertions (future)

- Response matches fixture shape (reuse `assert_openai_chat_completion_response_shape`)
- Error responses use correct envelope
- Empty prompt returns 400

### Stage 4 assertions (future)

- Stream chunks have correct SSE framing
- OpenAI stream ends with `data: [DONE]`
- Gemini stream does NOT end with `[DONE]`

---

## What Not to Assert Yet

1. **Exact content semantics** — assert structure, not meaning
2. **Upstream response fidelity** — we are testing the route layer, not the upstream API
3. **Performance or timing** — no latency or throughput assertions
4. **Token lifecycle** — token selection, refresh, and ban logic are not in scope
5. **Captcha/browser behavior** — completely out of scope for route tests
6. **Database writes** — route tests should not verify stats or logging side effects
7. **File cache behavior** — caching is an internal concern, not a compatibility concern

---

## How to Avoid Upstream Calls and Secrets

1. **Never import `src.main`** — import `src.api.routes` directly
2. **Never run the lifespan** — do not create a FastAPI app with `lifespan=lifespan`
3. **Mock `generation_handler`** — set `routes.generation_handler` to a mock before tests
4. **Use placeholder API keys** — pass `api_key="test-key"` as the already-resolved dependency parameter (no auth behavior exercised)
5. **No real image URLs** — text-only tests avoid the `retrieve_image_data` path
6. **No real tokens** — mock handler does not call `token_manager` or `flow_client`
7. **Fixture-based responses** — mock handler yields fixture JSON, not real upstream data
8. **Temporary directories** — if `FileCache` is needed, use `tempfile.TemporaryDirectory()`

---

## Fallback Plan If App Import Is Unsafe

If importing `src.api.routes` triggers unexpected side effects (e.g., config
module fails to load without `setting.toml`), the following fallback strategies
are available:

### Fallback A: Provide a minimal config file

Create a temporary `setting.toml` in the test `setUp()` with minimal required
fields. Set the config file path via environment variable or monkeypatch.

### Fallback B: Mock the config module before import

Use `unittest.mock.patch.dict` to set `sys.modules['src.core.config']` to a
mock module before importing `src.api.routes`.

### Fallback C: Test only the conversion functions that do not require config

Some conversion functions (e.g., `_sanitize_media_prompt`, `_normalize_finish_reason`)
do not depend on config at all. These can be tested by copying the function
logic into a test helper (not ideal, but safe).

### Fallback D: Defer route tests and expand conversion-layer coverage

If all import strategies prove unsafe, Sprint 006B can focus on expanding the
static fixture assertions (similar to Sprint 005D) and defer route-level tests
to a later sprint with more infrastructure.

---

## Summary

| Stage | Scope | Safety | Sprint |
|-------|-------|--------|--------|
| 1 | Conversion-layer pure functions | Highest | 006B (recommended) |
| 2 | Model listing route handlers | High | 006B (recommended) |
| 3 | Non-streaming generation with mocked handler | Medium-High | 006C or later |
| 4 | Streaming generation with mocked handler | Medium | 006C or later |
| 5 | Auth and error paths | Medium | 006D or later |

Sprint 006B should establish the conversion-layer test foundation and verify
model listing compatibility. This provides immediate value without the risk
of handler mocking or HTTP infrastructure.
