# SECURITY_AND_COMPLIANCE.md

## Licensing

This fork preserves the original MIT license from the upstream project.

- **Upstream license**: MIT — Copyright (c) 2025 TheSmallHanCat
- **License file**: [LICENSE](../LICENSE)
- **Obligation**: The original copyright notice and permission notice must remain in all copies or substantial portions of the Software.

## Fork Attribution

This is an **unofficial fork** and is not endorsed by the upstream author. The fork adds English documentation and planning artifacts. No upstream source code has been modified in Sprint 000.

## Security Considerations

### Token Handling

- Session tokens (ST) and access tokens (AT) for Google accounts are stored in SQLite (`data/flow2api.db`)
- Tokens are sensitive credentials — the database file should be protected with filesystem permissions
- The `debug.mask_token` config option controls whether tokens are masked in logs (default: `true`)
- Admin API key is stored in config file and database

### Authentication

- API key authentication protects generation endpoints
- Admin UI uses username/password authentication with bcrypt hashing
- Default credentials are `admin`/`admin` — must be changed on first login
- No rate limiting on authentication endpoints (potential brute-force vector)
- No CSRF protection on admin forms (static HTML with embedded JS)

### Network Security

- CORS is configured to allow all origins (`allow_origins=["*"]`)
- TLS is not terminated by the application — expected to be behind a reverse proxy
- Proxy URLs (HTTP/SOCKS5) are stored in plain text in the database
- `curl_cffi` uses `verify=False` for some upstream requests (TLS verification disabled)

### Captcha Infrastructure

- Third-party captcha services receive the site key and page URL
- Browser-based captcha modes launch real browser instances
- Captcha tokens are short-lived and not persisted

### Admin Interface

- Management endpoints are protected by admin session cookies
- No RBAC — single admin role with full access
- Token import via browser extension WebSocket uses API key authentication
- Debug mode can log full request/response bodies (including tokens if masking is disabled)

### Observability

- `/health` endpoint is public (no authentication required)
- `/metrics` endpoint is public (no authentication required) — contains operational metrics
- Prometheus metrics include token counts, ban counts, and generation statistics
- Request logging is configurable via debug settings

## Compliance Notes

### Upstream Terms of Service

This project interfaces with Google's services. Users should be aware of:
- Google's Terms of Service for Google Labs / VideoFX
- Google's reCAPTCHA Terms of Service
- Rate limits and usage policies of the upstream service

### Data Privacy

- No user prompts or generated content are sent to third parties (except the upstream Google service)
- Image data for generation is passed through to upstream
- Cached files are stored locally in `tmp/` directory
- Database contains credentials and usage statistics

## Anti-Abuse Statement

This documentation project does not design, implement, or encourage:
- Bypassing upstream access controls
- Evading rate limits beyond what the upstream service permits
- Circumventing security measures
- Unauthorized access to Google services

All behavior is inherited from the upstream project and is intended to remain unchanged unless explicitly documented in a future sprint with appropriate security review.
