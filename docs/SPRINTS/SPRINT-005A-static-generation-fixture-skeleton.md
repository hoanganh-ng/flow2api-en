# Sprint 005A — Static Generation Fixture Skeleton

**Status:** Active  
**Sprint Number:** 005A  
**Type:** Documentation + Fixture Creation  
**Dependencies:** Sprint 004 (Generation Fixture Plan)

---

## Goal

Create the first minimal, sanitized, static fixture skeleton for generation compatibility testing. This sprint produces synthetic fixture files for three priority-1 fixtures without implementing executable tests or runtime behavior.

---

## Context

- Sprint 000 established the English project brain and documentation baseline
- Sprint 001 mapped the existing system (system map, entrypoints, configuration)
- Sprint 001A audited English surfaces and created a translation plan
- Sprint 001B safely translated the README
- Sprint 001C created a translation allowlist for remaining Chinese surfaces
- Sprint 002 inventoried the API surface (endpoints, compatibility notes, risk classification)
- Sprint 003 documented the generation contract (request/response shapes, streaming behavior, model resolution)
- Sprint 004 planned generation fixtures (fixture matrix, test harness strategy, sanitization policy)

Sprint 005A executes the first slice of Sprint 004's fixture plan by creating static, synthetic fixture files for the highest-priority generation compatibility tests.

---

## Scope

### In Scope

1. **Create fixture directory structure** under `tests/fixtures/generation/`
2. **Create static fixture files** for three priority-1 fixtures:
   - FX-ML-001: OpenAI model list response shape
   - FX-ON-001: OpenAI non-streaming text request/response shape
   - FX-OS-003: OpenAI streaming `[DONE]` termination sentinel
3. **Document fixtures** with README files explaining purpose, verification scope, and limitations
4. **Update project state** to reflect Sprint 005A as active
5. **Mark Sprint 004 completed** in project documentation

### Out of Scope

- Executable test runner or test harness code
- Assertion utilities or shape validators
- Fixture loader utilities
- Runtime-captured fixtures from live upstream services
- Gemini endpoint fixtures (deferred to future sprint)
- Media generation fixtures (images, videos)
- Error response fixtures
- Request conversion fixtures
- Modifications to Python runtime source code
- Modifications to static/admin UI files
- Modifications to configuration defaults
- Modifications to Docker, compose, dependencies, scripts, README files, or LICENSE
- Translation of any files
- Refactoring or feature additions
- Upstream service calls or real credential usage

---

## Files Changed

### New Fixture Directories

- `tests/fixtures/`
- `tests/fixtures/generation/`
- `tests/fixtures/generation/model-list/`
- `tests/fixtures/generation/openai-non-streaming/`
- `tests/fixtures/generation/openai-streaming/`

### New Fixture Files

1. **`tests/fixtures/generation/model-list/openai-model-list.json`** (FX-ML-001)
   - Synthetic OpenAI-compatible model list response
   - Contains 3 representative model entries from documented catalog
   - Verifies response shape: `object`, `data`, model fields

2. **`tests/fixtures/generation/openai-non-streaming/text-basic-request.json`** (FX-ON-001 request)
   - Minimal POST `/v1/chat/completions` request shape
   - Fields: `model`, `messages`, `stream: false`
   - Uses placeholder prompt text

3. **`tests/fixtures/generation/openai-non-streaming/text-basic-response.json`** (FX-ON-001 response)
   - Synthetic OpenAI-compatible chat completion response
   - Fields: `id`, `object`, `created`, `model`, `choices`, `usage`
   - Uses synthetic timestamps and placeholder content

4. **`tests/fixtures/generation/openai-streaming/done-termination.sse.txt`** (FX-OS-003)
   - Minimal SSE stream with one data chunk
   - Terminates with `data: [DONE]` sentinel
   - Verifies streaming termination shape

### New Documentation Files

5. **`tests/fixtures/README.md`**
   - Purpose of fixture directory
   - Sanitization policy (no secrets, no real upstream responses)
   - Fixture naming conventions
   - Future test harness note

6. **`tests/fixtures/generation/README.md`**
   - Generation fixture scope
   - Per-fixture documentation (FX-ML-001, FX-ON-001, FX-OS-003)
   - What each fixture verifies and does not verify
   - Runtime capture status

7. **`docs/SPRINTS/SPRINT-005A-static-generation-fixture-skeleton.md`** (this file)
   - Sprint goal, context, scope
   - Files changed
   - Verification checklist

### Modified Documentation Files

8. **`docs/PROJECT_STATE.md`**
   - Mark Sprint 004 completed
   - Mark Sprint 005A active
   - Note first fixture skeleton in progress

9. **`docs/SPRINTS/README.md`**
   - Add Sprint 005A to sprint index
   - Mark Sprint 004 completed, Sprint 005A active

10. **`docs/TEST_HARNESS_PLAN.md`**
    - Clarify Sprint 005A as fixture skeleton step
    - Note no test runner/assertion utilities included yet

11. **`docs/GENERATION_FIXTURE_MATRIX.md`**
    - Mark FX-ML-001, FX-ON-001, FX-OS-003 as skeleton files created
    - Note not yet tested

---

## Verification Checklist

### File Existence

- [ ] `tests/fixtures/` directory exists
- [ ] `tests/fixtures/generation/` directory exists
- [ ] `tests/fixtures/generation/model-list/` directory exists
- [ ] `tests/fixtures/generation/openai-non-streaming/` directory exists
- [ ] `tests/fixtures/generation/openai-streaming/` directory exists
- [ ] All 6 new files created (4 fixtures + 2 READMEs)
- [ ] Sprint 005A documentation created
- [ ] PROJECT_STATE.md updated
- [ ] SPRINTS/README.md updated
- [ ] TEST_HARNESS_PLAN.md updated
- [ ] GENERATION_FIXTURE_MATRIX.md updated

### JSON Validation

- [ ] `tests/fixtures/generation/model-list/openai-model-list.json` is valid JSON
- [ ] `tests/fixtures/generation/openai-non-streaming/text-basic-request.json` is valid JSON
- [ ] `tests/fixtures/generation/openai-non-streaming/text-basic-response.json` is valid JSON

### Sanitization Check

- [ ] No real API keys, tokens, or credentials in fixture files
- [ ] No real cookies or session identifiers
- [ ] No real account IDs or personally identifying information
- [ ] No real upstream response data
- [ ] All placeholder values clearly synthetic (e.g., `test-*`, `1700000000`)

### Git Diff Verification

- [ ] `git status --short` shows only expected files
- [ ] `git diff --stat` shows reasonable line counts
- [ ] `git diff --name-only` does NOT include:
  - `README.md` or `README.zh-CN.md`
  - `src/` directory files
  - `config/` directory files
  - `docker/` directory files
  - `extension/` directory files
  - `static/` directory files
  - `main.py`, `admin.py`, `database.py`
  - `requirements.txt`
  - `Dockerfile` or `Dockerfile.headed`
  - `docker-compose*.yml` files
  - `LICENSE`
  - Executable test files (`.py` test runners)
  - Fixture loader utilities

### Runtime Behavior

- [ ] No Python runtime source files modified
- [ ] No executable tests created (only static fixture data)
- [ ] No fixture loader utilities created
- [ ] No upstream service calls made
- [ ] No real credentials used

---

## Notes

- **This sprint creates sanitized static fixtures only.** No executable tests are implemented.
- **Fixtures are synthetic.** All data is clearly placeholder and does not represent real upstream responses.
- **Test harness deferred.** Fixture loader, assertion utilities, and test runner will be created in a future sprint.
- **Runtime capture deferred.** Capturing real upstream responses requires a separate sprint with sanitization review.
- **Fork remains unofficial.** No changes imply endorsement by upstream author or Google.

---

## Next Steps (Future Sprint)

1. Implement fixture loader utility (`tests/harness/fixture_loader.py`)
2. Implement shape assertion utilities (`tests/harness/shape_assertions.py`)
3. Create executable test files for FX-ML-001, FX-ON-001, FX-OS-003
4. Add sanitization checker utility
5. Expand fixtures to cover media generation (images, videos)
6. Add Gemini endpoint fixtures
7. Add error response fixtures
8. Consider runtime capture sprint with sanitization review
