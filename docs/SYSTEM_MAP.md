# System Map — flow2api-en

> **Sprint 001 deliverable.** Documentation-only. Based on source inspection of the current repository. No runtime behavior has been changed.

## 1. Top-Level Repository Layout

```
flow2api-en/
├── main.py                    # Uvicorn CLI entrypoint (13 lines)
├── requirements.txt           # Python dependencies (14 lines)
├── Dockerfile                 # Headless container image (14 lines)
├── Dockerfile.headed          # Headed browser container image
├── docker-compose.yml         # Default compose (headless)
├── docker-compose.headed.yml  # Compose for headed browser mode
├── docker-compose.local.yml   # Local development compose
├── docker-compose.proxy.yml   # Proxy-side compose
├── docker/
│   └── entrypoint.headed.sh   # Xvfb + Fluxbox startup, then python main.py
├── config/
│   └── setting_example.toml   # Example TOML configuration (72 lines)
├── extension/                 # Chrome Extension (Manifest V3) for captcha
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── options.html
│   └── options.js
├── src/
│   ├── main.py                # FastAPI app creation + lifespan (256 lines)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # OpenAI + Gemini API routes (1003 lines)
│   │   └── admin.py           # Admin management API (2207 lines)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # TOML-based config singleton (648 lines)
│   │   ├── auth.py            # API key + admin auth (63 lines)
│   │   ├── database.py        # SQLite persistence layer (1950 lines)
│   │   ├── models.py          # Pydantic data models (301 lines)
│   │   ├── model_resolver.py  # Model name alias resolution (634 lines)
│   │   ├── account_tiers.py   # Paygate tier helpers (58 lines)
│   │   ├── monitoring.py      # Prometheus metrics (560 lines)
│   │   └── logger.py          # Debug file logger (283 lines)
│   └── services/
│       ├── __init__.py
│       ├── flow_client.py              # Upstream API client (3123 lines)
│       ├── token_manager.py            # Token lifecycle + AT refresh (780 lines)
│       ├── generation_handler.py       # Generation orchestration (2467 lines)
│       ├── load_balancer.py            # Token selection strategy (356 lines)
│       ├── concurrency_manager.py      # Per-token rate limiting (303 lines)
│       ├── proxy_manager.py            # Proxy config + normalization (151 lines)
│       ├── file_cache.py              # Media download cache (515 lines)
│       ├── browser_captcha.py          # Playwright headed captcha (2122 lines)
│       ├── browser_captcha_personal.py # nodriver personal captcha (13309 lines)
│       ├── browser_captcha_extension.py# Extension WebSocket captcha (215 lines)
│       └── browser_cookie_utils.py     # Cookie parsing helpers (316 lines)
├── static/
│   ├── login.html             # Admin login page
│   ├── manage.html            # Admin management console
│   └── test.html              # Model testing page
├── tests/                     # Unit tests (6 files)
└── docs/                      # Documentation (this fork's additive layer)
```

**Total Python lines:** ~32,628 (observed via `wc -l`).

## 2. Major Runtime Modules

### 2.1 Application Bootstrap (`src/main.py`)

Observed in source (lines 1–256):
- Creates the FastAPI `app` with a `lifespan` async context manager.
- Instantiates all core singletons at module level: `Database`, `ProxyManager`, `FlowClient`, `TokenManager`, `ConcurrencyManager`, `LoadBalancer`, `GenerationHandler`.
- Injects dependencies into `routes` and `admin` modules via setter functions.
- Registers two routers (`routes.router`, `admin.router`).
- Mounts `/tmp` as static files for cached media.
- Serves HTML pages at `/`, `/login`, `/manage`, `/test`.
- Exposes `/metrics` (Prometheus).

### 2.2 API Routes (`src/api/routes.py`, 1003 lines)

Observed in source:
- OpenAI-compatible endpoint: `POST /v1/chat/completions`
- Gemini-compatible endpoints: `POST /v1beta/models/{model}:generateContent`, `POST /v1beta/models/{model}:streamGenerateContent` (also at `/models/...`)
- Model listing: `GET /v1/models`, `GET /v1/models/aliases`, `GET /v1beta/models`, `GET /models/{model}`
- WebSocket captcha: `WS /captcha_ws`
- Supports both streaming (SSE) and non-streaming responses.
- Normalizes incoming requests from OpenAI or Gemini format into a shared `NormalizedGenerationRequest`.
- Handles image data URL decoding, remote image fetching, reference image extraction from chat history.

### 2.3 Admin API (`src/api/admin.py`, 2207 lines)

Observed in source:
- Full CRUD for tokens, projects, proxy config, captcha config, cache config, debug config, generation config, call logic config, plugin config.
- Admin login/session management (in-memory token set).
- Token operations: add, update, delete, enable, disable, refresh credits, manual ban/unban.
- Configuration read/write endpoints for all runtime settings.
- Dashboard statistics and health endpoint.
- Remote browser health probing.
- This is the largest API surface and second-largest file in the project.

### 2.4 Configuration (`src/core/config.py`, 648 lines)

Observed in source:
- Singleton `Config` class loaded from `config/setting.toml` (falls back to `setting_example.toml`).
- TOML-based, no environment variable loading observed.
- Sections: `[global]`, `[flow]`, `[server]`, `[debug]`, `[proxy]`, `[generation]`, `[call_logic]`, `[admin]`, `[cache]`, `[captcha]`.
- Many mutable properties with runtime setters (admin can change settings without restart).
- Supports multiple captcha providers: yescaptcha, capmonster, ezcaptcha, capsolver, browser, personal, remote_browser, extension.

### 2.5 Database (`src/core/database.py`, 1950 lines)

Observed in source:
- SQLite via `aiosqlite`, stored at `data/flow.db`.
- Write-serialized via `asyncio.Lock`.
- Tables observed: `tokens`, `projects`, `token_stats`, `tasks`, `request_logs`, `admin_config`, `proxy_config`, `generation_config`, `cache_config`, `captcha_config`, `debug_config`, `plugin_config`, `call_logic_config`.
- First-startup initialization from TOML config.
- Migration support via `check_and_migrate_db` (adds missing tables/columns).
- In-memory config reload via `reload_config_to_memory`.

### 2.6 Authentication (`src/core/auth.py`, 63 lines)

Observed in source:
- API key verification: simple string comparison against `config.api_key`.
- Admin auth: username/password comparison (observed in source: `auth.py` lines 21–24; credentials appear stored without hashing in config and DB — to be confirmed during contract extraction; `bcrypt` is imported and available).
- Flexible API key extraction: `Authorization: Bearer`, `x-goog-api-key` header, or `?key=` query param.

### 2.7 Model Registry (`src/services/generation_handler.py` + `src/core/model_resolver.py`)

Observed in source:
- `MODEL_CONFIG` dict in `generation_handler.py` maps internal model keys to upstream model names, aspect ratios, and optional upsample settings.
- Image models: Gemini 3.0 Pro (GEM_PIX_2), Gemini 3.1 Flash (NARWHAL), Imagen 4.0 (IMAGEN_3_5), Veo Lite image variants.
- Video models: Veo 3.1 variants (T2V, I2V, R2V, Extend, Interpolation) with fast/standard/ultra/lite tiers, multiple durations (4s/6s), and resolution options (4K/1080p).
- `model_resolver.py` provides alias resolution from simplified names + `generationConfig` params to internal keys.
- Supports OpenAI-style `size` and `quality` parameter mapping.

### 2.8 Token Management (`src/services/token_manager.py`, 780 lines)

Observed in source:
- Token CRUD operations.
- AT (Access Token) auto-refresh from ST (Session Token).
- ST refresh via browser captcha service (personal mode only).
- Project pool management: creates and rotates projects per token in round-robin order.
- 429 rate-limit auto-ban (disables token) and auto-unban (after 12 hours, hourly check).
- Consecutive error auto-disable (threshold from admin config).
- Credits and paygate tier refresh.

### 2.9 Flow Client (`src/services/flow_client.py`, 3123 lines)

Observed in source:
- **Largest file in the project.**
- HTTP client for upstream Google Labs / AI Sandbox APIs.
- ST-to-AT conversion, credits querying.
- Image generation: single-shot HTTP requests with polling for results.
- Video generation: scene creation, operation polling, result retrieval.
- Captcha token acquisition: delegates to configured captcha service.
- Browser fingerprint management (per-account User-Agent caching, context-var-based request fingerprinting).
- Remote browser prefill support.
- Uses `curl_cffi` with browser impersonation (`chrome120`).
- Multiple retry and timeout strategies for image vs. video.
- Proxy-aware (request proxy + media proxy fallback).

### 2.10 Generation Handler (`src/services/generation_handler.py`, 2467 lines)

Observed in source:
- Orchestrates the full generation lifecycle.
- Selects token via load balancer, ensures valid AT, acquires concurrency slots.
- Routes to image or video generation based on model config.
- Handles caching (file cache for videos/images).
- Builds OpenAI-compatible JSON/SSE responses.
- Records usage, errors, and success metrics.
- Supports soft/hard concurrency limits with wait-queue behavior.
- Pre-launch staggering for burst smoothing.

### 2.11 Load Balancer (`src/services/load_balancer.py`, 356 lines)

Observed in source:
- Two selection modes: "default" (load-aware sort) and "polling" (round-robin).
- Filters tokens by: active status, image/video capability, account tier, concurrency availability, extension route connectivity.
- Prefers tokens that don't need AT refresh; defers refresh-needing tokens.
- Optional slot pre-reservation and pending tracking for burst smoothing.

### 2.12 Concurrency Manager (`src/services/concurrency_manager.py`, 303 lines)

Observed in source:
- Per-token image/video in-flight counters.
- Configurable per-token concurrency limits (-1 = unlimited).
- Wait-acquire pattern with configurable timeout for hard slot contention.

### 2.13 Browser Captcha Services

Three distinct implementations observed:

| Service | File | Lines | Engine | Description |
|---------|------|-------|--------|-------------|
| `browser_captcha.py` | `src/services/browser_captcha.py` | 2122 | Playwright | Headed browser with slot-based captcha solving |
| `browser_captcha_personal.py` | `src/services/browser_captcha_personal.py` | 13309 | nodriver | **Largest file.** Resident tab pool, ST refresh, cookie management |
| `browser_captcha_extension.py` | `src/services/browser_captcha_extension.py` | 215 | WebSocket | Chrome extension bridge for external captcha solving |

`browser_captcha_personal.py` is by far the largest and most complex file. It appears to manage:
- A shared pool of resident browser tabs across all tokens/projects.
- reCAPTCHA token generation via real browser automation.
- Session Token (ST) refresh through browser cookie extraction.
- Browser profile lifecycle (fresh restart after N solves).
- Tab idle TTL and cleanup.

### 2.14 File Cache (`src/services/file_cache.py`, 515 lines)

Observed in source:
- Downloads and caches media files (images/videos) to `tmp/` directory.
- MD5-based cache filenames with extension guessing.
- Three download methods: curl_cffi, wget, curl (fallback chain).
- Background cleanup task with configurable interval.
- Proxy-aware downloads (media proxy preferred for media).

### 2.15 Monitoring (`src/core/monitoring.py`, 560 lines)

Observed in source:
- Prometheus metrics via `prometheus_client` (graceful fallback if not installed).
- Metrics: generation requests, durations, token states (active/inactive/expired/banned), credits, in-flight counts, dashboard stats, remote browser health.
- Per-token labeled gauges for detailed observability.
- Public health snapshot builder for admin dashboard.

## 3. Largest / Highest-Coupling Files

| File | Lines | Coupling Notes |
|------|-------|----------------|
| `browser_captcha_personal.py` | 13309 | Depends on config, logger, cookie_utils; used by token_manager, main lifespan |
| `flow_client.py` | 3123 | Depends on config, logger, proxy_manager, database, captcha services |
| `generation_handler.py` | 2467 | Depends on flow_client, token_manager, load_balancer, database, concurrency_manager, proxy_manager, file_cache, monitoring |
| `admin.py` | 2207 | Depends on all core + services for admin CRUD |
| `database.py` | 1950 | Core persistence; used by every service |
| `browser_captcha.py` | 2122 | Depends on config, logger; parallel implementation to personal |

## 4. Important Runtime Flows (High Level)

### 4.1 Application Startup

1. `main.py` → uvicorn starts `src.main:app`.
2. Lifespan startup: DB init/migration → config reload to memory → token snapshot → browser captcha init (if configured) → concurrency manager init → remote browser prefill → start background tasks (auto-unban, cache cleanup).

### 4.2 Generation Request (OpenAI)

1. `POST /v1/chat/completions` → `routes.py`.
2. Auth check (`verify_api_key_flexible`).
3. Request normalization: extract prompt + images from messages, resolve model name.
4. If streaming: return `StreamingResponse` → `_iterate_openai_stream` → `generation_handler.handle_generation`.
5. If non-streaming: collect result → return JSON.

### 4.3 Generation Request (Gemini)

1. `POST /v1beta/models/{model}:generateContent` → `routes.py`.
2. Auth check, normalize Gemini contents → extract prompt + images.
3. Sanitize media prompts (strip tool/agent scaffolding).
4. Delegate to `generation_handler.handle_generation`.
5. Convert response to Gemini format (candidates/parts structure).

### 4.4 Token Selection

1. `LoadBalancer.select_token` filters active tokens by capability, tier, concurrency, extension route.
2. Sorts by load (inflight, remaining slots, refresh needs).
3. Ensures AT validity (triggers refresh if needed).
4. Optionally reserves concurrency slot.

### 4.5 Upstream Generation (Image)

1. `flow_client` acquires captcha token → builds request → sends to upstream API.
2. Polls for result (configurable interval/attempts).
3. Downloads result media → caches locally → returns URL.

### 4.6 Upstream Generation (Video)

1. `flow_client` acquires captcha token → creates scene → polls operation.
2. Downloads result video → caches locally → returns URL.

### 4.7 Token Refresh

1. AT refresh: ST → AT conversion via upstream API, validated by credits check.
2. ST refresh: personal mode only, via browser captcha service cookie extraction.
3. Concurrent refresh coalescing via asyncio tasks.

## 5. Current Test Coverage Areas

| Test File | Lines | Area |
|-----------|-------|------|
| `test_browser_captcha_personal.py` | 359 | Personal browser captcha service |
| `test_daily_stats_reset.py` | 85 | Daily statistics reset logic |
| `test_flow_client_upload.py` | 133 | Flow client upload behavior |
| `test_veo_lite_support.py` | 315 | Veo Lite model support |
| `test_yescaptcha_task_type.py` | 30 | YesCaptcha task type normalization |
| `testgeneration_config_max_retries.py` | 65 | Generation config max retries |

**Total test lines:** ~987. Coverage appears focused on specific edge cases rather than comprehensive integration testing.

## 6. Unknowns for Later Analysis

- **Database schema completeness:** Full table/column list not yet extracted; to be confirmed during contract extraction sprint.
- **Admin API full endpoint list:** `admin.py` is 2207 lines; complete route inventory to be cataloged in a later sprint.
- **Flow client upstream API contracts:** Exact request/response shapes for Google Labs / AI Sandbox APIs are embedded in `flow_client.py` (3123 lines) but not formally specified.
- **Captcha service selection logic at runtime:** How the system switches between captcha methods dynamically is partially in config and partially in lifespan; to be confirmed.
- **Streaming response format details:** SSE chunk structure for both OpenAI and Gemini formats is implemented inline; formal schema extraction needed.
- **`browser_captcha_personal.py` internals:** At 13,309 lines, this file likely contains substantial state machine logic, error recovery, and browser lifecycle management that has not been fully inspected.
- **Extension protocol:** WebSocket message format between the Chrome extension and the server is not formally documented.
- **Error handling and retry strategies:** Distributed across `flow_client`, `generation_handler`, and `token_manager`; unified error taxonomy not yet created.
- **Concurrency edge cases:** Interaction between soft limits, hard limits, pending tracking, and stagger delays across image and video paths.
