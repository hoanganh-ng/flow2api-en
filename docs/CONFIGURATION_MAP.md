# Configuration Map — flow2api-en

> **Sprint 001 deliverable.** Documentation-only. Based on source inspection. No runtime behavior has been changed.

## 1. Configuration Files

### 1.1 Primary Config File

| File | Purpose | Loaded By |
|------|---------|-----------|
| `config/setting.toml` | User-provided runtime configuration | `src/core/config.py` (`Config._load_config`, line 34–41) |
| `config/setting_example.toml` | Fallback example configuration | `src/core/config.py` (if `setting.toml` is missing) |

**Format:** TOML (parsed via `tomli` library).

**Loading behavior (observed in source, `config.py` lines 34–41):**
```python
def _load_config(self) -> Dict[str, Any]:
    config_dir = Path(__file__).parent.parent.parent / "config"
    config_path = config_dir / "setting.toml"
    if not config_path.exists():
        config_path = config_dir / "setting_example.toml"
    with open(config_path, "rb") as f:
        return tomli.load(f)
```

- Config is loaded once at import time (global singleton).
- Can be reloaded at runtime via `config.reload_config()`.
- The `Config` class exposes each setting as a Python property.
- Many settings have runtime setters that update the in-memory dict (admin API can change settings without restart).

### 1.2 Environment Variables

No `os.getenv` or `os.environ` usage observed in `config.py`. The configuration system is TOML-based, not environment-variable-based.

Environment variables are used in:
- `docker/entrypoint.headed.sh`: `DISPLAY`, `XVFB_SCREEN`, `BROWSER_EXECUTABLE_PATH`, `ALLOW_DOCKER_HEADED_CAPTCHA`.
- `browser_captcha.py`: `PLAYWRIGHT_BROWSERS_PATH` (set to `"0"`).
- `file_cache.py`: `http_proxy`/`https_proxy` for wget subprocess.
- `docker-compose.yml`: `PYTHONUNBUFFERED=1`.

### 1.3 Database as Config Store

**File:** `src/core/database.py`

The database (`data/flow.db`) is the **authoritative runtime config store**. On first startup, config is initialized from TOML. On subsequent startups, the database config takes precedence.

Observed in source (`src/main.py` lines 39–49):
- First startup: `db.init_config_from_toml(config_dict, is_first_startup=True)`.
- Subsequent: `db.check_and_migrate_db(config_dict)`.
- Always: `db.reload_config_to_memory()` — syncs DB config to in-memory singleton.

## 2. Configuration Sections

### 2.1 `[global]` — Core Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_key` | string | `"han1234"` | API key for authenticating client requests |
| `admin_username` | string | `"admin"` | Admin login username |
| `admin_password` | string | `"admin"` | Admin login password |

**Source:** `config.py` lines 52–282.

**Persistence:** Stored in both TOML and `admin_config` DB table. DB values override TOML at runtime.

### 2.2 `[flow]` — Upstream API Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `labs_base_url` | string | `"https://labs.google/fx/api"` | Google Labs base URL for project management |
| `api_base_url` | string | `"https://aisandbox-pa.googleapis.com/v1"` | AI Sandbox API base URL for generation |
| `timeout` | int | `120` | General upstream request timeout (seconds, min 5) |
| `max_retries` | int | `3` | Max retries per request (min 1) |
| `image_request_timeout` | int | `40` | Single image HTTP request timeout (seconds) |
| `image_timeout_retry_count` | int | `1` | Fast retry count on image timeout (0–3) |
| `image_timeout_retry_delay` | float | `0.8` | Delay before timeout retry (seconds, 0–5) |
| `image_timeout_use_media_proxy_fallback` | bool | `true` | Switch to media proxy on timeout |
| `image_prefer_media_proxy` | bool | `false` | Always use media proxy for images |
| `image_slot_wait_timeout` | float | `480` | Hard concurrency slot wait timeout (seconds) |
| `image_launch_soft_limit` | int | `20` | Soft concurrency limit for image launch (0=disabled) |
| `image_launch_wait_timeout` | float | `480` | Soft concurrency wait timeout (seconds) |
| `image_launch_stagger_ms` | int | `0` | Stagger interval between image launches (ms) |
| `video_slot_wait_timeout` | float | `480` | Video hard concurrency slot wait timeout |
| `video_launch_soft_limit` | int | `20` | Video soft concurrency limit |
| `video_launch_wait_timeout` | float | `480` | Video soft concurrency wait timeout |
| `video_launch_stagger_ms` | int | `0` | Video launch stagger interval |
| `poll_interval` | float | `3.0` | Polling interval for async operations (seconds) |
| `max_poll_attempts` | int | `200` | Max polling attempts |

**Source:** `config.py` lines 68–233.

### 2.3 `[server]` — Server Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Bind address |
| `port` | int | `8000` | Bind port |

**Source:** `config.py` lines 236–241.

### 2.4 `[debug]` — Debug Logging

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable debug logging to `logs.txt` |
| `log_requests` | bool | `true` | Log outgoing requests |
| `log_responses` | bool | `true` | Log incoming responses |
| `mask_token` | bool | `true` | Mask tokens in logs |

**Source:** `config.py` lines 244–288, `logger.py`.

### 2.5 `[proxy]` — Proxy Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `proxy_enabled` | bool | `false` | Enable request proxy |
| `proxy_url` | string | `""` | Proxy URL for upstream requests |

**Note:** The TOML `[proxy]` section appears to be an initial config source. At runtime, proxy settings are managed via the `proxy_config` DB table and the `ProxyManager` service, which supports separate request and media proxies.

**Source:** `proxy_manager.py`, `models.py` `ProxyConfig`.

### 2.6 `[generation]` — Generation Timeouts

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `image_timeout` | int | `300` | Image generation overall timeout (seconds) |
| `video_timeout` | int | `1500` | Video generation overall timeout (seconds) |

**Source:** `config.py` lines 291–310, `models.py` `GenerationConfig`.

### 2.7 `[call_logic]` — Token Selection Mode

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `call_mode` | string | `"default"` | Token selection strategy: `"default"` (load-aware) or `"polling"` (round-robin) |

**Source:** `config.py` lines 312–338, `load_balancer.py`.

### 2.8 `[admin]` — Admin Behavior

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `error_ban_threshold` | int | `3` | Auto-disable token after N consecutive errors |

**Source:** `models.py` `AdminConfig`, `config/setting_example.toml` line 49.

### 2.9 `[cache]` — Media Cache

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Enable media caching |
| `timeout` | int | `7200` | Cache TTL in seconds (0 = never expire) |
| `base_url` | string | `""` | Base URL for cached file access (empty = use server address) |

**Source:** `config.py` lines 351–383, `file_cache.py`.

### 2.10 `[captcha]` — Captcha Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `captcha_method` | string | `"extension"` | Captcha method: `extension`/`yescaptcha`/`browser`/`personal`/`remote_browser` |
| `browser_recaptcha_settle_seconds` | float | `3.0` | Extra wait after reCAPTCHA page load |
| `browser_count` | int | `1` | Browser instances for captcha (1–20) |
| `personal_project_pool_size` | int | `4` | Projects per token (1–50) |
| `personal_max_resident_tabs` | int | `5` | Shared resident tabs per browser instance (1–50) |
| `browser_personal_fresh_restart_every_n_solves` | int | `10` | Restart browser after N solves (0=disabled) |
| `personal_idle_tab_ttl_seconds` | int | `600` | Tab idle timeout (seconds, min 60) |
| `yescaptcha_api_key` | string | `""` | YesCaptcha API key |
| `yescaptcha_base_url` | string | `"https://api.yescaptcha.com"` | YesCaptcha base URL |
| `yescaptcha_task_type` | string | `"RecaptchaV3TaskProxylessM1"` | YesCaptcha task type |
| `capmonster_api_key` | string | `""` | CapMonster API key |
| `capmonster_base_url` | string | `"https://api.capmonster.cloud"` | CapMonster base URL |
| `ezcaptcha_api_key` | string | `""` | EzCaptcha API key |
| `ezcaptcha_base_url` | string | `"https://api.ez-captcha.com"` | EzCaptcha base URL |
| `capsolver_api_key` | string | `""` | CapSolver API key |
| `capsolver_base_url` | string | `"https://api.capsolver.com"` | CapSolver base URL |
| `remote_browser_base_url` | string | `""` | Remote browser service URL |
| `remote_browser_api_key` | string | `""` | Remote browser API key |
| `remote_browser_timeout` | int | `60` | Remote browser timeout (seconds, min 5) |

**Additional captcha config fields (observed in `models.py` `CaptchaConfig` but not in example TOML):**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `website_key` | string | `"6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"` | reCAPTCHA website key |
| `page_action` | string | `"IMAGE_GENERATION"` | reCAPTCHA page action |
| `browser_proxy_enabled` | bool | `false` | Use proxy for browser captcha |
| `browser_proxy_url` | string | `None` | Browser captcha proxy URL |
| `browser_launch_background` | bool | `true` | Launch browser in background |
| `browser_idle_ttl_seconds` | int | `600` | Browser idle TTL |

**Source:** `config.py` lines 386–643, `models.py` `CaptchaConfig`.

## 3. Database-Persisted Configuration

The following tables in `data/flow.db` hold runtime configuration:

| Table | Model | Key Fields |
|-------|-------|-----------|
| `admin_config` | `AdminConfig` | username, password, api_key, error_ban_threshold |
| `proxy_config` | `ProxyConfig` | enabled, proxy_url, media_proxy_enabled, media_proxy_url |
| `generation_config` | `GenerationConfig` | image_timeout, video_timeout, max_retries |
| `cache_config` | `CacheConfig` | cache_enabled, cache_timeout, cache_base_url |
| `captcha_config` | `CaptchaConfig` | All captcha settings |
| `debug_config` | `DebugConfig` | enabled, log_requests, log_responses, mask_token |
| `plugin_config` | `PluginConfig` | connection_token, auto_enable_on_update |
| `call_logic_config` | `CallLogicConfig` | call_mode, polling_mode_enabled |

**Source:** `models.py`, `database.py`.

## 4. Configuration Ownership and Precedence

1. **TOML file** (`config/setting.toml`) — initial config source.
2. **Database** (`data/flow.db`) — authoritative runtime config.
3. **In-memory** (`Config` singleton) — runtime working state.

**Precedence rule (observed in source):**
- First startup: TOML → DB → memory.
- Subsequent startups: DB → memory (TOML used only for migration checks).
- Admin API changes: API → DB → memory (via setter methods on `Config`).

## 5. Proxy-Related Configuration

| Layer | Setting | Source |
|-------|---------|--------|
| Request proxy | `proxy_config.enabled` + `proxy_config.proxy_url` | DB, admin API |
| Media proxy | `proxy_config.media_proxy_enabled` + `proxy_config.media_proxy_url` | DB, admin API |
| Browser captcha proxy | `captcha_config.browser_proxy_enabled` + `captcha_config.browser_proxy_url` | DB, admin API |
| Token-level captcha proxy | `Token.captcha_proxy_url` | DB, per-token |
| Image proxy fallback | `flow.image_timeout_use_media_proxy_fallback` | TOML/config |
| Image prefer media proxy | `flow.image_prefer_media_proxy` | TOML/config |

**Source:** `proxy_manager.py`, `config.py`, `models.py`.

## 6. Token / Account-Related Configuration

Per-token settings stored in the `tokens` table:

| Field | Type | Description |
|-------|------|-------------|
| `st` | string | Session Token (`__Secure-next-auth.session-token`) |
| `at` | string | Access Token (derived from ST) |
| `at_expires` | datetime | AT expiration time |
| `email` | string | Account email |
| `is_active` | bool | Whether token is usable |
| `credits` | int | Remaining credits |
| `user_paygate_tier` | string | Account tier (Free/Pro/Ult) |
| `current_project_id` | string | Current active project UUID |
| `image_enabled` | bool | Image generation allowed |
| `video_enabled` | bool | Video generation allowed |
| `image_concurrency` | int | Image concurrency limit (-1=unlimited) |
| `video_concurrency` | int | Video concurrency limit (-1=unlimited) |
| `captcha_proxy_url` | string | Per-token captcha proxy override |
| `extension_route_key` | string | Extension routing key |
| `ban_reason` | string | Why token was disabled |
| `banned_at` | datetime | When token was banned |

**Source:** `models.py` `Token` class.

## 7. Admin / Security-Related Configuration

| Setting | Location | Description |
|---------|----------|-------------|
| Admin username | `admin_config` table / `[global]` TOML | Admin login credential |
| Admin password | `admin_config` table / `[global]` TOML | Admin login credential (observed in source: appears stored without hashing — to be confirmed) |
| API key | `admin_config` table / `[global]` TOML | Client authentication key |
| Error ban threshold | `admin_config` table / `[admin]` TOML | Auto-disable after N consecutive errors |
| Admin session tokens | In-memory (`active_admin_tokens` set in `admin.py`) | Ephemeral session management |

**Note:** Admin password is stored in plaintext in both TOML and database. `bcrypt` is imported but appears to be available for hashing (observed in `auth.py` lines 27–34) but not consistently used for storage. To be confirmed during contract extraction.

## 8. Uncertainties (To Be Confirmed)

- Whether `setting.toml` is ever written back to disk at runtime (not observed; likely no).
- Full list of admin API config mutation endpoints.
- Whether plugin_config `connection_token` is used for WebSocket authentication or something else.
- Exact DB migration behavior when new columns are added between versions.
- Whether `website_key` and `page_action` in `CaptchaConfig` are ever changed from defaults.
