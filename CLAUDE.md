# CLAUDE.md — Project Brain for flow2api-en

## What This Is

This is an **unofficial English-friendly fork** of [flow2api](https://github.com/TheSmallHanCat/flow2api) by TheSmallHanCat. It is not endorsed by the upstream author. The original MIT license and attribution are preserved in [LICENSE](LICENSE).

## Current State

Sprint 000: Fork baseline and English project brain. **No runtime behavior changes.** All API, authentication, token, captcha, proxy, generation, Docker, config, model list, and admin UI behavior must remain identical to upstream unless a future sprint explicitly documents a change.

See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for full status.

## Tech Stack

- Python 3.11, FastAPI 0.119.0, Uvicorn
- Playwright + nodriver (browser captcha)
- curl-cffi (upstream HTTP impersonation)
- aiosqlite (SQLite persistence)
- Pydantic v2 (request/response models)
- Docker / Docker Compose (primary deployment)
- Chrome extension (Manifest V3) for extension-mode captcha

## Repository Layout

```
main.py                    # Uvicorn entrypoint
src/
  main.py                  # FastAPI app, lifespan, dependency wiring
  api/
    routes.py              # OpenAI + Gemini endpoints, WebSocket captcha
    admin.py               # Admin management endpoints (2200+ lines)
  core/
    config.py              # TOML config loader + runtime config properties
    database.py            # SQLite schema, migrations, CRUD (1950+ lines)
    models.py              # Pydantic data models
    model_resolver.py      # Simplified model name → internal key resolution
    auth.py                # API key + admin auth
    logger.py              # Debug logging
    monitoring.py          # Prometheus metrics
    account_tiers.py       # Account tier classification
  services/
    flow_client.py         # Upstream Google Flow API client
    token_manager.py       # Token lifecycle (ST→AT, refresh, ban/unban)
    load_balancer.py       # Multi-token selection strategy
    generation_handler.py  # Generation orchestration (image/video/upsample)
    concurrency_manager.py # Per-token concurrency slots
    proxy_manager.py       # HTTP/SOCKS proxy configuration
    file_cache.py          # Local file cache with TTL
    browser_captcha.py     # Headed browser captcha (Playwright)
    browser_captcha_personal.py  # nodriver-based personal captcha
    browser_captcha_extension.py # Chrome extension captcha bridge
    browser_cookie_utils.py      # Cookie extraction helpers
extension/                 # Chrome extension (Manifest V3)
static/                    # Admin UI HTML (login, manage, test)
config/                    # setting_example.toml
docker/                    # Headed Docker entrypoint
tests/                     # Unit tests
```

## High-Risk Areas (Do Not Change Without Explicit Sprint Scope)

1. **Token handling** — ST/AT lifecycle, refresh logic, 429 ban/unban
2. **Captcha/browser workflows** — extension, personal (nodriver), headed (Playwright), remote browser
3. **Proxy/network configuration** — request proxy, media proxy, browser proxy
4. **Upstream client behavior** — request signing, impersonation, polling, media upload
5. **Generation request/response compatibility** — OpenAI and Gemini payload shapes

## Key Commands

```bash
# Run locally
pip install -r requirements.txt
python main.py

# Run tests
pytest tests/

# Docker (standard)
docker-compose up -d

# Docker (headed captcha)
docker compose -f docker-compose.headed.yml up -d --build
```

## Coding Conventions

- Python files use Chinese comments extensively — do not bulk-translate existing comments
- Config keys are in `setting.toml` (TOML format), sections: global, flow, server, debug, proxy, generation, call_logic, admin, cache, captcha
- Database is SQLite via aiosqlite, schema managed imperatively in `database.py`
- FastAPI dependency injection is done via module-level globals set in `src/main.py`

## Documentation Index

- [Project State](docs/PROJECT_STATE.md)
- [Product Overview](docs/PRODUCT_OVERVIEW.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Module Boundaries](docs/MODULE_BOUNDARIES.md)
- [Glossary](docs/GLOSSARY.md)
- [Upstream Baseline](docs/UPSTREAM_BASELINE.md)
- [Security & Compliance](docs/SECURITY_AND_COMPLIANCE.md)
- [Decisions](docs/DECISIONS/ADR-0001-fork-principles.md)
- [Sprints](docs/SPRINTS/README.md)
