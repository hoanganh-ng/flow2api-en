# Sprint 006F — Mocked OpenAI Image-Result Route Contract

> **Status:** ✅ Completed
> **Scope:** Characterize the OpenAI non-streaming image-result route path
> represented by FX-ON-002, using fully synthetic data and no network or
> external media retrieval.

---

## Purpose

This sprint characterizes the OpenAI non-streaming image-result route path
(`create_chat_completion` with `stream=False` yielding markdown image content)
via direct Python function calls with a fake handler. The goal is to document
the actual call chain, fake-handler yield protocol, and relationship to the
FX-ON-002 fixture, while confirming that the route does not invoke any network
or external media retrieval helpers.

---

## Safety Gate

**Result: PASSED**

The image-result route path requires no network, HTTP image retrieval, external
file access, real image assets, upstream services, database, browser, captcha,
token, proxy, or session behavior when invoked with a text-only request
(no `image_url` in messages, no historical assistant messages with image URLs).

The route layer parses the handler's JSON output and returns it as-is without
processing the image URL. The markdown image content (`![Generated Image](url)`)
is preserved verbatim in the response.

### Network/Media Helpers Identified

| Helper | Location | Risk |
|--------|----------|------|
| `retrieve_image_data` | `src/api/routes.py` L171 | Network — HTTP GET via `curl_cffi.AsyncSession` |
| `_load_image_bytes_from_uri` | `src/api/routes.py` L221 | Network — calls `retrieve_image_data` for non-data URIs |

### Helpers Guarded During Tests

Both `retrieve_image_data` and `_load_image_bytes_from_uri` were patched to
raise `RuntimeError` immediately if invoked. The tests confirmed that the
image-result route path does not trigger these helpers.

---

## Image-Result Route Call Chain

### Route Function

```python
@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
    api_key: str = Depends(verify_api_key_flexible),
):
```

### Non-Streaming Image-Result Path (`stream=False`)

```
create_chat_completion
  → _normalize_openai_request(request)
    → _extract_prompt_and_images_from_openai_messages(messages)
      [no image_url in messages → no _load_image_bytes_from_uri call]
    → _resolve_request_model(model, request)
      → resolve_model_name(model, request, MODEL_CONFIG)  [pure]
    → _append_openai_reference_images(model, messages, images)
      [no historical assistant messages with images → no retrieve_image_data call]
  → _get_request_base_url(raw_request)  [reads request.headers]
  → _collect_non_stream_result(model, prompt, images, base_url, video_media_id)
    → _ensure_generation_handler()
      → reads src.api.routes.generation_handler
    → handler.handle_generation(...)  [async generator]
      → consumes single yielded result (JSON string)
  → _parse_handler_result(result)  [json.loads]
  → _build_openai_json_response(payload)
    → _get_error_status_code(payload)  [returns 200 on success]
```

**Response:** `JSONResponse` with status 200, body containing the parsed JSON.

### Key Observation

The route layer does **not** process the image URL in the handler's output.
The markdown image content is preserved verbatim in `choices[0].message.content`.
No network or media retrieval occurs in the response path.

---

## Fake-Handler Output Protocol

### Signature

```python
async def handle_generation(
    self,
    model: str,
    prompt: str,
    images=None,
    stream: bool = False,
    base_url_override=None,
    video_media_id=None,
) -> AsyncGenerator[str, None]:
```

### Image-Result Yield

```python
yield json.dumps({
    "id": "chatcmpl-1700000000",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "flow2api",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "![Generated Image](https://placeholder.example.invalid/media/test-image.jpg)"
        },
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }
})
```

The fake handler yields a single JSON string with markdown image content.
The route layer parses this and returns it as a `JSONResponse`.

---

## Relationship to FX-ON-002

### FX-ON-002 Fixture

- **Request:** `tests/fixtures/generation/openai-non-streaming/image-result-request.json`
- **Response:** `tests/fixtures/generation/openai-non-streaming/image-result-response.json`

### Shape Compatibility

| Field | Fixture | Route Output | Match |
|-------|---------|--------------|-------|
| `choices` | ✅ present | ✅ present | ✅ |
| `choices[0].message.content` | `![Generated Image](url)` | `![Generated Image](url)` | ✅ |
| `choices[0].finish_reason` | `"stop"` | `"stop"` | ✅ |
| `id` | `"chatcmpl-1700000000"` | handler-provided | fixture-only |
| `object` | `"chat.completion"` | `"chat.completion"` | ✅ |
| `created` | `1700000000` | handler-provided | fixture-only |
| `model` | `"flow2api"` | `"flow2api"` | ✅ |
| `usage` | `{prompt_tokens: 0, ...}` | handler-provided | fixture-only |

### Fixture-Only Fields

- `id`, `created`, `usage` are static in the fixture but dynamic in the route
  output (provided by the fake handler). These are acceptable differences for
  synthetic fixtures.

### Contract Semantics

- Markdown image pattern `![Generated Image](url)` is preserved.
- `finish_reason: "stop"` is preserved.
- Response is `JSONResponse`, not `StreamingResponse`.

---

## Tests Implemented

### Test File

`tests/compatibility/test_generation_route_image_result.py`

### Test Classes and Methods

| Class | Test | Description |
|-------|------|-------------|
| `OpenAIImageResultSuccessTests` | `test_openai_image_result_success` | Verify image-result route returns JSON with markdown image content |
| `OpenAIImageResultSuccessTests` | `test_openai_image_result_stable_structure` | Verify stable image-result structure matches expected shape |
| `FXON002RelationshipTests` | `test_fx_on_002_shape_compatibility` | Verify route output matches FX-ON-002 fixture shape and semantics |
| `FXON002RelationshipTests` | `test_fx_on_002_contract_semantics` | Verify contract semantics: markdown image, finish_reason, no streaming |
| `NetworkMediaHelperGuardTests` | `test_no_network_or_media_retrieval` | Confirm successful response without media retrieval |

### Test Count

- **New tests:** 5
- **Existing tests (before sprint):** 221
- **Combined tests (after sprint):** 226

### Test Approach

- Standard-library `unittest` with `IsolatedAsyncioTestCase`
- `unittest.mock.patch` for `generation_handler`, `retrieve_image_data`, `_load_image_bytes_from_uri`
- Direct calls to `create_chat_completion` (no FastAPI app or TestClient)
- Minimal Starlette `Request` for `_get_request_base_url`
- Test-local fake generation handler
- Synthetic values only

---

## Verification

### Commands Run

```bash
# Baseline verification
git status --short  # clean
git log -5 --oneline  # commits 7257afe and 8085205 present
python3 -m unittest discover -s tests/compatibility -p "test_*.py"  # 221 tests pass

# New test file
python3 -m unittest tests.compatibility.test_generation_route_image_result -v  # 5 tests pass

# Full suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py"  # 226 tests pass

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"  # OK

# No runtime source changes
git diff -- src  # empty
git diff --check  # clean
git status --short  # clean (only new files)
```

### Test Counts

| Suite | Tests | Status |
|-------|-------|--------|
| Static fixture tests | 48 | ✅ pass |
| Route conversion helpers | 67 | ✅ pass |
| Model catalog routes | 95 | ✅ pass |
| Non-streaming routes | 6 | ✅ pass |
| **Image-result routes** | **5** | ✅ pass |
| **Combined** | **226** | ✅ pass |

---

## Files Created and Modified

### New Files

| File | Purpose |
|------|---------|
| `tests/compatibility/test_generation_route_image_result.py` | 5 mocked image-result route tests |
| `docs/SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md` | This sprint document |

### Updated Files

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006F to history, updated current sprint |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006F summary |
| `docs/SPRINTS/README.md` | Added Sprint 006F to sprint index |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Updated FX-ON-002 tested status |

### Runtime Source

**No files under `src/` were modified.**

---

## Confirmation

- ✅ Safety gate passed — no network or external media retrieval required
- ✅ Image-result route call chain documented
- ✅ Fake-handler yield protocol documented
- ✅ Relationship to FX-ON-002 documented
- ✅ Network/media helpers identified and guarded
- ✅ 5 tests implemented and passing
- ✅ 226 combined tests passing
- ✅ No streaming or Gemini media retrieval occurred
- ✅ No runtime source changed
- ✅ No commits or pushes made

---

## Deferred

- Streaming image results (requires `StreamingResponse` testing approach)
- Gemini image results (requires `_build_gemini_parts_from_output` which calls `retrieve_image_data`)
- Video results (FX-ON-003, FX-GN-002)
- Reference-image input handling (historical assistant messages with image URLs)
- `extend://` video continuation (FX-CX-001)

---

## Recommendation for Following Sprint

**Sprint 006G (suggested):** Mocked OpenAI streaming route tests covering:
- `_iterate_openai_stream` async generator with fake handler
- SSE framing (`data: {json}\n\n`, `data: [DONE]\n\n`)
- Reasoning content delta (FX-OS-002)
- Termination event (FX-OS-003)

**Alternative:** Gemini non-streaming image-result route tests (if `_build_gemini_parts_from_output`
can be safely tested with synthetic data URLs or by patching `retrieve_image_data`).

---

## Scope Confirmation

This sprint intentionally excluded:
- Gemini image results
- Streaming (OpenAI and Gemini)
- Video results
- Reference-image input handling
- External image URLs or real downloads
- Local image files
- Authentication, database, browser, captcha, proxy, session services
- Runtime source modifications
