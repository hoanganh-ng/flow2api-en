# API Surface Inventory

> **Status:** Documentation-only inventory. No runtime behavior has been changed or tested.
> **Sprint:** 002 — API Surface Inventory
> **Last updated:** 2025 (Sprint 002)

---

## Purpose

This document catalogs every HTTP and WebSocket endpoint declared in the flow2api-en
codebase as observed in source. It is intended as a pre-refactor baseline so that any
future contract extraction, compatibility test harness, or rewrite can verify that
observable behavior is preserved.

All observations are based on static source inspection. Behavior that depends on
runtime configuration, database state, or upstream service availability is noted only
at the boundary level and marked "to be confirmed."

---

## Source Files Inspected

| File | Role |
|------|------|
| `src/main.py` | FastAPI app creation, CORS middleware, lifespan, router mounting, static file serving, HTML page routes, `/metrics` |
| `src/api/routes.py` | `APIRouter` for OpenAI-compatible and Gemini-compatible generation endpoints, plus WebSocket captcha endpoint |
| `src/api/admin.py` | `APIRouter` for admin panel endpoints (auth, token management, config, logs, plugin, captcha) |
| `src/core/auth.py` | `AuthManager`, `verify_api_key_flexible`, `verify_api_key_header` |
| `src/core/models.py` | Pydantic request/response models |
| `src/services/generation_handler.py` | `MODEL_CONFIG` catalog, `GenerationHandler` entry |
| `src/core/monitoring.py` | Prometheus metrics helpers, `build_public_health_snapshot` |

---

## App / Router Mounting Overview

Observed in `src/main.py` (lines 186–209):

```
app = FastAPI(title="Flow2API", version="1.0.0", lifespan=lifespan)
app.include_router(routes.router)   # OpenAI + Gemini generation routes
app.include_router(admin.router)    # Admin panel routes
app.mount("/tmp", StaticFiles(directory=tmp_dir), name="tmp")
```

CORS middleware appears to allow all origins, credentials, methods, and headers
(`src/main.py` lines 194–200; observed in source).

Dependency injection is performed at module level:
- `routes.set_generation_handler(generation_handler)` — routes.py line 85
- `admin.set_dependencies(token_manager, proxy_manager, db, concurrency_manager)` — admin.py line 469

---

## OpenAI-Compatible Routes

Source: `src/api/routes.py`

### GET /v1/models

- **Handler:** `list_models` (line 788)
- **Auth:** `verify_api_key_flexible` (Bearer token, `x-goog-api-key` header, or `key` query param)
- **Response shape:** `{ "object": "list", "data": [ { "id", "object": "model", "owned_by": "flow2api", "description" } ] }`
- **Notes:** Returns the keys of `MODEL_CONFIG` from `generation_handler.py`. This is the endpoint OpenAI-compatible clients call to discover available models.

### GET /v1/models/aliases

- **Handler:** `list_model_aliases` (line 804)
- **Auth:** `verify_api_key_flexible`
- **Response shape:** Same list shape as `/v1/models` but with `is_alias: true` on each entry.
- **Notes:** Exposes short aliases (e.g., model family names) that can be resolved via `generationConfig`-based model resolution. Observed in source; appears to be a convenience for clients that use short model names.

### POST /v1/chat/completions

- **Handler:** `create_chat_completion` (line 850)
- **Auth:** `verify_api_key_flexible`
- **Request model:** `ChatCompletionRequest` (`src/core/models.py` line 285)
  - Fields: `model` (required), `messages`, `stream`, `temperature`, `max_tokens`, `image` (deprecated), `video` (deprecated), `generationConfig`, `contents` (Gemini extension)
  - Extra fields are allowed (`ConfigDict(extra="allow")`)
- **Streaming:** Yes — when `stream: true`, returns `StreamingResponse` with `media_type="text/event-stream"`. Headers include `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
- **Non-streaming:** Returns `JSONResponse`. Status code is taken from any embedded `error.status_code` field in the handler result.
- **Notes:**
  - Accepts both OpenAI `messages` format and Gemini `contents` format (extension).
  - When `contents` is provided in a chat completion request, the request is normalized as a Gemini request internally.
  - The `extend://MEDIA_ID` scheme in image URLs is observed for video continuation workflows.
  - Reference images from earlier conversation turns may be fetched and prepended (observed in `_append_openai_reference_images`).

---

## Gemini-Compatible Routes

Source: `src/api/routes.py`

### GET /v1beta/models and GET /models

- **Handlers:** `list_gemini_models` (lines 822–823)
- **Auth:** `verify_api_key_flexible`
- **Response shape:** `{ "models": [ { "name": "models/{id}", "displayName", "description", "version": "flow2api", "inputTokenLimit": 0, "outputTokenLimit": 0, "supportedGenerationMethods": ["generateContent", "streamGenerateContent"] } ] }`
- **Notes:** Combines base model aliases (from `model_resolver.py`) with `MODEL_CONFIG` entries. The `/models` path (without `/v1beta/` prefix) is also accepted.

### GET /v1beta/models/{model} and GET /models/{model}

- **Handler:** `get_gemini_model` (lines 835–836)
- **Auth:** `verify_api_key_flexible`
- **Response shape:** Single Gemini model resource (see above).
- **Error response:** 404 with Gemini error envelope `{ "error": { "code": 404, "message": ..., "status": "NOT_FOUND" } }`

### POST /v1beta/models/{model}:generateContent and POST /models/{model}:generateContent

- **Handler:** `generate_content` (lines 892–893)
- **Auth:** `verify_api_key_flexible`
- **Request model:** `GeminiGenerateContentRequest` (`src/core/models.py` line 275)
  - Fields: `contents` (required, list of `GeminiContent`), `generationConfig`, `systemInstruction`
- **Response shape:** Gemini success envelope `{ "candidates": [ { "content": { "role": "model", "parts": [...] }, "finishReason": "STOP", "index": 0 } ], "modelVersion": "..." }`
- **Streaming:** No
- **Error response:** Gemini error envelope with status mapped via `GEMINI_STATUS_MAP` (line 57).
- **Notes:**
  - Output is enriched with a direct `url` field when an image/video URL is detected in the response.
  - Media prompts are sanitized to strip agent/tool scaffolding.
  - `systemInstruction` for media models may be ignored if it appears to be boilerplate tool-calling scaffolding.

### POST /v1beta/models/{model}:streamGenerateContent and POST /models/{model}:streamGenerateContent

- **Handler:** `stream_generate_content` (lines 938–939)
- **Auth:** `verify_api_key_flexible`
- **Request model:** `GeminiGenerateContentRequest`
- **Query param:** `alt` (optional, observed but not actively used in handler body)
- **Streaming:** Yes — `StreamingResponse` with `media_type="text/event-stream"`. Same SSE headers as OpenAI streaming.
- **SSE format:** `data: {json}\n\n` — each chunk is a Gemini-shaped candidates delta. Errors are emitted inline as Gemini error payloads.
- **Notes:** Converts internal OpenAI-shaped stream chunks to Gemini format via `_convert_openai_stream_chunk_to_gemini_event`.

---

## Admin Routes

Source: `src/api/admin.py`

All admin routes (except `/health`, `/api/login`, `/api/logout`, `/api/plugin/update-token`)
require a Bearer admin session token in the `Authorization` header. The token is
validated against an in-memory `active_admin_tokens` set (admin.py line 38).

### Authentication Endpoints

| Method | Path | Handler | Auth | Notes |
|--------|------|---------|------|-------|
| POST | `/api/admin/login` | `admin_login` (line 602) | None | Accepts `{ username, password }`, returns `{ success, token, username }`. Token is prefixed `admin-`. |
| POST | `/api/admin/logout` | `admin_logout` (line 623) | Admin token | Invalidates session token |
| POST | `/api/admin/change-password` | `change_password` (line 630) | Admin token | Changes password, clears all sessions |
| POST | `/api/login` | `login` (line 1272) | None | Alias for `/api/admin/login` |
| POST | `/api/logout` | `logout` (line 1278) | Admin token | Alias for `/api/admin/logout` |

### Token Management Endpoints

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/tokens` | `get_tokens` | 660 | Returns array of all tokens with stats |
| POST | `/api/tokens` | `add_token` | 719 | Add new token via ST |
| PUT | `/api/tokens/{token_id}` | `update_token` | 764 | Update token (ST→AT conversion) |
| DELETE | `/api/tokens/{token_id}` | `delete_token` | 818 | Delete token |
| POST | `/api/tokens/{token_id}/enable` | `enable_token` | 833 | Enable token |
| POST | `/api/tokens/{token_id}/disable` | `disable_token` | 843 | Disable token |
| POST | `/api/tokens/{token_id}/refresh-credits` | `refresh_credits` | 853 | Refresh credit balance |
| POST | `/api/tokens/{token_id}/refresh-at` | `refresh_at` | 870 | Manual AT refresh (ST conversion) |
| POST | `/api/tokens/st2at` | `st_to_at` | 922 | Convert ST→AT without DB write |
| POST | `/api/tokens/import` | `import_tokens` | 941 | Batch import tokens |

### Proxy Configuration Endpoints

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/config/proxy` | `get_proxy_config` | 1055 | Returns proxy config (original shape) |
| GET | `/api/proxy/config` | `get_proxy_config_alias` | 1070 | Returns proxy config (frontend-compatible shape) |
| POST | `/api/config/proxy` | `update_proxy_config` | 1100 | Update proxy config (original) |
| POST | `/api/proxy/config` | `update_proxy_config_alias` | 1082 | Update proxy config (frontend-compatible) |
| POST | `/api/proxy/test` | `test_proxy_connectivity` | 1118 | Test proxy against target URL |

### Generation Configuration Endpoints

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/config/generation` | `get_generation_config` | 1181 | Returns image/video timeout and max_retries |
| POST | `/api/config/generation` | `update_generation_config` | 1195 | Update generation config, hot-reloads |
| GET | `/api/generation/timeout` | `get_generation_timeout` | 1438 | Alias — delegates to `get_generation_config` |
| POST | `/api/generation/timeout` | `update_generation_timeout` | 1444 | Alias — same logic as `update_generation_config` |

### Call Logic / Token Selection

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/call-logic/config` | `get_call_logic_config` | 1213 | Returns call_mode ("default" or "polling") |
| POST | `/api/call-logic/config` | `update_call_logic_config` | 1229 | Updates call mode, hot-reloads |

### System / Dashboard

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/system/info` | `get_system_info` | 1254 | Token counts, credits, version |
| GET | `/api/stats` | `get_stats` | 1293 | Dashboard stats |

### Logs

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/logs` | `get_logs` | 1299 | List recent request logs (max 100) |
| GET | `/api/logs/{log_id}` | `get_log_detail` | 1332 | Single log detail with payload |
| DELETE | `/api/logs` | `clear_logs` | 1362 | Clear all logs |

### Admin Config

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/admin/config` | `get_admin_config` | 1372 | Returns admin username, api_key, error_ban_threshold, debug_enabled |
| POST | `/api/admin/config` | `update_admin_config` | 1385 | Updates error_ban_threshold |
| POST | `/api/admin/password` | `update_admin_password` | 1397 | Alias for change_password |
| POST | `/api/admin/apikey` | `update_api_key` | 1406 | Update API key (for external API calls) |
| POST | `/api/admin/debug` | `update_debug_config` | 1421 | Toggle debug mode (in-memory only) |

### AT Auto-Refresh

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/token-refresh/config` | `get_token_refresh_config` | 1464 | Returns AT auto-refresh status (always enabled) |
| POST | `/api/token-refresh/enabled` | `update_token_refresh_enabled` | 1475 | No-op; AT refresh is always enabled |

### Cache Configuration

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/cache/config` | `get_cache_config` | 1495 | Cache enabled, timeout, base_url |
| POST | `/api/cache/enabled` | `update_cache_enabled` | 1514 | Toggle cache, hot-reloads |
| POST | `/api/cache/config` | `update_cache_config_full` | 1530 | Full cache config update |
| POST | `/api/cache/base-url` | `update_cache_base_url` | 1557 | Update cache base URL only |

### Captcha Configuration

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| POST | `/api/captcha/config` | `update_captcha_config` | 1573 | Full captcha config update (method, API keys, browser settings) |
| GET | `/api/captcha/config` | `get_captcha_config` | 1686 | Returns full captcha config |
| POST | `/api/captcha/score-test` | `test_captcha_score` | 1714 | Solve captcha and verify score against antcpt.com |

### Plugin / Extension Integration

| Method | Path | Handler | Line | Notes |
|--------|------|---------|------|-------|
| GET | `/api/plugin/config` | `get_plugin_config` | 2053 | Returns plugin connection token and URL |
| POST | `/api/plugin/config` | `update_plugin_config` | 2087 | Update plugin connection settings |
| POST | `/api/plugin/update-token` | `plugin_update_token` | 2113 | Receives ST from Chrome extension; uses `connection_token` (not admin auth) |

---

## Health / Metrics / Status Routes

### GET /health

- **Source:** `src/api/admin.py` line 1284
- **Handler:** `health_check`
- **Auth:** None (public)
- **Response:** Calls `build_public_health_snapshot(db)`. Fallback: `{ backend_running: true, has_active_tokens: false }`.

### GET /metrics

- **Source:** `src/main.py` line 251
- **Handler:** `metrics`
- **Auth:** None (public)
- **Response:** Prometheus exposition format (`CONTENT_TYPE_LATEST`). If `prometheus_client` is not installed, returns a stub comment line.
- **Notes:** Exposes request counters, latencies, token counts, concurrency state.

---

## Static / Admin UI Routes

Source: `src/main.py`

| Method | Path | Handler | Line | Serves |
|--------|------|---------|------|--------|
| GET | `/` | `index` | 215 | `static/login.html` |
| GET | `/login` | `login_page` | 224 | `static/login.html` |
| GET | `/manage` | `manage_page` | 233 | `static/manage.html` |
| GET | `/test` | `test_page` | 242 | `static/test.html` |
| Mount | `/tmp` | StaticFiles | 209 | `tmp/` directory (cached generation output) |

All HTML routes return `FileResponse` or 404 `HTMLResponse` fallback.

---

## Extension / Browser / Token / Captcha / Session-Related Routes

### WebSocket /captcha_ws

- **Source:** `src/api/routes.py` line 975
- **Handler:** `captcha_websocket_endpoint`
- **Auth:** API key via query param (`key` or `api_key`), `x-goog-api-key` header, or `Authorization: Bearer` header. Connection is closed with code 1008 if auth fails.
- **Purpose:** Extension-based captcha solving. Connects to `ExtensionCaptchaService` for bidirectional message handling.
- **Notes:** This is the only WebSocket endpoint observed. The service is used when `captcha_method` is configured for extension-based solving.

### POST /api/plugin/update-token

- **Source:** `src/api/admin.py` line 2113
- **Auth:** `connection_token` via `Authorization: Bearer` header (NOT admin token, NOT API key). The connection token is a shared secret configured in the plugin settings.
- **Purpose:** Receives a `session_token` from the browser extension. Converts ST→AT, then upserts the token record (matched by email).

---

## Auth / Security Observations

1. **API key authentication** (`verify_api_key_flexible` in `src/core/auth.py` line 44):
   - Accepts key from `Authorization: Bearer {key}`, `x-goog-api-key` header, or `?key=` query param.
   - Key is compared against `config.api_key` (single shared secret, not per-user).
   - Used by all `/v1/*`, `/v1beta/*`, and `/models*` endpoints.

2. **Admin session token authentication** (`verify_admin_token` in `src/api/admin.py` line 586):
   - Expects `Authorization: Bearer admin-{token}` header.
   - Token is validated against in-memory `active_admin_tokens` set.
   - Tokens are issued by `/api/admin/login` and invalidated by logout or password change.
   - No expiration mechanism observed in source (tokens live until logout or server restart).

3. **Plugin connection token** (`/api/plugin/update-token`):
   - Separate auth mechanism using `connection_token` stored in plugin config.
   - Verified via `Authorization: Bearer {connection_token}`.

4. **WebSocket auth** (`/captcha_ws`):
   - API key verified via multiple channels (query, header, bearer).

5. **CORS:** Appears fully open (`allow_origins=["*"]`, all methods, all headers; observed in source).

---

## Streaming Observations

1. **OpenAI SSE streaming** (`/v1/chat/completions` with `stream: true`):
   - Media type: `text/event-stream`
   - Headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
   - Final chunk: `data: [DONE]\n\n`
   - Chunks are `data: {json}\n\n` where JSON follows OpenAI chat completion delta format.

2. **Gemini SSE streaming** (`/v1beta/models/{model}:streamGenerateContent`):
   - Same media type and headers.
   - Chunks are Gemini-shaped `{ candidates: [{ content, finishReason }], modelVersion }`.
   - No `[DONE]` terminator observed for Gemini stream (the generator simply ends).
   - Errors mid-stream are emitted as Gemini error payloads in SSE data frames.

3. **Internal conversion:** The generation handler produces OpenAI-shaped chunks; Gemini stream output converts each chunk via `_convert_openai_stream_chunk_to_gemini_event`.

---

## Error Response Observations

1. **OpenAI endpoints:** Errors are returned as `JSONResponse` with status code from the handler result's `error.status_code` field, or 500 for unhandled exceptions. No standard OpenAI error envelope wrapping was observed — the handler result is returned directly.

2. **Gemini endpoints:** Errors use the Gemini error envelope:
   ```
   { "error": { "code": <int>, "message": "<str>", "status": "<GEMINI_STATUS_MAP>" } }
   ```
   Status code mapping is defined in `GEMINI_STATUS_MAP` (routes.py line 57).

3. **Admin endpoints:** Use FastAPI's `HTTPException` which returns `{ "detail": "..." }`. Some handlers return `{ "success": false, "message": "..." }` without raising exceptions (inconsistent envelope).

---

## Unknowns for Later Contract Extraction

1. **Exact request/response schemas** for `ChatCompletionRequest` with extra fields — the model allows arbitrary extra fields (`ConfigDict(extra="allow")`). Which extra fields are actually used by clients is unknown.

2. **Model resolution logic** (`src/core/model_resolver.py`) — the mapping from aliases and `generationConfig` parameters to concrete model names requires deeper inspection.

3. **Generation handler output format** — `handle_generation()` yields string chunks; the exact JSON structure depends on `FlowClient` and upstream service responses.

4. **Token ST/AT lifecycle** — the exact upstream API contracts for session-token to access-token conversion are external to this codebase.

5. **Captcha service contracts** — browser, personal, remote_browser, and third-party API captcha methods each have distinct integration surfaces not fully captured here.

6. **WebSocket message protocol** — the exact message schema for `/captcha_ws` is defined in `ExtensionCaptchaService` and requires separate extraction.

7. **Prometheus metric names and labels** — defined in `src/core/monitoring.py` but not enumerated in this inventory.

8. **File cache behavior** — `/tmp` mount serves cached files; the naming convention and TTL logic are in `src/services/file_cache.py`.

9. **Duplicate/aliased endpoints** — several admin endpoints have paired aliases (e.g., `/api/config/proxy` and `/api/proxy/config`). Whether both are actively used by the frontend or only one is the canonical path is to be confirmed.

10. **The `alt` query parameter** on `streamGenerateContent` — accepted but not observed to change behavior. May be intended for `alt=sse` compatibility with official Gemini API.
