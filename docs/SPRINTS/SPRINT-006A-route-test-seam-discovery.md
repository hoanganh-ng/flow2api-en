# Sprint 006A — Route Test Seam Discovery

## Sprint Goal

Discover and document the safest seam for future route-level generation
compatibility tests. Do not implement route tests in this sprint.

## Context

Sprint 005A created sanitized static generation fixtures. Sprint 005B added
an offline fixture loader and static shape assertions. Sprint 005C added
additional sanitized generation fixtures. Sprint 005D added additional static
fixture assertions. The compatibility harness now validates fixture shapes
offline.

The next logical step is route-level compatibility testing for generation
endpoints, but this must be done carefully. Importing the FastAPI app or
generation routes may trigger runtime setup, config loading, database setup,
token/account lifecycle, captcha/browser/session behavior, proxy setup, or
upstream client wiring.

This sprint inspects the source code to identify safe test seams and document
unsafe approaches — without modifying any source files or adding any tests.

## Scope

- Inspect existing test conventions in `tests/`
- Inspect route and app construction without modifying source
- Identify generation route entrypoints and dependencies
- Identify safe test seam candidates for Sprint 006B
- Identify unsafe or risky test approaches to avoid
- Create discovery documentation:
  - `docs/ROUTE_TEST_SEAM_DISCOVERY.md`
  - `docs/GENERATION_ROUTE_TEST_PLAN.md`
  - `docs/SPRINTS/SPRINT-006A-route-test-seam-discovery.md`
- Update tracking documents:
  - `docs/PROJECT_STATE.md`
  - `docs/SPRINTS/README.md`
  - `docs/TEST_HARNESS_PLAN.md`

## Out of Scope

- Implementing route-level tests
- Importing or starting the FastAPI app in committed tests
- Modifying Python runtime source files under `src/`
- Modifying static/admin UI files
- Modifying config defaults
- Modifying Docker, compose, dependencies, scripts, README files, or LICENSE
- Calling upstream services
- Triggering token refresh, captcha/browser/session behavior, proxy behavior,
  or account lifecycle behavior
- Capturing real upstream responses
- Including real tokens, cookies, account identifiers, local secrets, upstream
  secrets, or personally identifying data
- Adding dependencies
- Adding fixture files
- Adding executable tests

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `docs/ROUTE_TEST_SEAM_DISCOVERY.md` | Test seam analysis: files inspected, safe seams, unsafe approaches |
| `docs/GENERATION_ROUTE_TEST_PLAN.md` | Proposed route-level test stages and Sprint 006B scope |
| `docs/SPRINTS/SPRINT-006A-route-test-seam-discovery.md` | This sprint document |

### Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Sprint 005D → completed, Sprint 006A → active, new docs listed |
| `docs/SPRINTS/README.md` | Sprint 005D → completed, Sprint 006A row added |
| `docs/TEST_HARNESS_PLAN.md` | Reflect Sprint 006A discovery, reference new documents |

### Inspected (not modified)

| File | Inspection purpose |
|------|---------------------|
| `src/main.py` | App construction, lifespan, dependency wiring |
| `src/api/routes.py` | Generation route handlers, conversion functions |
| `src/api/admin.py` | Admin router mounting context |
| `src/core/auth.py` | API key verification dependency |
| `src/core/models.py` | Pydantic request/response models |
| `src/core/model_resolver.py` | Model name resolution logic |
| `src/services/generation_handler.py` | Generation handler class and dependencies |
| `src/services/flow_client.py` | Upstream API client constructor |
| `tests/compatibility/test_static_generation_fixtures.py` | Offline static fixture test patterns |
| `tests/test_daily_stats_reset.py` | Database test pattern |
| `tests/test_flow_client_upload.py` | FlowClient mock pattern |
| `tests/test_veo_lite_support.py` | Model resolver + handler test patterns |
| `tests/test_yescaptcha_task_type.py` | Config normalization test pattern |
| `tests/test_browser_captcha_personal.py` | Browser captcha test patterns |
| `tests/testgeneration_config_max_retries.py` | Config + database test pattern |

## Verification Checklist

- [x] No Python source files under `src/` were modified
- [x] No test files were created or modified
- [x] No fixture files were created
- [x] No dependency files were modified
- [x] No Docker/compose files were modified
- [x] No README files were modified
- [x] No LICENSE file was modified
- [x] No static/admin UI files were modified
- [x] No config files were modified
- [x] No real tokens, secrets, cookies, or account IDs are included
- [x] No upstream responses were captured
- [x] No instructions for abuse, evasion, or bypassing access controls
- [x] Fork is clearly documented as unofficial
- [x] License and attribution are preserved
- [x] `git diff --name-only` shows only the 6 expected documentation files

## Sprint Type

**Discovery/docs-only.** This sprint produces analysis documents and updates
tracking documents. No executable code, tests, or fixtures are created or
modified. No runtime behavior is changed.

## Key Findings Summary

1. **Safest seam:** Conversion-layer pure functions in `src/api/routes.py` can
   be tested directly without any mocking or HTTP infrastructure.
2. **Second safest:** Model listing route handlers can be called directly with
   `api_key` passed as a keyword argument to satisfy the already-resolved dependency
   parameter, without exercising FastAPI dependency injection or auth behavior.
3. **Unsafe to avoid:** Importing `src.main` (creates singletons), running the
   lifespan (initializes databases, browsers, background tasks), and any test
   that touches `FlowClient`, `TokenManager`, or `BrowserCaptchaService` without
   comprehensive mocking.
4. **Recommended Sprint 006B scope:** Stage 1 (conversion-layer unit tests) and
   Stage 2 (model listing route tests). See
   [GENERATION_ROUTE_TEST_PLAN.md](../GENERATION_ROUTE_TEST_PLAN.md) for details.

## Next Steps

- Sprint 006B: Implement Stage 1 (conversion-layer unit tests) and Stage 2
  (model listing route tests) based on the seam analysis in this sprint.
- Sprint 006C (tentative): Implement Stage 3 (non-streaming generation with
  mocked handler) and Stage 4 (streaming generation).
