# UPSTREAM_BASELINE.md

## Upstream Project

| Field | Value |
|-------|-------|
| **Name** | flow2api |
| **Author** | TheSmallHanCat |
| **Repository** | https://github.com/TheSmallHanCat/flow2api |
| **License** | MIT (Copyright © 2025 TheSmallHanCat) |
| **Language** | Python 3.8+ (tested on 3.11) |
| **Framework** | FastAPI 0.119.0 |
| **Last synced commit** | `ab3b2c9` (HEAD of main at fork time) |

## Observed Repository Structure (at fork time)

```
flow2api/
├── .github/workflows/         # CI: Docker publish (standard + beta)
├── config/
│   └── setting_example.toml   # Example configuration
├── docker/
│   └── entrypoint.headed.sh   # Headed Docker startup script
├── docs/
│   ├── DECISIONS/             # (empty at fork time)
│   └── SPRINTS/               # (empty at fork time)
├── extension/                 # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── options.html
│   └── options.js
├── src/
│   ├── main.py                # FastAPI app initialization
│   ├── api/
│   │   ├── routes.py          # OpenAI + Gemini endpoints
│   │   └── admin.py           # Admin management endpoints
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # SQLite database layer
│   │   ├── models.py          # Pydantic data models
│   │   ├── model_resolver.py  # Model name resolution
│   │   ├── auth.py            # Authentication
│   │   ├── logger.py          # Debug logging
│   │   ├── monitoring.py      # Prometheus metrics
│   │   └── account_tiers.py   # Account tier logic
│   └── services/
│       ├── flow_client.py     # Upstream Flow API client
│       ├── token_manager.py   # Token lifecycle
│       ├── load_balancer.py   # Token selection
│       ├── generation_handler.py  # Generation orchestration
│       ├── concurrency_manager.py # Concurrency control
│       ├── proxy_manager.py   # Proxy configuration
│       ├── file_cache.py      # Media file cache
│       ├── browser_captcha.py # Playwright captcha
│       ├── browser_captcha_personal.py  # nodriver captcha
│       ├── browser_captcha_extension.py # Extension captcha
│       └── browser_cookie_utils.py     # Cookie helpers
├── static/
│   ├── login.html             # Login page
│   ├── manage.html            # Admin management page
│   └── test.html              # Model testing page
├── tests/                     # Unit tests
├── main.py                    # Uvicorn entrypoint
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Standard Docker image
├── Dockerfile.headed          # Headed browser Docker image
├── docker-compose.yml         # Standard deployment
├── docker-compose.headed.yml  # Headed deployment
├── docker-compose.proxy.yml   # Proxy (WARP) deployment
├── docker-compose.local.yml   # Local development
└── LICENSE                    # MIT License
```

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.119.0 | Web framework |
| uvicorn | 0.32.1 | ASGI server |
| aiosqlite | 0.20.0 | Async SQLite |
| pydantic | 2.10.4 | Data validation |
| curl-cffi | 0.7.3 | TLS impersonation HTTP client |
| httpx | >=0.27.0 | Async HTTP client |
| playwright | >=1.40.0 | Browser automation |
| nodriver | >=0.48.0 | Undetected Chrome |
| prometheus-client | 0.22.1 | Metrics |
| bcrypt | 4.2.1 | Password hashing |
| tomli | 2.2.1 | TOML parser |

## Known High-Risk Areas

1. **Upstream API coupling** — `flow_client.py` is tightly coupled to Google's internal API endpoints, request formats, and authentication flows. Any upstream change can break generation.

2. **Token handling** — ST/AT exchange, refresh logic, and captcha-triggered renewal are critical path. Failures cascade to all generation.

3. **Captcha subsystem** — Three browser-based modes plus four third-party services. Complex state management, timing-sensitive operations, browser lifecycle management.

4. **Model configuration** — `MODEL_CONFIG` in `generation_handler.py` is a large dictionary mapping internal model IDs to upstream keys. Upstream model changes require manual updates.

5. **Database migrations** — Imperative schema management in `database.py` without a migration framework. Schema changes require careful manual migration logic.

6. **TLS impersonation** — `curl_cffi` is used to impersonate Chrome's TLS fingerprint. Upstream fingerprint detection changes could break requests.

7. **Concurrency model** — In-memory semaphores for concurrency control. Not distributed; single-process only.

## Explicit Unknowns (Require Source Analysis in Later Sprints)

- Exact upstream request signing/headers for `aisandbox-pa.googleapis.com`
- Token exchange flow details (ST → AT mechanism)
- Project creation and management protocol on `labs.google/fx/api`
- Video generation polling protocol and operation lifecycle
- Media upload/download flow and proxy fallback logic
- R2V structured prompt assembly details
- Extend (video continuation) protocol
- Account tier effects on available models and rate limits
- Personal mode tab lifecycle and project rotation algorithm
- Extension WebSocket protocol message format
- Database migration edge cases across schema versions
- Admin session management and CSRF handling
- Exact error code mapping from upstream to downstream responses
