# Sprint 005B — Fixture Loader & Shape Assertions

> **Status:** 🔄 Active
> **Scope:** Test-only — offline static fixture shape assertions
> **Runtime impact:** None — no runtime source files are modified

---

## Sprint Goal

Add minimal test-only fixture loading and shape assertion tests for the three
static fixtures created in Sprint 005A (FX-ML-001, FX-ON-001, FX-OS-003).
Tests are offline, deterministic, and independent of upstream services.

---

## Context

Sprint 005A created the first sanitized static generation fixture skeleton:

| Fixture ID | File | Description |
|------------|------|-------------|
| FX-ML-001 | `tests/fixtures/generation/model-list/openai-model-list.json` | GET /v1/models response shape |
| FX-ON-001 | `tests/fixtures/generation/openai-non-streaming/text-basic-request.json` | Non-streaming chat request shape |
| FX-ON-001 | `tests/fixtures/generation/openai-non-streaming/text-basic-response.json` | Non-streaming chat response shape |
| FX-OS-003 | `tests/fixtures/generation/openai-streaming/done-termination.sse.txt` | SSE [DONE] termination shape |

Sprint 005B turns these static fixtures into the first tiny executable
compatibility safety net.

---

## Scope

### Included

- `tests/compatibility/helpers/fixture_loader.py` — standard-library-only
  fixture loader using `pathlib` and `json`
- `tests/compatibility/helpers/shape_assertions.py` — shallow structural
  assertion helpers for the four fixture shapes
- `tests/compatibility/test_static_generation_fixtures.py` — executable
  `unittest.TestCase` tests for all three Sprint 005A fixtures
- `tests/compatibility/README.md` — directory-level documentation
- `docs/SPRINTS/SPRINT-005B-fixture-loader-shape-assertions.md` — this document
- Updates to `docs/PROJECT_STATE.md`, `docs/SPRINTS/README.md`,
  `docs/TEST_HARNESS_PLAN.md`, `docs/GENERATION_FIXTURE_MATRIX.md`

### Out of Scope

- Modifying any Python runtime source files under `src/`
- Modifying static/admin UI files
- Modifying config defaults
- Modifying Docker, compose, dependencies, scripts, README, or LICENSE files
- Importing or starting the FastAPI application
- Calling upstream services
- Capturing real upstream responses
- Adding new fixture files beyond the three Sprint 005A fixtures
- Route-level behavior tests (future sprint)
- Mocked handler output tests (future sprint)
- Any translation work

---

## Files Changed

### Created

| File | Purpose |
|------|---------|
| `tests/compatibility/__init__.py` | Package init |
| `tests/compatibility/helpers/__init__.py` | Helpers sub-package init |
| `tests/compatibility/helpers/fixture_loader.py` | JSON and text fixture loader (stdlib only) |
| `tests/compatibility/helpers/shape_assertions.py` | Shallow shape assertion helpers |
| `tests/compatibility/test_static_generation_fixtures.py` | Executable unittest tests |
| `tests/compatibility/README.md` | Directory documentation |
| `docs/SPRINTS/SPRINT-005B-fixture-loader-shape-assertions.md` | This sprint document |

### Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Sprint 005A marked completed; Sprint 005B marked active |
| `docs/SPRINTS/README.md` | Sprint 005B added to index |
| `docs/TEST_HARNESS_PLAN.md` | Sprint 005B noted as first static fixture shape assertion step |
| `docs/GENERATION_FIXTURE_MATRIX.md` | FX-ML-001, FX-ON-001, FX-OS-003 marked with static shape assertions |

---

## Verification Checklist

- [ ] JSON fixtures validate (`python -m json.tool` on each)
- [ ] `python -m unittest tests.compatibility.test_static_generation_fixtures` passes
- [ ] No runtime files under `src/` are modified
- [ ] No config, Docker, compose, dependency, or README files are modified
- [ ] No real tokens, secrets, cookies, or account IDs in any new file
- [ ] `git diff --name-only` shows only the files listed above
- [ ] Tests are offline (no network access) and deterministic

---

## Notes

- This sprint adds **offline static fixture shape assertions only**.
- Route-level tests that import the FastAPI app and exercise HTTP routes
  remain future work and will require a separate sprint with its own scope
  and constraints review.
- The existing test convention in this repository uses `unittest.TestCase`,
  so the new tests follow the same style for consistency.
- The fixture loader resolves paths relative to the repository root using a
  robust ancestor-search strategy, so tests can be run from any working
  directory.
