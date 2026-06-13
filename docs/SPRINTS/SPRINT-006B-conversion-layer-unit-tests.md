# Sprint 006B — Conversion-Layer Unit Tests

## Goal

Add the first unit tests that import a runtime module, limited to pure
conversion/helper functions in `src/api/routes.py`, after confirming that
importing `src.api.routes` is sufficiently side-effect-free.

---

## Import-Safety Findings

### Import chain

```
src.api.routes
├── curl_cffi.requests.AsyncSession          (class import only)
├── fastapi APIRouter, Depends, HTTPException, etc.  (class/function imports)
├── ..core.auth → AuthManager, verify_api_key_flexible
│   └── ..core.config → Config()             (reads setting_example.toml from disk)
├── ..core.logger → debug_logger             (in-memory logger, no I/O at import)
├── ..core.model_resolver → get_base_model_aliases, resolve_model_name
├── ..core.models → ChatCompletionRequest, ChatMessage, GeminiContent, etc.
├── ..services.generation_handler → MODEL_CONFIG (dict), GenerationHandler (class)
│   ├── ..core.config → config               (same module-level singleton)
│   ├── ..core.monitoring                    (prometheus metrics registration)
│   └── ..services.file_cache                (class import only)
└── ..services.browser_captcha_extension → ExtensionCaptchaService (class)
    └── asyncio.Lock()                       (module-level, harmless)
```

### What is NOT triggered by the import

- `src.main` is **not** imported directly or indirectly.
- No `Database`, `FlowClient`, `TokenManager`, or `GenerationHandler` instances
  are constructed.
- No browser, captcha, session, or proxy services are started.
- No HTTP clients or network connections are created.
- No threads, workers, or background tasks are spawned.
- No lifespan or FastAPI application construction occurs.
- `generation_handler` module-level variable remains `None`.

### Module-level side effects

| Side effect | Risk |
|-------------|------|
| `Config()` reads `config/setting_example.toml` | Low — local file I/O only |
| `MODEL_CONFIG` dict constructed | None — pure data |
| `APIRouter()` created | None — no app binding |
| `asyncio.Lock()` created | None — no event loop required |
| Prometheus metric descriptors registered | None — in-memory only |
| `HTTPBearer()` / `HTTPBearer(auto_error=False)` | None — Pydantic model |

### Conclusion

Importing `src.api.routes` is **safe for the current helper-test seam**.
The import is not completely side-effect-free: `Config()` performs controlled
local reading of `config/setting_example.toml`, and `APIRouter`, `asyncio.Lock`,
`MODEL_CONFIG`, and Prometheus metric descriptors are initialized in memory.
None of these effects start services, perform network I/O, construct application
singletons, or trigger lifespan behavior, so they are acceptable for offline
characterization tests.

---

## Smoke-Check Result

```
$ python3 -c "import src.api.routes; print('src.api.routes import: OK')"
src.api.routes import: OK
```

---

## Functions Tested

| Function | Type | Tests |
|----------|------|-------|
| `_sanitize_media_prompt` | sync | 9 |
| `_build_gemini_error_payload` | sync | 13 |
| `_normalize_finish_reason` | sync | 6 |
| `_extract_url_from_openai_payload` | sync | 12 |
| `_detect_image_mime_type` | sync | 9 |
| `_coerce_gemini_contents` | sync | 8 |
| `_convert_openai_stream_chunk_to_gemini_event` | async | 10 |
| **Total** | | **67** |

---

## Observed Contracts

### `_sanitize_media_prompt(prompt: str) -> str`
- Returns `""` for falsy input (empty string, `None`, whitespace-only).
- Removes `<tools>...</tools>` blocks via regex substitution.
- Strips known preamble patterns (function-calling AI model boilerplate).
- Collapses 3+ consecutive newlines to 2.
- Strips leading/trailing whitespace from input and output.

### `_build_gemini_error_payload(status_code: int, message: str) -> dict`
- Returns `{"error": {"code": ..., "message": ..., "status": ...}}`.
- `status` is derived from `GEMINI_STATUS_MAP`; unknown codes map to `"UNKNOWN"`.
- Exactly three keys in the `error` dict: `code`, `message`, `status`.

### `_normalize_finish_reason(reason: Optional[str]) -> Optional[str]`
- `"stop"` → `"STOP"`, `"length"` → `"MAX_TOKENS"`, `"content_filter"` → `"SAFETY"`.
- Unknown non-None values → `"STOP"` (default fallback).
- `None` → `None`.

### `_extract_url_from_openai_payload(payload: dict) -> Optional[str]`
- Direct `payload["url"]` (non-blank string) is preferred.
- Falls through to markdown image regex in `choices[0].message.content`.
- Falls through to HTML video regex if no markdown image found.
- Returns `None` for empty/missing/malformed payloads.

### `_detect_image_mime_type(image_bytes: bytes, fallback: str = "image/png") -> str`
- Recognizes JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), GIF (`GIF87a`/`GIF89a`),
  WebP (`RIFF....WEBP`).
- Returns fallback for unknown, empty, or insufficient bytes.

### `_coerce_gemini_contents(raw_contents: Optional[List[Any]]) -> List[GeminiContent]`
- Returns `[]` for `None` or empty list.
- Passes through existing `GeminiContent` instances by identity.
- Validates dicts via `GeminiContent.model_validate()`.
- Preserves role (including `None`) and parts structure.

### `_convert_openai_stream_chunk_to_gemini_event(payload: dict, response_model: str) -> Optional[str]`
- Returns `None` for empty/missing choices.
- Returns `None` for chunks with only `index` (no text, no finish_reason).
- `reasoning_content` is preferred over `content` via `or` chain.
- `finish_reason` is mapped through `_normalize_finish_reason`.
- Emits `"data: {json}\n\n"` SSE format.
- Output includes `candidates` and `modelVersion` top-level keys.
- Never emits `[DONE]` sentinel.

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

# New helper tests
$ python3 -m unittest tests.compatibility.test_route_conversion_helpers -v
Ran 67 tests in 0.005s
OK

# Combined compatibility suite
$ python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
Ran 120 tests in 0.011s
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
| `tests/compatibility/test_route_conversion_helpers.py` | 67 unit tests for 7 pure conversion helpers |

### Unchanged

- No files under `src/` were modified.
- No dependencies were added.

---

## Runtime Source Confirmation

- **No runtime source files were changed.** `git diff -- src` produces no output.
- **No upstream calls occurred.** All tests are offline and deterministic.
- **No credentials, database, browser, captcha, token, proxy, or session activity occurred.**

---

## Limitations

1. **Async testing uses `asyncio.run()`.** Each async test creates and tears down
   an event loop. This is acceptable for stdlib-only tests but may need adjustment
   if a future sprint adopts `pytest-asyncio`.

2. **`_convert_openai_stream_chunk_to_gemini_event` with image content is not tested.**
   The function calls `_build_gemini_parts_from_output` which calls
   `_build_image_parts_from_uri` (an async function that performs network I/O
   for non-data-URL images). Testing image-bearing chunks would require mocking
   the image download path, which is out of scope for this sprint.

3. **Coverage is helper-level only.** This sprint does not test complete route
   handlers, streaming transport, request normalization, or HTTP behavior.

4. **Config file dependency.** Importing `src.api.routes` reads
   `config/setting_example.toml` via the `Config` class. If this file is missing
   or unreadable, the import will fail. The import test verifies the current
   environment works.

---

## Status

**COMPLETED**
