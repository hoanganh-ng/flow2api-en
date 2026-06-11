# Risk Register — flow2api-en

> **Sprint 001 deliverable.** Documentation-only. Based on source inspection. No runtime behavior has been changed.

Each risk entry identifies a high-risk area, why it is risky, what must be preserved, and which later sprint should inspect it more deeply.

---

## R-01: Upstream Client Behavior

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/flow_client.py` (3123 lines) |
| **Why risky** | This is the largest file and the sole interface with upstream Google Labs / AI Sandbox APIs. Observed in source: it contains inline URL patterns, request shapes, header impersonation, polling logic, and retry strategies. Any upstream API change could break generation silently. |
| **What must be preserved** | ST-to-AT conversion flow, image generation request/response cycle, video scene creation and polling, captcha token acquisition integration, browser fingerprint management (UA caching, context-var fingerprinting), proxy-aware request routing, media proxy fallback logic. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — extract exact request/response schemas, URL patterns, header requirements, and error handling contracts. |

---

## R-02: Authentication / Token Lifecycle

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/token_manager.py` (780 lines), `src/core/auth.py` (63 lines) |
| **Why risky** | Token lifecycle is central to system operation. ST→AT conversion, AT refresh timing, ST refresh via browser, concurrent refresh coalescing, and 429 auto-ban/unban all interact in complex ways. A mistake could cause all tokens to become invalid simultaneously. |
| **What must be preserved** | AT refresh threshold (1 hour before expiry), ST refresh only in personal mode, concurrent refresh coalescing via asyncio tasks, 429 ban after rate limit detection, 12-hour auto-unban cycle, consecutive error auto-disable with configurable threshold, credits/tier refresh. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — document exact refresh state machine, timing thresholds, and failure mode behavior. |

---

## R-03: Captcha / Browser / Session Lifecycle

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/browser_captcha_personal.py` (13,309 lines), `src/services/browser_captcha.py` (2122 lines), `src/services/browser_captcha_extension.py` (215 lines), `src/services/browser_cookie_utils.py` (316 lines), `extension/` (5 files) |
| **Why risky** | `browser_captcha_personal.py` alone is 13,309 lines — over 40% of all Python code. It manages a complex resident tab pool, browser profile lifecycle, reCAPTCHA token generation, ST refresh via cookie extraction, and tab idle TTL. Browser automation is inherently fragile (Chrome updates, reCAPTCHA changes, OS-level dependencies). |
| **What must be preserved** | Resident tab pool sizing and sharing model, per-project tab assignment, warmup behavior at startup, fresh profile restart threshold, idle tab TTL and cleanup, ST refresh via cookie extraction, extension WebSocket protocol, captcha method selection logic at startup. |
| **Deeper inspection sprint** | Sprint 003 or later — this is the most complex subsystem and requires dedicated analysis. Consider splitting into multiple sub-sprints. |

---

## R-04: Proxy Behavior

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/proxy_manager.py` (151 lines), `src/core/config.py` (proxy properties), `src/services/flow_client.py` (proxy usage), `src/services/file_cache.py` (proxy for downloads) |
| **Why risky** | Multiple proxy layers exist: request proxy, media proxy, browser captcha proxy, per-token captcha proxy, and media proxy fallback on timeout. Incorrect proxy routing could expose the real IP to upstream or cause all requests to fail. |
| **What must be preserved** | Proxy URL normalization (multiple input formats), request vs. media proxy separation, media proxy fallback on image timeout, per-token captcha proxy override, browser proxy configuration. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — map all proxy decision points and fallback chains. |

---

## R-05: Model Registry and Generation Routing

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/generation_handler.py` (MODEL_CONFIG dict, 2467 lines total), `src/core/model_resolver.py` (634 lines), `src/core/account_tiers.py` (58 lines) |
| **Why risky** | Observed in source: MODEL_CONFIG is a large inline dict mapping internal model keys to upstream model names and parameters. Model resolution involves aspect ratio, image size, OpenAI compatibility, and account tier checks. Adding or removing models incorrectly could route requests to wrong upstream endpoints. |
| **What must be preserved** | All existing model keys and their upstream mappings, aspect ratio normalization, image size resolution, OpenAI size/quality compatibility, tier-based model filtering (Free/Pro/Ult), video model orientation handling. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — extract complete MODEL_CONFIG inventory and resolution algorithm. |

---

## R-06: Streaming Responses

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/api/routes.py` (lines 717–786 for stream iterators), `src/services/generation_handler.py` (streaming generation) |
| **Why risky** | Two distinct streaming formats are supported: OpenAI SSE and Gemini SSE. The conversion between internal OpenAI-format chunks and Gemini-format events is done inline. Incorrect streaming could break client integrations. |
| **What must be preserved** | OpenAI SSE format (`data: {...}\n\n` + `data: [DONE]\n\n`), Gemini SSE format (candidates/parts structure), error injection into streams, finish reason mapping, `text/event-stream` media type with correct headers. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — document exact SSE chunk schemas for both formats. |

---

## R-07: Upload / Media Handling

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/flow_client.py` (upload logic), `src/services/file_cache.py` (515 lines), `src/api/routes.py` (image extraction/decoding) |
| **Why risky** | Image inputs can come from data URLs, HTTP URLs, local cache, or chat history reference images. The system downloads remote images, decodes base64, and passes binary data upstream. Upload to upstream for image-to-video also goes through `flow_client`. |
| **What must be preserved** | Data URL decoding, remote image fetching with proxy support, MIME type detection, reference image extraction from chat history, `extend://` media ID handling for video continuation, file cache download chain (curl_cffi → wget → curl). |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — document upload request/response contracts and cache behavior. |

---

## R-08: Admin UI / Security

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/api/admin.py` (2207 lines), `src/core/auth.py` (63 lines), `static/` (3 HTML files) |
| **Why risky** | The admin API has full CRUD access to all tokens, configs, and system state. Observed in source (`auth.py`, `admin.py`): admin authentication appears to use direct string comparison for credentials; `bcrypt` is imported but its usage for storage is unclear. Admin session tokens are stored in-memory (not persisted). CORS is configured to allow all origins (`*`). |
| **What must be preserved** | Admin login flow, session token management, all CRUD endpoints, dependency injection pattern, input validation (or lack thereof — to be assessed). |
| **Security concerns** | Observed in source: admin password appears stored without hashing in config and DB. CORS configured as wildcard (`*`). In-memory session tokens (lost on restart). No rate limiting on admin endpoints observed. To be confirmed during security audit sprint. |
| **Deeper inspection sprint** | Sprint 002 or dedicated security sprint. |

---

## R-09: Persistence / Data Migration

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/core/database.py` (1950 lines) |
| **Why risky** | SQLite with custom migration logic (add missing tables/columns). No formal migration framework. Schema evolution is handled imperatively in `check_and_migrate_db`. A bug could corrupt token data or lose configuration. |
| **What must be preserved** | All table schemas, first-startup initialization from TOML, migration logic (additive only), write serialization via asyncio lock, daily stats reset logic, in-memory config reload. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — extract complete DB schema and migration history. |

---

## R-10: Concurrency / Load Balancing

| Attribute | Value |
|-----------|-------|
| **Source area** | `src/services/concurrency_manager.py` (303 lines), `src/services/load_balancer.py` (356 lines), `src/services/generation_handler.py` (soft/hard concurrency logic) |
| **Why risky** | Multiple concurrency layers interact: soft limits (pre-launch shaping), hard limits (slot-based), pending tracking (burst smoothing), stagger delays, and wait-acquire with timeout. Incorrect interaction could cause deadlocks, request starvation, or upstream overload. |
| **What must be preserved** | Per-token image/video limits, wait-acquire with configurable timeout, pending count tracking, round-robin vs. load-aware selection, tier-based filtering, extension route checking, slot pre-reservation. |
| **Deeper inspection sprint** | Sprint 002 (contract extraction) — document concurrency state machine and interaction between soft/hard limits. |

---

## R-11: Test Coverage Gaps

| Attribute | Value |
|-----------|-------|
| **Source area** | `tests/` (6 files, ~987 lines) |
| **Why risky** | Current tests cover specific edge cases (YesCaptcha task type, daily stats reset, Veo Lite support, flow client upload, browser captcha personal, generation config max retries). No integration tests, no API contract tests, no streaming tests, no load balancer tests, no database migration tests observed. |
| **What must be preserved** | Existing test files and their assertions. |
| **Gaps identified** | API endpoint integration tests, streaming format tests, model resolver tests, load balancer tests, concurrency manager tests, database migration tests, admin API tests, token refresh state machine tests. |
| **Deeper inspection sprint** | Sprint 002+ — build test harness before any refactoring begins. |

---

## Risk Summary

| ID | Area | Severity | Complexity | Sprint |
|----|------|----------|-----------|--------|
| R-01 | Upstream client | High | High | 002 |
| R-02 | Token lifecycle | High | High | 002 |
| R-03 | Captcha/browser | Critical | Very High | 003+ |
| R-04 | Proxy behavior | Medium | Medium | 002 |
| R-05 | Model registry | Medium | Medium | 002 |
| R-06 | Streaming | Medium | Medium | 002 |
| R-07 | Upload/media | Medium | Medium | 002 |
| R-08 | Admin/security | High | Medium | 002 or security sprint |
| R-09 | Persistence/migration | High | Medium | 002 |
| R-10 | Concurrency/LB | Medium | High | 002 |
| R-11 | Test coverage | High | — | 002+ |
