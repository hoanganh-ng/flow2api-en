# Entrypoints — flow2api-en

> **Sprint 001 deliverable.** Documentation-only. Based on source inspection. No runtime behavior has been changed.

## 1. Main Application Startup

### 1.1 CLI Entrypoint

**File:** `main.py` (root, 13 lines)

```python
# Observed in source (main.py:5-13)
if __name__ == "__main__":
    from src.core.config import config
    uvicorn.run(
        "src.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False
    )
```

- The application is started with `python main.py`.
- Uvicorn loads the `app` object from `src.main`.
- Host and port are read from the TOML config (`[server]` section, default `0.0.0.0:8000`).
- Reload is disabled.

### 1.2 FastAPI App Creation

**File:** `src/main.py` (lines 186–191)

```python
app = FastAPI(
    title="Flow2API",
    description="OpenAI-compatible API for Google VideoFX (Veo)",
    version="1.0.0",
    lifespan=lifespan
)
```

- The `app` object is created at module level (not inside a factory function).
- It uses a `lifespan` async context manager for startup/shutdown.

## 2. Lifespan / Startup / Shutdown

**File:** `src/main.py`, `lifespan()` function (lines 21–162)

### 2.1 Startup Sequence

Observed in source (lines 22–145):

1. Load raw config dict from TOML.
2. Check if database file exists (determines first startup).
3. Initialize database tables (`db.init_db()`).
4. First startup: populate config from TOML (`db.init_config_from_toml`).
5. Subsequent startups: check and migrate missing tables/columns (`db.check_and_migrate_db`).
6. Reload config from DB to memory (`db.reload_config_to_memory`).
7. Set cache timeout from config, start cache cleanup task.
8. Load all tokens from DB.
9. **If captcha method is `personal`:**
   - Import and initialize `BrowserCaptchaService` (nodriver mode).
   - Warm up resident tabs for project pool.
   - If no tokens available, open login window for manual setup.
10. **If captcha method is `browser`:**
    - Import and initialize `BrowserCaptchaService` (Playwright headed mode).
    - Warm up browser slots.
11. Initialize concurrency manager from token list.
12. **If captcha method is `remote_browser`:** prefill remote browser pool.
13. Start background task: auto-unban 429-banned tokens (hourly).
14. Print startup summary.
15. `yield` — application is now serving requests.

### 2.2 Shutdown Sequence

Observed in source (lines 147–162):

1. Stop file cache cleanup task.
2. Cancel auto-unban background task.
3. Close browser service if initialized.
4. Print shutdown summary.

## 3. Module-Level Component Initialization

**File:** `src/main.py` (lines 165–183)

These singletons are created at import time (module level), before the lifespan runs:

| Variable | Type | Dependencies |
|----------|------|-------------|
| `db` | `Database` | — |
| `proxy_manager` | `ProxyManager` | `db` |
| `flow_client` | `FlowClient` | `proxy_manager`, `db` |
| `token_manager` | `TokenManager` | `db`, `flow_client` |
| `concurrency_manager` | `ConcurrencyManager` | — |
| `load_balancer` | `LoadBalancer` | `token_manager`, `concurrency_manager` |
| `generation_handler` | `GenerationHandler` | `flow_client`, `token_manager`, `load_balancer`, `db`, `concurrency_manager`, `proxy_manager` |

Dependencies are injected into route modules via setters:
```python
routes.set_generation_handler(generation_handler)
admin.set_dependencies(token_manager, proxy_manager, db, concurrency_manager)
```

## 4. Middleware

**File:** `src/main.py` (lines 193–200)

CORS middleware is applied with permissive defaults:
- `allow_origins=["*"]`
- `allow_credentials=True`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

## 5. Routers

**File:** `src/main.py` (lines 202–204)

Two routers are included:
- `routes.router` — API endpoints (OpenAI, Gemini, model listing, WebSocket captcha).
- `admin.router` — Admin management endpoints.

## 6. Static File Serving

**File:** `src/main.py` (lines 206–248)

| Path | Source | Description |
|------|--------|-------------|
| `/tmp` | `tmp/` directory | Cached media files (mounted as `StaticFiles`) |
| `/` | `static/login.html` | Index redirects to login page |
| `/login` | `static/login.html` | Login page |
| `/manage` | `static/manage.html` | Admin management console |
| `/test` | `static/test.html` | Model testing page |

## 7. Metrics Endpoint

**File:** `src/main.py` (lines 251–255)

- `GET /metrics` — Prometheus metrics (text format).
- Calls `render_main_metrics(db, concurrency_manager)` on each request.

## 8. Docker / Compose Entrypoints

### 8.1 Default Dockerfile

**File:** `Dockerfile` (14 lines)

```dockerfile
CMD ["python", "main.py"]
```

- Base image: `python:3.11-slim`
- Working directory: `/app`
- Exposes port 8000.

### 8.2 Headed Dockerfile

**File:** `Dockerfile.headed`

- Not fully inspected in this sprint; expected to include browser dependencies (Chromium, Xvfb, Fluxbox).

### 8.3 Headed Entrypoint Script

**File:** `docker/entrypoint.headed.sh` (58 lines)

Observed behavior:
1. Resolves browser executable path (via Playwright or env var).
2. If `ALLOW_DOCKER_HEADED_CAPTCHA` is true:
   - Starts Xvfb on configured `DISPLAY`.
   - Starts Fluxbox window manager.
3. Executes `python main.py`.

### 8.4 Docker Compose

**File:** `docker-compose.yml` (16 lines)

- Maps host port 38000 → container port 8000.
- Volume mounts: `./data:/app/data`, `./tmp:/app/tmp`, `./config/setting.toml:/app/config/setting.toml`.
- `PYTHONUNBUFFERED=1`.

## 9. API Endpoint Summary

### 9.1 OpenAI-Compatible Routes (`routes.router`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| `GET` | `/v1/models` | `list_models` | API key |
| `GET` | `/v1/models/aliases` | `list_model_aliases` | API key |
| `POST` | `/v1/chat/completions` | `create_chat_completion` | API key |

### 9.2 Gemini-Compatible Routes (`routes.router`)

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| `GET` | `/v1beta/models` | `list_gemini_models` | API key |
| `GET` | `/models` | `list_gemini_models` | API key |
| `GET` | `/v1beta/models/{model}` | `get_gemini_model` | API key |
| `GET` | `/models/{model}` | `get_gemini_model` | API key |
| `POST` | `/v1beta/models/{model}:generateContent` | `generate_content` | API key |
| `POST` | `/models/{model}:generateContent` | `generate_content` | API key |
| `POST` | `/v1beta/models/{model}:streamGenerateContent` | `stream_generate_content` | API key |
| `POST` | `/models/{model}:streamGenerateContent` | `stream_generate_content` | API key |

### 9.3 WebSocket Route (`routes.router`)

| Type | Path | Handler | Auth |
|------|------|---------|------|
| `WS` | `/captcha_ws` | `captcha_websocket_endpoint` | API key (query/header) |

### 9.4 Admin Routes (`admin.router`)

To be fully cataloged in a later sprint. Observed patterns:
- Admin login/session management.
- Token CRUD and lifecycle operations.
- Configuration management for all subsystems.
- Dashboard statistics and health checks.
- Plugin connection management.

### 9.5 Static/HTML Routes

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| `GET` | `/` | `index` (serves `login.html`) | None |
| `GET` | `/login` | `login_page` | None |
| `GET` | `/manage` | `manage_page` | None |
| `GET` | `/test` | `test_page` | None |
| `GET` | `/metrics` | `metrics` | None |

## 10. Background Tasks

Observed in source (started during lifespan):

| Task | Interval | Description |
|------|----------|-------------|
| `auto_unban_task` | Every 3600s (1 hour) | Checks and unbans tokens disabled due to 429 rate limits |
| File cache cleanup | Every 300s (5 minutes) | Removes expired cached files (disabled if timeout ≤ 0) |
