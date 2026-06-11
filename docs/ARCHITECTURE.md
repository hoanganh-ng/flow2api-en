# ARCHITECTURE.md

## System Overview

```
Downstream Clients (OpenAI / Gemini compatible)
        │
        ▼
┌──────────────────────────────────────────────────┐
│                  FastAPI Application               │
│                                                    │
│  ┌─────────┐   ┌─────────┐   ┌───────────────┐  │
│  │ routes  │   │  admin  │   │  static HTML  │  │
│  │ (API)   │   │ (mgmt)  │   │  (login/mgmt/ │  │
│  │         │   │         │   │   test pages) │  │
│  └────┬────┘   └────┬────┘   └───────────────┘  │
│       │              │                            │
│  ┌────▼──────────────▼──────────────────────┐    │
│  │         Core Layer                         │    │
│  │  config │ database │ auth │ models │      │    │
│  │  model_resolver │ monitoring │ logger      │    │
│  └────┬──────────────────────────────────────┘    │
│       │                                           │
│  ┌────▼──────────────────────────────────────┐    │
│  │         Services Layer                       │    │
│  │  generation_handler ──► flow_client         │    │
│  │  token_manager ──► flow_client              │    │
│  │  load_balancer ──► token_manager            │    │
│  │  concurrency_manager                        │    │
│  │  proxy_manager                              │    │
│  │  file_cache                                 │    │
│  │  browser_captcha (3 variants)               │    │
│  └────┬──────────────────────────────────────┘    │
│       │                                           │
└───────┼───────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│           Upstream Google Services                  │
│  labs.google/fx/api (project management)          │
│  aisandbox-pa.googleapis.com (generation)         │
│  reCAPTCHA Enterprise (token validation)          │
└──────────────────────────────────────────────────┘
```

## Runtime Flow

### Request Lifecycle

1. Client sends request to OpenAI or Gemini endpoint
2. `routes.py` normalizes request into `NormalizedGenerationRequest`
3. Model name resolved via `model_resolver.py`
4. `generation_handler` selects a token via `load_balancer`
5. Concurrency slot acquired via `concurrency_manager`
6. `flow_client` sends generation request to upstream
7. Polling loop checks upstream for completion
8. Result returned (media URL or inline data)
9. Concurrency slot released
10. Stats updated in database

### Token Lifecycle

1. Admin adds token (ST = session token) via admin UI or browser extension
2. `token_manager` exchanges ST for AT (access token)
3. AT has TTL; when expired, `token_manager` refreshes using ST
4. When ST expires, captcha flow is triggered to obtain new ST
5. Tokens can be banned after consecutive errors (threshold in admin config)
6. 429-banned tokens are auto-unbanned hourly

### Captcha Lifecycle

Five captcha methods supported:
- **extension**: Chrome extension solves reCAPTCHA on `labs.google`
- **personal**: nodriver-managed browser with project pool rotation
- **browser**: Headed Playwright browser instances
- **yescaptcha/capmonster/ezcaptcha/capsolver**: Third-party API captcha services
- **remote_browser**: External headed browser service via HTTP API

## Data Persistence

- **SQLite** via `aiosqlite` — single file at `data/flow2api.db`
- Schema created imperatively in `database.py` (`init_db`, `check_and_migrate_db`)
- Tables: tokens, token_stats, projects, tasks, request_logs, admin_config, proxy_config, generation_config, call_logic_config, cache_config, debug_config, captcha_config, plugin_config

## Configuration Flow

1. `config/setting.toml` loaded at startup (falls back to `setting_example.toml`)
2. Config values synced to database on first startup
3. Subsequent startups: database values take precedence; file is source of initial defaults
4. Admin UI can modify most config values at runtime (persisted to DB)

## Key Architectural Patterns

- **Dependency injection via globals**: `generation_handler`, `token_manager`, etc. are module-level globals set during app initialization
- **Lifespan context manager**: FastAPI lifespan handles startup/shutdown (browser init, warmup tasks, background tasks)
- **Dual API compatibility**: Single internal pipeline serves both OpenAI and Gemini request formats
- **Model resolution**: Simplified model names + `generationConfig` params are resolved to internal `MODEL_CONFIG` keys
