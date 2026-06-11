# API Endpoint Index

> **Status:** Documentation-only inventory. No runtime behavior has been changed or tested.
> **Sprint:** 002 — API Surface Inventory
> **Source method:** Static source inspection via `grep`/`Read` over `src/**/*.py`.

---

## Legend

| Column | Meaning |
|--------|---------|
| **Method** | HTTP method or WS (WebSocket) |
| **Path** | URL path as declared in route decorator |
| **Source** | Source file and line number |
| **Handler** | Python function name |
| **Category** | Surface category (see below) |
| **Auth** | Authentication requirement |
| **Stream** | Streaming capability: yes / no / conditional |
| **Risk** | Compatibility risk: low / medium / high |

**Category codes:**
- `OpenAI` — OpenAI-compatible API
- `Gemini` — Gemini-compatible API
- `Admin` — Admin panel API
- `Health` — health / metrics / status
- `Static` — static file or admin UI serving
- `Ext/Captcha` — extension / browser / token / captcha related
- `Upload` — upload / media (no dedicated upload endpoint observed; media handled inline)

**Auth codes:**
- `api_key` — verified by `verify_api_key_flexible` (Bearer, `x-goog-api-key`, or `?key=`)
- `admin` — admin session token via `Authorization: Bearer admin-{token}`
- `plugin` — plugin connection token via `Authorization: Bearer {connection_token}`
- `none` — no authentication required

---

## Endpoint Table

### OpenAI-Compatible API

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 1 | GET | `/v1/models` | routes.py:788 | `list_models` | OpenAI | api_key | no | high | Primary model discovery for OpenAI clients |
| 2 | GET | `/v1/models/aliases` | routes.py:804 | `list_model_aliases` | OpenAI | api_key | no | medium | Short-name alias listing; non-standard extension |
| 3 | POST | `/v1/chat/completions` | routes.py:850 | `create_chat_completion` | OpenAI | api_key | conditional | high | Unified generation endpoint; streaming when `stream: true` |

### Gemini-Compatible API

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 4 | GET | `/v1beta/models` | routes.py:822 | `list_gemini_models` | Gemini | api_key | no | high | Gemini model catalog |
| 5 | GET | `/models` | routes.py:823 | `list_gemini_models` | Gemini | api_key | no | high | Same handler as #4 (alias without version prefix) |
| 6 | GET | `/v1beta/models/{model}` | routes.py:835 | `get_gemini_model` | Gemini | api_key | no | medium | Single model resource |
| 7 | GET | `/models/{model}` | routes.py:836 | `get_gemini_model` | Gemini | api_key | no | medium | Same handler as #6 (alias) |
| 8 | POST | `/v1beta/models/{model}:generateContent` | routes.py:892 | `generate_content` | Gemini | api_key | no | high | Non-streaming Gemini generation |
| 9 | POST | `/models/{model}:generateContent` | routes.py:893 | `generate_content` | Gemini | api_key | no | high | Same handler as #8 (alias) |
| 10 | POST | `/v1beta/models/{model}:streamGenerateContent` | routes.py:938 | `stream_generate_content` | Gemini | api_key | yes | high | SSE streaming Gemini generation |
| 11 | POST | `/models/{model}:streamGenerateContent` | routes.py:939 | `stream_generate_content` | Gemini | api_key | yes | high | Same handler as #10 (alias) |

### Extension / Captcha WebSocket

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 12 | WS | `/captcha_ws` | routes.py:975 | `captcha_websocket_endpoint` | Ext/Captcha | api_key | yes | medium | Bidirectional captcha solving via browser extension |

### Health / Metrics

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 13 | GET | `/health` | admin.py:1284 | `health_check` | Health | none | no | low | Public health check |
| 14 | GET | `/metrics` | main.py:251 | `metrics` | Health | none | no | low | Prometheus exposition format |

### Static / Admin UI

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 15 | GET | `/` | main.py:215 | `index` | Static | none | no | low | Serves `static/login.html` |
| 16 | GET | `/login` | main.py:224 | `login_page` | Static | none | no | low | Serves `static/login.html` |
| 17 | GET | `/manage` | main.py:233 | `manage_page` | Static | none | no | low | Serves `static/manage.html` |
| 18 | GET | `/test` | main.py:242 | `test_page` | Static | none | no | low | Serves `static/test.html` |
| 19 | Mount | `/tmp` | main.py:209 | StaticFiles | Static | none | no | low | Serves `tmp/` directory (cached files) |

### Admin API — Auth

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 20 | POST | `/api/admin/login` | admin.py:602 | `admin_login` | Admin | none | no | medium | Returns admin session token; response shape is client-critical |
| 21 | POST | `/api/admin/logout` | admin.py:623 | `admin_logout` | Admin | admin | no | low | Invalidates session token |
| 22 | POST | `/api/admin/change-password` | admin.py:630 | `change_password` | Admin | admin | no | medium | Changes password, invalidates all sessions |
| 23 | POST | `/api/login` | admin.py:1272 | `login` | Admin | none | no | low | Alias for #20 |
| 24 | POST | `/api/logout` | admin.py:1278 | `logout` | Admin | admin | no | low | Alias for #21 |

### Admin API — Token Management

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 25 | GET | `/api/tokens` | admin.py:660 | `get_tokens` | Admin | admin | no | low | All tokens with stats |
| 26 | POST | `/api/tokens` | admin.py:719 | `add_token` | Admin | admin | no | medium | Add token via ST; credential-bearing request |
| 27 | PUT | `/api/tokens/{token_id}` | admin.py:764 | `update_token` | Admin | admin | no | medium | Update token (ST→AT); credential-bearing request |
| 28 | DELETE | `/api/tokens/{token_id}` | admin.py:818 | `delete_token` | Admin | admin | no | low | Delete token |
| 29 | POST | `/api/tokens/{token_id}/enable` | admin.py:833 | `enable_token` | Admin | admin | no | low | Enable token |
| 30 | POST | `/api/tokens/{token_id}/disable` | admin.py:843 | `disable_token` | Admin | admin | no | low | Disable token |
| 31 | POST | `/api/tokens/{token_id}/refresh-credits` | admin.py:853 | `refresh_credits` | Admin | admin | no | low | Refresh credit balance |
| 32 | POST | `/api/tokens/{token_id}/refresh-at` | admin.py:870 | `refresh_at` | Admin | admin | no | low | Manual AT refresh |
| 33 | POST | `/api/tokens/st2at` | admin.py:922 | `st_to_at` | Admin | admin | no | low | ST→AT conversion (no DB write) |
| 34 | POST | `/api/tokens/import` | admin.py:941 | `import_tokens` | Admin | admin | no | medium | Batch credential import |

### Admin API — Proxy Config

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 35 | GET | `/api/config/proxy` | admin.py:1055 | `get_proxy_config` | Admin | admin | no | low | Proxy config (original shape) |
| 36 | GET | `/api/proxy/config` | admin.py:1070 | `get_proxy_config_alias` | Admin | admin | no | low | Proxy config (frontend shape, alias) |
| 37 | POST | `/api/config/proxy` | admin.py:1100 | `update_proxy_config` | Admin | admin | no | medium | Update proxy (original) |
| 38 | POST | `/api/proxy/config` | admin.py:1082 | `update_proxy_config_alias` | Admin | admin | no | medium | Update proxy (frontend shape, alias) |
| 39 | POST | `/api/proxy/test` | admin.py:1118 | `test_proxy_connectivity` | Admin | admin | no | low | Test proxy reachability |

### Admin API — Generation Config

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 40 | GET | `/api/config/generation` | admin.py:1181 | `get_generation_config` | Admin | admin | no | low | Image/video timeout, max_retries |
| 41 | POST | `/api/config/generation` | admin.py:1195 | `update_generation_config` | Admin | admin | no | medium | Update generation config, hot-reloads |
| 42 | GET | `/api/generation/timeout` | admin.py:1438 | `get_generation_timeout` | Admin | admin | no | low | Alias for #40 |
| 43 | POST | `/api/generation/timeout` | admin.py:1444 | `update_generation_timeout` | Admin | admin | no | medium | Alias for #41 |

### Admin API — Call Logic

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 44 | GET | `/api/call-logic/config` | admin.py:1213 | `get_call_logic_config` | Admin | admin | no | low | Token selection mode |
| 45 | POST | `/api/call-logic/config` | admin.py:1229 | `update_call_logic_config` | Admin | admin | no | low | Update call mode |

### Admin API — System / Dashboard / Logs

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 46 | GET | `/api/system/info` | admin.py:1254 | `get_system_info` | Admin | admin | no | low | Token counts, credits, version |
| 47 | GET | `/api/stats` | admin.py:1293 | `get_stats` | Admin | admin | no | low | Dashboard stats |
| 48 | GET | `/api/logs` | admin.py:1299 | `get_logs` | Admin | admin | no | low | Recent request logs |
| 49 | GET | `/api/logs/{log_id}` | admin.py:1332 | `get_log_detail` | Admin | admin | no | low | Log detail with payload |
| 50 | DELETE | `/api/logs` | admin.py:1362 | `clear_logs` | Admin | admin | no | low | Clear all logs |

### Admin API — Admin Config

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 51 | GET | `/api/admin/config` | admin.py:1372 | `get_admin_config` | Admin | admin | no | low | Admin settings |
| 52 | POST | `/api/admin/config` | admin.py:1385 | `update_admin_config` | Admin | admin | no | low | Update error_ban_threshold |
| 53 | POST | `/api/admin/password` | admin.py:1397 | `update_admin_password` | Admin | admin | no | low | Alias for #22 |
| 54 | POST | `/api/admin/apikey` | admin.py:1406 | `update_api_key` | Admin | admin | no | high | Rotate API key; affects all API clients |
| 55 | POST | `/api/admin/debug` | admin.py:1421 | `update_debug_config` | Admin | admin | no | low | Toggle debug (in-memory only) |

### Admin API — Token Refresh

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 56 | GET | `/api/token-refresh/config` | admin.py:1464 | `get_token_refresh_config` | Admin | admin | no | low | AT auto-refresh status |
| 57 | POST | `/api/token-refresh/enabled` | admin.py:1475 | `update_token_refresh_enabled` | Admin | admin | no | low | No-op; always enabled |

### Admin API — Cache Config

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 58 | GET | `/api/cache/config` | admin.py:1495 | `get_cache_config` | Admin | admin | no | low | Cache settings |
| 59 | POST | `/api/cache/enabled` | admin.py:1514 | `update_cache_enabled` | Admin | admin | no | low | Toggle cache |
| 60 | POST | `/api/cache/config` | admin.py:1530 | `update_cache_config_full` | Admin | admin | no | low | Full cache update |
| 61 | POST | `/api/cache/base-url` | admin.py:1557 | `update_cache_base_url` | Admin | admin | no | low | Update cache base URL |

### Admin API — Captcha Config

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 62 | POST | `/api/captcha/config` | admin.py:1573 | `update_captcha_config` | Admin | admin | no | medium | Full captcha config update; affects generation pipeline |
| 63 | GET | `/api/captcha/config` | admin.py:1686 | `get_captcha_config` | Admin | admin | no | low | Read captcha config |
| 64 | POST | `/api/captcha/score-test` | admin.py:1714 | `test_captcha_score` | Admin | admin | no | low | Solve + verify captcha score |

### Admin API — Plugin / Extension Integration

| # | Method | Path | Source | Handler | Category | Auth | Stream | Risk | Notes |
|---|--------|------|--------|---------|----------|------|--------|------|-------|
| 65 | GET | `/api/plugin/config` | admin.py:2053 | `get_plugin_config` | Admin | admin | no | low | Plugin connection settings |
| 66 | POST | `/api/plugin/config` | admin.py:2087 | `update_plugin_config` | Admin | admin | no | low | Update plugin config |
| 67 | POST | `/api/plugin/update-token` | admin.py:2113 | `plugin_update_token` | Ext/Captcha | plugin | no | medium | Receives ST from browser extension |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| OpenAI-compatible API | 3 |
| Gemini-compatible API | 8 |
| Extension / Captcha (WebSocket + plugin token) | 2 |
| Health / Metrics | 2 |
| Static / Admin UI serving | 5 |
| Admin API (auth) | 5 |
| Admin API (token management) | 10 |
| Admin API (proxy config) | 5 |
| Admin API (generation config) | 4 |
| Admin API (call logic) | 2 |
| Admin API (system/dashboard/logs) | 5 |
| Admin API (admin config) | 5 |
| Admin API (token refresh) | 2 |
| Admin API (cache config) | 4 |
| Admin API (captcha config) | 3 |
| Admin API (plugin / extension) | 2 |
| **Total unique endpoints** | **67** |

> **Note on counting:** The 67 unique endpoints are the numbered entries #1–#67.
> Endpoint #67 (`/api/plugin/update-token`) is categorized as Ext/Captcha (it uses
> plugin-auth, not admin-auth) but appears in the "Admin API — Plugin / Extension
> Integration" table section for organizational convenience. The summary rows
> (Ext/Captcha = 2: #12, #67; Admin plugin = 2: #65, #66) sum to 67 with no overlap.

**Highest-risk surfaces:** All OpenAI and Gemini generation endpoints (risk: high) — these are the primary client-facing contracts. Several admin endpoints carry medium compatibility risk (see table).
