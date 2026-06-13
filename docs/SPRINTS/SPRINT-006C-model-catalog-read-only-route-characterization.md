# Sprint 006C — Model Catalog and Read-Only Route Characterization

## Goal

Characterize the model catalog helpers and the safest read-only model route
functions without starting FastAPI, lifespan, authentication dependencies,
upstream services, or generation behavior.

---

## Source Discovery

### Functions Discovered

| Function | Module | Route path(s) | Type | Description |
|----------|--------|---------------|------|-------------|
| `_build_model_description` | `src.api.routes` | (helper) | sync | Builds human-readable description from model config dict |
| `_get_openai_model_catalog` | `src.api.routes` | (helper) | sync | Returns list of `{id, description}` for all MODEL_CONFIG entries |
| `_get_gemini_model_catalog` | `src.api.routes` | (helper) | sync | Returns dict of model_id → description (aliases + MODEL_CONFIG) |
| `_build_gemini_model_resource` | `src.api.routes` | (helper) | sync | Builds Gemini-compatible model resource dict |
| `get_base_model_aliases` | `src.core.model_resolver` | (helper) | sync | Returns simplified alias map for image/video base models |
| `list_models` | `src.api.routes` | `GET /v1/models` | async | OpenAI-compatible model list route |
| `list_model_aliases` | `src.api.routes` | `GET /v1/models/aliases` | async | Simplified alias list route |
| `list_gemini_models` | `src.api.routes` | `GET /v1beta/models`, `GET /models` | async | Gemini-compatible model list route |
| `get_gemini_model` | `src.api.routes` | `GET /v1beta/models/{model}`, `GET /models/{model}` | async | Single Gemini model lookup route |

### Dependencies on MODEL_CONFIG

- `_build_model_description` reads `type`, `model_name`, and `model_key` from a
  model config dict passed as a parameter.
- `_get_openai_model_catalog` iterates `MODEL_CONFIG.items()` directly.
- `_get_gemini_model_catalog` iterates `MODEL_CONFIG.items()` and merges with
  `get_base_model_aliases()`.
- `list_models` calls `_get_openai_model_catalog()`.
- `list_gemini_models` calls `_get_gemini_model_catalog()` and
  `_build_gemini_model_resource()`.
- `get_gemini_model` calls `_get_gemini_model_catalog()` and
  `_build_gemini_model_resource()`.

### Dependencies on high-risk services

None of the tested functions call `generation_handler`, `FlowClient`,
`TokenManager`, `Database`, browser/captcha services, or network access.
All tested functions use only local constants, `MODEL_CONFIG` (a module-level
dict), and `get_base_model_aliases()` (which reads local constants from
`model_resolver.py`).

---

## Safety Gate

### Functions selected for testing

All 9 discovered functions were selected. Each is fully local:

- `_build_model_description` — pure function on a dict parameter.
- `_get_openai_model_catalog` — reads `MODEL_CONFIG` only.
- `_get_gemini_model_catalog` — reads `MODEL_CONFIG` and `get_base_model_aliases()`.
- `_build_gemini_model_resource` — pure function on two string parameters.
- `get_base_model_aliases` — reads local constants from `model_resolver.py`.
- `list_models` — calls `_get_openai_model_catalog()`, returns a dict.
- `list_model_aliases` — calls `get_base_model_aliases()`, returns a dict.
- `list_gemini_models` — calls `_get_gemini_model_catalog()`, returns a dict.
- `get_gemini_model` — calls `_get_gemini_model_catalog()`, returns dict or
  JSONResponse(404).

### Functions omitted and reasons

No discovered model-catalog functions were omitted. All are fully local.

Generation routes (`create_chat_completion`, `generate_content`,
`stream_generate_content`), WebSocket endpoints (`captcha_ws`), and helper
functions that call `_ensure_generation_handler()` or perform network I/O
(`retrieve_image_data`, `_load_image_bytes_from_uri`, etc.) were **not**
tested because they cross high-risk boundaries (handler instantiation,
upstream calls, network access).

---

## Sync/Async Behavior

| Function | Sync/Async |
|----------|------------|
| `_build_model_description` | sync |
| `_get_openai_model_catalog` | sync |
| `_get_gemini_model_catalog` | sync |
| `_build_gemini_model_resource` | sync |
| `get_base_model_aliases` | sync |
| `list_models` | async |
| `list_model_aliases` | async |
| `list_gemini_models` | async |
| `get_gemini_model` | async |

---

## Dependency Parameter Handling

Route functions (`list_models`, `list_model_aliases`, `list_gemini_models`,
`get_gemini_model`) accept an `api_key` parameter normally populated through
FastAPI dependency resolution (`Depends(verify_api_key_flexible)`). In these
tests, the parameter is supplied directly as a Python function argument
(`api_key="test-key"`). This is supplying the already-resolved dependency
parameter during a direct Python function call. Authentication behavior is
not exercised.

---

## Observed Contracts

### `_build_model_description(model_config: dict) -> str`

- For `type == "image"`: returns `"Image generation - {model_name}"`.
- For `type == "video"`: returns `"Video generation - {model_key}"`.
- For other types: returns `"{Type} generation - {model_key}"` (capitalized).

### `_get_openai_model_catalog() -> List[Dict[str, str]]`

- Returns one entry per `MODEL_CONFIG` key, preserving insertion order.
- Each entry has exactly two keys: `id` and `description`.
- IDs are unique and match `MODEL_CONFIG.keys()` exactly.
- No secrets or sensitive data in descriptions.

### `_get_gemini_model_catalog() -> Dict[str, str]`

- Merges `get_base_model_aliases()` with `MODEL_CONFIG` entries.
- Alias entries take precedence (via `setdefault`) over MODEL_CONFIG entries
  with the same key.
- Size is >= `len(MODEL_CONFIG)`.
- The catalog is exactly the union of alias IDs and MODEL_CONFIG keys.

### `_build_gemini_model_resource(model_id: str, description: str) -> dict`

- Returns a dict with 7 keys: `name`, `displayName`, `description`, `version`,
  `inputTokenLimit`, `outputTokenLimit`, `supportedGenerationMethods`.
- `name` is `"models/{model_id}"`.
- `version` is always `"flow2api"`.
- Token limits are always `0`.
- `supportedGenerationMethods` is `["generateContent", "streamGenerateContent"]`.

### `get_base_model_aliases() -> Dict[str, str]`

- Returns image aliases (3: gemini-3.0-pro-image, gemini-3.1-flash-image,
  imagen-4.0-generate-preview) and video aliases (many veo_3_1_* names).
- Image alias descriptions contain "aspects:" and supported aspect ratios.
- Video alias descriptions mention "landscape/portrait via generationConfig".

### `list_models(api_key: str) -> dict`

- Returns `{"object": "list", "data": [...]}`.
- Each data entry has exactly 4 keys: `id`, `object` ("model"), `owned_by`
  ("flow2api"), `description`.
- Data entries do **not** contain `created` (fixture-only field; see FX-ML-001
  relationship below).
- Data count matches `_get_openai_model_catalog()` length.
- IDs match catalog IDs in order.
- No sensitive fields (api_key, token, secret) in output.

### `list_model_aliases(api_key: str) -> dict`

- Returns `{"object": "list", "data": [...]}`.
- Each entry has: `id`, `object` ("model"), `owned_by` ("flow2api"),
  `description`, `is_alias` (True).
- Count and IDs match `get_base_model_aliases()`.

### `list_gemini_models(api_key: str) -> dict`

- Returns `{"models": [...]}`.
- Each model has the Gemini resource shape (7 keys).
- Count and displayNames match `_get_gemini_model_catalog()`.
- All entries have `version: "flow2api"`, token limits 0, and both
  generation methods.

### `get_gemini_model(model: str, api_key: str) -> dict | JSONResponse`

- Known model (in catalog): returns Gemini resource dict.
- Alias model: returns Gemini resource dict.
- Unknown model: returns `JSONResponse(status_code=404)` with error payload
  `{"error": {"code": 404, "message": "Model not found: {model}",
  "status": "NOT_FOUND"}}`.

---

## Relationship to FX-ML-001

FX-ML-001 (`tests/fixtures/generation/model-list/openai-model-list.json`)
is a synthetic structural fixture with 3 model entries and a `created`
field. The current `/v1/models` route does **not** emit a `created` field.

Key points:

- FX-ML-001 is a synthetic structural fixture, not a captured runtime response.
- The `created` field is fixture-only relative to the current implementation.
- The `created` field is not a required current-runtime field.
- No runtime change is proposed to add or remove `created`.
- The test `test_entries_do_not_contain_created` explicitly asserts that
  current route entries do not contain `created`.
- The test `test_structural_compatibility_with_fixture` verifies shared
  contract shape (object=list, data entries with id/object/owned_by)
  without requiring exact equality with the fixture.

At the time of Sprint 006C, `MODEL_CONFIG` contained 167 entries (32 image,
135 video). Tests derive expected counts from the live `MODEL_CONFIG` dict
and helper output; the snapshot number is recorded here for documentation
only and is not used as an independent test oracle.

---

## MODEL_CONFIG Summary

- **Total models:** 167
- **By type:** 32 image, 135 video
- **Image model families:** gemini-3.0-pro-image (GEM_PIX_2),
  gemini-3.1-flash-image (NARWHAL), imagen-4.0-generate-preview (IMAGEN_3_5)
- **Video model families:** veo_3_1_t2v_*, veo_3_1_i2v_*, veo_3_1_r2v_*,
  veo_3_1_extend, veo_3_1_interpolation_*

---

## Commands and Results

```bash
# Import smoke check
$ python3 -c "import src.api.routes; print('src.api.routes import: OK')"
src.api.routes import: OK

# Existing static fixture suite
$ python3 -m unittest tests.compatibility.test_static_generation_fixtures -v
Ran 53 tests in 0.007s
OK

# Existing route conversion helper tests
$ python3 -m unittest tests.compatibility.test_route_conversion_helpers -v
Ran 67 tests in 0.005s
OK

# New model catalog route tests
$ python3 -m unittest tests.compatibility.test_model_catalog_routes -v
Ran 95 tests in 0.079s
OK

# Combined compatibility suite
$ python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
Ran 215 tests in 0.087s
OK

# Source unchanged
$ git diff -- src
(no output)

# No whitespace issues
$ git diff --check
(no output)
```

---

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `tests/compatibility/test_model_catalog_routes.py` | 95 unit tests for 5 helpers and 4 read-only route functions |

### Unchanged

- No files under `src/` were modified.
- No dependencies were added.

---

## Runtime Source Confirmation

- **No runtime source files were changed.** `git diff -- src` produces no output.
- **No HTTP transport was tested.** Route functions were called directly as Python
  functions.
- **No authentication validation was tested.** The `api_key` parameter was
  supplied as an already-resolved dependency value.
- **No upstream calls occurred.** All tests are offline and deterministic.
- **No database, browser, captcha, token, proxy, or session activity occurred.**

---

## Limitations

1. **Async route functions use `IsolatedAsyncioTestCase`.** Each async test
   method gets its own event loop. This is stdlib-standard and does not
   require pytest-asyncio.

2. **`list_models` does not emit a `created` field.** The FX-ML-001 fixture
   includes `"created": 1700000000` but the current route implementation does
   not emit this field. The test `test_entries_do_not_contain_created`
   explicitly characterizes this behavior. The `created` field is
   fixture-only relative to the current implementation. No runtime change
   is proposed.

3. **Gemini catalog merge behavior.** When an alias ID collides with a
   MODEL_CONFIG key, the alias description takes precedence (via
   `dict.setdefault`). This is characterized but not modified.

4. **Coverage is read-only routes only.** Generation routes, streaming,
   request normalization, and error handling routes are not tested here.

5. **Config file dependency.** Importing `src.api.routes` reads
   `config/setting_example.toml` via the `Config` class. If this file is
   missing or unreadable, the import will fail.

---

## Status

**COMPLETED**
