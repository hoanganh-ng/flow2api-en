# Route Test Seam Discovery

> **Sprint 006A — Route Test Seam Discovery**
> Discovery-only analysis of the safest integration point for future route-level
> generation compatibility tests. No tests were implemented in this sprint.

---

## Purpose

This document records the findings from inspecting the flow2api-en codebase to
identify the safest "seam" for future route-level generation compatibility tests.
A test seam is the boundary where test code can intercept runtime behavior without
triggering unsafe side effects (database writes, upstream calls, token lifecycle,
captcha/browser startup, proxy initialization).

Sprint 005B added offline static fixture shape assertions that do not import the
runtime application. Sprint 006A investigates how to go further — testing the
actual route handlers — while preserving the safety guarantees established in
earlier sprints.

---

## Files Inspected

| File | Purpose |
|------|---------|
| `src/main.py` (lines 1–256) | FastAPI app construction, lifespan, dependency wiring |
| `src/api/__init__.py` (lines 1–7) | Router re-exports |
| `src/api/routes.py` (lines 1–1003) | Generation route handlers, request normalization, response conversion |
| `src/api/admin.py` (lines 1–30) | Admin router mounting context (imports, router creation) |
| `src/core/auth.py` (lines 1–63) | API key verification dependency |
| `src/core/models.py` (lines 1–301) | Pydantic request/response models |
| `src/core/model_resolver.py` (lines 1–634) | Model name resolution logic |
| `src/services/generation_handler.py` (lines 1–120, 922–1046) | Generation handler class, `handle_generation` signature |
| `src/services/flow_client.py` (lines 1–100) | Upstream API client constructor |
| `tests/compatibility/test_static_generation_fixtures.py` | Offline static fixture tests (Sprint 005B/005D) |
| `tests/test_daily_stats_reset.py` | Database-level async test pattern |
| `tests/test_flow_client_upload.py` | FlowClient unit test with `AsyncMock` |
| `tests/test_veo_lite_support.py` | Model resolver + handler unit tests |
| `tests/test_yescaptcha_task_type.py` | Config normalization unit tests |
| `tests/test_browser_captcha_personal.py` | Browser captcha service unit tests |
| `tests/testgeneration_config_max_retries.py` | Config + database integration test |

---

## Current App/Router Construction Summary

Observed in `src/main.py`:

1. **Module-level singletons** are created immediately on import (lines 166–179):
   - `db = Database()`
   - `proxy_manager = ProxyManager(db)`
   - `flow_client = FlowClient(proxy_manager, db)`
   - `token_manager = TokenManager(db, flow_client)`
   - `concurrency_manager = ConcurrencyManager()`
   - `load_balancer = LoadBalancer(token_manager, concurrency_manager)`
   - `generation_handler = GenerationHandler(flow_client, token_manager, load_balancer, db, concurrency_manager, proxy_manager)`

2. **Dependency injection** is done via module-level setter (line 182):
   - `routes.set_generation_handler(generation_handler)` — sets a module global in `routes.py`
   - `admin.set_dependencies(token_manager, proxy_manager, db, concurrency_manager)`

3. **Lifespan context manager** (`lifespan()`, lines 22–163) performs heavy startup:
   - Database initialization (`db.init_db()`)
   - Config loading from `setting.toml`
   - Config sync to memory (`db.reload_config_to_memory()`)
   - File cache timeout and cleanup task
   - Captcha config loading
   - Token snapshot retrieval
   - Browser captcha service initialization (personal or headed mode)
   - Browser resident tab warmup
   - Concurrency manager initialization
   - Remote browser prefill
   - 429 auto-unban background task

4. **FastAPI app creation** (line 186) uses `lifespan=lifespan`.

5. **Router mounting** (lines 203–204):
   - `app.include_router(routes.router)` — generation endpoints
   - `app.include_router(admin.router)` — admin endpoints

6. **Static file serving** and HTML routes follow (lines 207–255).

### Key observation

Importing `src.main` triggers module-level singleton construction but does NOT
trigger the lifespan. The lifespan only runs when the ASGI server starts.
However, the singleton constructors themselves may have side effects:
- `Database()` — appears to only store the path, no file I/O in `__init__`
- `ProxyManager(db)` — stores db reference
- `FlowClient(proxy_manager, db)` — stores references, reads config values
- `TokenManager(db, flow_client)` — stores references
- `GenerationHandler(...)` — creates `FileCache` which creates a directory (`tmp/`)

---

## Observed Generation Dependencies

### Route handler dependency chain

```
POST /v1/chat/completions
  → verify_api_key_flexible (auth)
  → _normalize_openai_request
    → _extract_prompt_and_images_from_openai_messages
      → _load_image_bytes_from_uri (if image_url present)
        → retrieve_image_data (HTTP call via curl_cffi)
    → _resolve_request_model (pure logic)
    → _append_openai_reference_images (may fetch images)
  → _collect_non_stream_result or _iterate_openai_stream
    → generation_handler.handle_generation()
      → load_balancer (token selection)
      → token_manager (token lifecycle)
      → flow_client (upstream API calls)
      → db (stats, logging)
      → file_cache (result caching)
```

### Auth dependency

`verify_api_key_flexible` (src/core/auth.py, lines 44–62):
- Accepts API key from: `Authorization: Bearer`, `x-goog-api-key` header, or `?key=` query param
- Compares against `config.api_key` (loaded from config module)
- Raises `HTTPException(401)` on failure

### Generation handler dependency

`GenerationHandler.__init__` (src/services/generation_handler.py, lines 925–937):
- Requires: `flow_client`, `token_manager`, `load_balancer`, `db`, `concurrency_manager`, `proxy_manager`
- Creates `FileCache` which creates a `tmp/` directory on disk

---

## Safe Test Seam Candidates

### Candidate 1: Conversion-layer pure functions (SAFEST)

The `routes.py` module contains numerous pure or near-pure functions that perform
request normalization and response conversion without side effects:

| Function | Lines | Purpose | Side effects |
|----------|-------|---------|--------------|
| `_build_model_description` | 97–104 | Build model description string | None |
| `_get_openai_model_catalog` | 107–115 | Collect OpenAI model list | Reads `MODEL_CONFIG` (module-level dict) |
| `_get_gemini_model_catalog` | 118–128 | Collect Gemini model list | Reads `MODEL_CONFIG` + `get_base_model_aliases()` |
| `_decode_data_url` | 147–151 | Decode data: URLs | None |
| `_detect_image_mime_type` | 154–163 | Detect image MIME from bytes | None |
| `_sanitize_media_prompt` | 267–286 | Strip agent scaffolding from prompts | None |
| `_should_ignore_media_system_instruction` | 255–264 | Detect ignorable system instructions | None |
| `_extract_text_from_gemini_content` | 248–252 | Extract text from Gemini content | None |
| `_parse_handler_result` | 509–513 | Parse JSON handler output | None |
| `_get_error_status_code` | 516–525 | Extract error status from payload | None |
| `_build_openai_json_response` | 528–529 | Build OpenAI JSON response | None |
| `_build_gemini_error_payload` | 532–539 | Build Gemini error payload | None |
| `_extract_openai_message_content` | 552–559 | Extract content from OpenAI payload | None |
| `_extract_url_from_openai_payload` | 562–579 | Extract URL from OpenAI payload | None |
| `_enrich_payload_with_direct_url` | 582–586 | Add direct URL to payload | None |
| `_normalize_finish_reason` | 674–682 | Map finish reason strings | None |
| `_build_video_parts_from_uri` | 622–630 | Build Gemini video parts | None |
| `_coerce_gemini_contents` | 238–245 | Coerce Gemini content list | None |

**Safety:** These functions can be imported and tested directly without any
mocking. They do not touch the database, network, or filesystem.

**Limitation:** They do not exercise the full route handler (no HTTP layer).

### Candidate 2: Model resolver tests (ALREADY EXIST)

The `resolve_model_name` function (src/core/model_resolver.py, lines 515–613)
is already tested in `tests/test_veo_lite_support.py`. Additional resolver
tests can be added safely:

**Safety:** Pure function, no side effects.

### Candidate 3: Direct route handler invocation with mocked handler

The route handlers in `routes.py` are plain async functions decorated with
`@router.post(...)`. They can be invoked directly in a test by:

1. Setting `routes.generation_handler` to a mock object before the test
2. Constructing a Pydantic request model (e.g., `ChatCompletionRequest`)
3. Constructing a minimal `Request` object (or mocking it)
4. Calling the handler function directly

**Safety:** No HTTP server, no lifespan, no upstream calls if handler is mocked.

**Challenge:** Constructing a valid `Request` object for `_get_request_base_url`
requires either a real Starlette `Request` or careful mocking.

### Candidate 4: FastAPI TestClient with no-op lifespan override

FastAPI's `TestClient` (via `httpx`) can be used with a custom app that has
the lifespan disabled:

```python
# Conceptual (not implemented in this sprint)
from fastapi import FastAPI
from fastapi.testclient import TestClient

test_app = FastAPI()  # No lifespan
test_app.include_router(routes.router)
# Set routes.generation_handler to a mock before tests
```

**Safety:** The original `src.main` module is never imported, so no singletons
are created and no lifespan runs.

**Challenge:** The `routes` module imports `generation_handler` at module level
(line 71: `generation_handler: GenerationHandler = None`), which is safe (just
a type annotation). The actual handler is set via `set_generation_handler()`.

### Candidate 5: Monkeypatched generation handler module global

The simplest approach: import `src.api.routes` directly (which does NOT trigger
`src.main` import), set `routes.generation_handler` to a mock, and then either:
- Call route functions directly (Candidate 3)
- Use `TestClient` with a minimal app (Candidate 4)

**Safety:** Importing `src.api.routes` only imports:
- `fastapi` (framework)
- `curl_cffi.requests` (HTTP client library, but `AsyncSession` is only used in `retrieve_image_data`)
- `src.core.auth` (which imports `src.core.config`)
- `src.core.logger`
- `src.core.model_resolver`
- `src.core.models`
- `src.services.generation_handler` (which imports `src.core.config`, `src.services.file_cache`)
- `src.services.browser_captcha_extension` (import only, no instantiation)

**Risk:** Importing `src.services.generation_handler` creates the `MODEL_CONFIG`
dict (safe, just data) and imports `FileCache`. Importing `src.core.config`
reads `setting.toml` at module level — to be confirmed whether this fails
gracefully if the file is missing.

### Candidate 6: Dependency injection hook

FastAPI's `Depends()` mechanism could be overridden via `app.dependency_overrides`:

```python
# Conceptual
app.dependency_overrides[verify_api_key_flexible] = lambda: "test-api-key"
```

**Safety:** This avoids the auth check without mocking the config module.

**Limitation:** Still requires importing the app or constructing a test app.

---

## Unsafe Approaches to Avoid

### 1. Importing `src.main` directly

**Risk level:** HIGH

Importing `src.main` creates module-level singletons:
- `Database()` — low risk (just stores path)
- `FlowClient(proxy_manager, db)` — reads config values
- `GenerationHandler(...)` — creates `tmp/` directory via `FileCache`

While the lifespan is NOT triggered on import, the singleton constructors may
have subtle side effects (filesystem access, config reads).

### 2. Running the lifespan context manager

**Risk level:** CRITICAL

The `lifespan()` function (src/main.py, lines 22–163):
- Initializes the database (`db.init_db()`)
- Loads config from `setting.toml`
- Syncs config to memory
- Starts file cache cleanup tasks
- Initializes browser captcha service (if configured)
- Warms up browser resident tabs (launches real browsers)
- Starts 429 auto-unban background tasks

**This must never be triggered in a test without comprehensive mocking.**

### 3. Tests that touch database/config writes

**Risk level:** HIGH

Any test that calls `db.init_db()`, `db.init_config_from_toml()`, or
`db.update_generation_config()` without using a temporary database file
risks modifying the development database.

**Note:** Existing tests in `tests/test_daily_stats_reset.py` and
`tests/testgeneration_config_max_retries.py` use `tempfile.TemporaryDirectory()`
to isolate database writes — this pattern should be followed.

### 4. Tests that refresh tokens or call upstream services

**Risk level:** CRITICAL

`TokenManager` methods like `get_all_tokens()`, `refresh_token()`, and
`FlowClient` methods like `generate_image()`, `generate_video_text()` make
real HTTP calls to upstream services.

### 5. Tests that start captcha/browser/session components

**Risk level:** CRITICAL

`BrowserCaptchaService` launches real browser instances. Any test that
instantiates or calls this service without comprehensive mocking will start
real browsers.

### 6. Tests that require real credentials

**Risk level:** HIGH

The `verify_api_key_flexible` dependency compares against `config.api_key`.
Tests should either:
- Mock the dependency via `app.dependency_overrides`
- Set `config.api_key` to a known test value (if config is mutable in tests)
- Call the route function directly, passing `api_key="test-key"` as a keyword argument to satisfy the already-resolved dependency parameter, without exercising auth behavior

---

## Recommended First Route-Level Test Slice

Based on the seam analysis, the recommended first route-level test slice for
Sprint 006B is:

### Tier 1: Conversion-layer unit tests (no HTTP, no mocking)

Test the pure conversion functions in `routes.py` directly:
- `_sanitize_media_prompt` — prompt sanitization
- `_build_gemini_error_payload` — error envelope construction
- `_normalize_finish_reason` — finish reason mapping
- `_extract_url_from_openai_payload` — URL extraction
- `_build_gemini_parts_from_output` — parts construction (async, but no side effects for text-only)
- `_convert_openai_stream_chunk_to_gemini_event` — stream chunk conversion

### Tier 2: Route handler tests with mocked generation handler

Test the route handlers with `routes.generation_handler` set to a mock:
- `list_models` — model listing (no generation, reads `MODEL_CONFIG`)
- `list_model_aliases` — alias listing (reads `get_base_model_aliases()`)
- `get_gemini_model` — single model lookup
- `create_chat_completion` (non-streaming, text-only, no images) — with mocked handler
- `generate_content` (non-streaming, text-only, no images) — with mocked handler

### What to defer

- Streaming route tests (complex async iteration)
- Image/video generation tests (require image loading mocks)
- Auth-layer tests (require dependency override setup)
- Error path tests (require handler error simulation)

---

## Import Safety Caution

Sprint 006B must first verify that importing `src.api.routes` alone does not
construct `Database`, `FlowClient`, `GenerationHandler`, start lifespan logic,
initialize browser/captcha/session services, or call upstream services. If
importing `src.api.routes` has side effects (e.g., via transitive imports of
`src.core.config` which reads `setting.toml` at module level), Sprint 006B
should fall back to an even narrower conversion-helper extraction/testing
strategy — testing only the pure functions that can be isolated without
triggering any module-level initialization.

---

## Unresolved Questions

1. **Config module import behavior:** Does `src.core.config` fail gracefully if
   `setting.toml` is missing? To be confirmed during Sprint 006B implementation.
   If it raises on missing file, tests must either provide a minimal config file
   or mock the config module before import.

2. **`retrieve_image_data` side effects:** The function uses `curl_cffi.requests.AsyncSession`
   to fetch images. For text-only tests, this path is not exercised. For image
   tests, this function must be mocked.

3. **`browser_captcha_extension` import:** `routes.py` imports
   `ExtensionCaptchaService` at module level (line 25). Importing this module
   appears safe (no instantiation), but to be confirmed.

4. **TestClient vs. direct invocation:** FastAPI's `TestClient` requires `httpx`
   (already in `requirements.txt`). Direct function invocation is simpler but
   does not test the HTTP layer (headers, status codes, content negotiation).
   The choice depends on Sprint 006B scope.

5. **Async test framework:** Existing tests use `unittest.IsolatedAsyncioTestCase`.
   Route handlers are async. Sprint 006B should follow the same pattern or
   consider `pytest-asyncio` if it does not add dependencies (already available
   via `pytest`).

6. **Module-level `generation_handler` global:** The `routes.generation_handler`
   global is set via `set_generation_handler()`. Tests must set this before
   calling route functions. Thread safety is not a concern for sequential tests,
   but test isolation requires resetting the global in `tearDown`.

---

## Summary

| Seam candidate | Safety | Coverage | Recommended for Sprint 006B |
|----------------|--------|----------|-----------------------------|
| Conversion-layer pure functions | Highest | Low (no HTTP) | Yes — Tier 1 |
| Model resolver (additional tests) | Highest | Low | Yes — if gaps exist |
| Direct route handler + mock | High | Medium | Yes — Tier 2 |
| TestClient + no-op lifespan | Medium-High | High | Defer to Sprint 006C or later |
| Full app import + lifespan mock | Medium | High | Defer — higher risk |
| Real app import + lifespan | Unsafe | Full | Never in offline tests |

The safest path forward is to start with Tier 1 (conversion-layer unit tests)
in Sprint 006B, then expand to Tier 2 (route handler tests with mocked handler)
in the same or a subsequent sprint.
