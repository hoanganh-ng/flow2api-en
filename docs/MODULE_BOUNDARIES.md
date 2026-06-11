# MODULE_BOUNDARIES.md

## Initial Module Boundary Assumptions

These boundaries are based on initial inspection of the repository structure and key source files. They will be refined with source-verified detail in later sprints.

---

### 1. HTTP/API Compatibility Layer

**Files**: `src/api/routes.py`

**Responsibility**: Accept OpenAI and Gemini format requests, normalize them into a shared internal shape, and return responses in the format the client expects.

**Key types**: `NormalizedGenerationRequest`, `ChatCompletionRequest`, `GeminiGenerateContentRequest`

**Boundary notes**:
- Contains WebSocket endpoint for extension captcha (`/captcha_ws`)
- Contains all model catalog endpoints (`/v1/models`, `/v1beta/models`, etc.)
- Handles SSE streaming for both OpenAI and Gemini formats
- Has Gemini-specific error status code mapping

**Risk**: HIGH — any change to request normalization or response formatting breaks downstream clients.

---

### 2. Upstream Flow Client Behavior

**Files**: `src/services/flow_client.py`

**Responsibility**: Communicate with Google's Flow API to create projects, submit generation requests, poll for results, upload media, and refresh tokens.

**Boundary notes**:
- Uses `curl_cffi` for TLS impersonation
- Handles AT→generation request, polling, media upload/download
- Project creation and management for captcha flows
- Remote browser prefill integration

**Risk**: HIGH — upstream API changes can break all generation. This module is tightly coupled to upstream request/response formats.

---

### 3. Token/Account Lifecycle

**Files**: `src/services/token_manager.py`, `src/core/account_tiers.py`

**Responsibility**: Manage token CRUD, ST↔AT exchange, expiration tracking, error-based banning, 429 auto-unban, daily stats reset, and account tier classification.

**Boundary notes**:
- `token_manager` depends on `flow_client` for AT refresh and `database` for persistence
- Account tiers (`account_tiers.py`) classify tokens by `user_paygate_tier`
- Personal warmup project ID generation for browser captcha

**Risk**: HIGH — token refresh failures cascade to all generation.

---

### 4. Browser/Captcha/Session Lifecycle

**Files**: `src/services/browser_captcha.py`, `src/services/browser_captcha_personal.py`, `src/services/browser_captcha_extension.py`, `src/services/browser_cookie_utils.py`, `extension/`

**Responsibility**: Solve reCAPTCHA challenges to obtain fresh Google session tokens.

**Boundary notes**:
- Three browser-based modes: Playwright (headed), nodriver (personal), Chrome extension
- Third-party captcha services: YesCaptcha, CapMonster, EzCaptcha, CapSolver
- Remote browser mode via HTTP API
- Extension uses Manifest V3 with WebSocket bridge to server
- Personal mode manages project pool rotation and tab lifecycle

**Risk**: HIGH — most complex subsystem with multiple browser engines, tab management, and timing-sensitive operations.

---

### 5. Proxy/Network Configuration

**Files**: `src/services/proxy_manager.py`

**Responsibility**: Manage HTTP/SOCKS proxy settings for upstream requests and media transfers.

**Boundary notes**:
- Separate proxy for requests vs. media (image upload/download)
- Per-token captcha proxy override
- Browser proxy configuration
- Proxy URL stored in database, managed via admin UI

**Risk**: MEDIUM — proxy misconfiguration can cause silent failures or IP exposure.

---

### 6. Generation/Media Handling

**Files**: `src/services/generation_handler.py`, `src/services/file_cache.py`

**Responsibility**: Orchestrate the full generation pipeline — token selection, request submission, polling, result formatting, caching.

**Boundary notes**:
- Contains `MODEL_CONFIG` — the master model registry with upstream keys and types
- Handles image, video, R2V, interpolation, upsample, and extend flows
- File cache with TTL-based cleanup
- Integrates with load balancer and concurrency manager

**Risk**: HIGH — central orchestration point; changes affect all generation types.

---

### 7. Admin UI / Static Assets

**Files**: `src/api/admin.py`, `static/login.html`, `static/manage.html`, `static/test.html`

**Responsibility**: Web-based administration for tokens, configuration, monitoring, and model testing.

**Boundary notes**:
- `admin.py` is 2200+ lines — handles all management CRUD, token import, config updates
- Static HTML pages with embedded JavaScript (no build step)
- Admin authentication via session cookies
- Token import via browser extension WebSocket

**Risk**: MEDIUM — admin changes don't affect generation, but admin.py is large and tightly coupled to database schema.

---

### 8. Config/Persistence

**Files**: `src/core/config.py`, `src/core/database.py`

**Responsibility**: Load TOML configuration, manage SQLite schema, handle migrations, provide CRUD for all entities.

**Boundary notes**:
- `config.py`: 648 lines of property accessors with validation/clamping
- `database.py`: 1950+ lines — imperative schema management, no ORM
- Config precedence: TOML → database (first run), database → memory (subsequent runs)
- Migration logic checks for missing tables/columns

**Risk**: MEDIUM — schema changes require careful migration logic.

---

### 9. Observability

**Files**: `src/core/monitoring.py`, `src/core/logger.py`

**Responsibility**: Prometheus metrics export and structured debug logging.

**Boundary notes**:
- `/metrics` endpoint renders Prometheus-format metrics
- `/health` endpoint returns service health summary
- Debug logger with configurable request/response logging and token masking
- Metrics cover: active tokens, expiring tokens, banned tokens, generation counts

**Risk**: LOW — additive only; doesn't affect generation behavior.

---

### 10. Load Balancing / Concurrency

**Files**: `src/services/load_balancer.py`, `src/services/concurrency_manager.py`

**Responsibility**: Select which token handles a request and enforce per-token concurrency limits.

**Boundary notes**:
- Two call logic modes: `default` (random weighted) and `polling` (sequential round-robin)
- Per-token image and video concurrency limits (-1 = unlimited)
- Concurrency slots tracked in-memory, not persisted

**Risk**: MEDIUM — load balancing logic affects token utilization and error distribution.

---

## Cross-Cutting Concerns

| Concern | Modules Involved |
|---------|-----------------|
| Database access | All services + core |
| Config access | All modules via global `config` singleton |
| Proxy routing | flow_client, proxy_manager, browser_captcha variants |
| Token selection | load_balancer → token_manager → generation_handler |
| Error handling | routes.py, generation_handler, flow_client |
