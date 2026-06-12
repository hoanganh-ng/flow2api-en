# Sprint 004 — Generation Fixture Plan

## Sprint Goal

Create a documentation-only fixture plan for future generation compatibility tests.
Identify which endpoints, request shapes, response shapes, and streaming behaviors
are candidates for fixture-based verification. Classify fixtures by implementation
mode and priority. Design a future test harness approach.

This sprint does not implement tests, create real fixture data, or change runtime
behavior of any kind.

## Context

Prior sprints established:

- **Sprint 000** — English project-brain documentation baseline
- **Sprint 001** — Existing system map (architecture, entrypoints, config, risks)
- **Sprint 001A** — English surface audit of Chinese-language surfaces
- **Sprint 001B** — Safe README translation (English-first, original Chinese preserved)
- **Sprint 001C** — Conservative translation allowlist/denylist
- **Sprint 002** — API surface inventory (67 unique endpoints inventoried)
- **Sprint 003** — Generation contract deep dive (generation routes, streaming,
  model compatibility, request/response conversion)

Sprint 003 identified high-risk compatibility surfaces and unknowns that require
fixture-based verification. This sprint plans those fixtures without implementing
them.

## Scope

### In scope

- Review Sprint 002 and Sprint 003 documentation for fixture candidates
- Inspect source files only where needed to clarify fixture boundaries (read-only)
- Create `docs/GENERATION_FIXTURE_PLAN.md` — fixture design, categories,
  sanitization requirements, priorities, risks
- Create `docs/GENERATION_FIXTURE_MATRIX.md` — per-fixture detail table with
  19 planned fixtures across 11 surface categories
- Create `docs/TEST_HARNESS_PLAN.md` — future test harness approach, directory
  layout, naming conventions, mocking strategy, streaming comparison
- Create this sprint document (`docs/SPRINTS/SPRINT-004-generation-fixture-plan.md`)
- Update `docs/PROJECT_STATE.md` — mark Sprint 003 completed, Sprint 004 active
- Update `docs/SPRINTS/README.md` — add Sprint 004 to index

### Out of Scope

- Runtime behavior changes of any kind
- Source code modifications (Python, static, config, Docker, tests, scripts, etc.)
- Translation of any files
- Refactoring or feature additions
- Creating executable test harness code
- Creating captured real upstream response fixtures
- Creating fixture JSON files with real data
- Including real tokens, cookies, account identifiers, or upstream secrets
- Admin API fixture planning (deferred)
- WebSocket `/captcha_ws` fixture planning (deferred)
- Bypass, evasion, or upstream-protection avoidance instructions

## Files Changed

### Created

| File | Description |
|------|-------------|
| `docs/GENERATION_FIXTURE_PLAN.md` | Fixture design, categories, sanitization requirements, priorities, risks, recommended next sprint |
| `docs/GENERATION_FIXTURE_MATRIX.md` | 19 planned fixtures with per-fixture detail: endpoint, surface category, fixture mode, input/output shapes, compatibility risk, source references, sensitive data notes, test-harness priority |
| `docs/TEST_HARNESS_PLAN.md` | Future test harness approach: directory layout, naming conventions, secret avoidance, first slice, mock vs runtime-capture strategy, streaming comparison, compatibility assertions |
| `docs/SPRINTS/SPRINT-004-generation-fixture-plan.md` | This file |

### Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Marked Sprint 003 completed, Sprint 004 active, added Sprint 004 documents |
| `docs/SPRINTS/README.md` | Added Sprint 004 to sprint index, marked Sprint 003 completed |

## Source Files Inspected

Source files were inspected only where necessary to confirm fixture boundaries
already documented in Sprint 003. No source files were modified.

| File | Role |
|------|------|
| `src/api/routes.py` | Route entrypoints, normalization, response shaping, SSE streaming, conversion |
| `src/core/models.py` | Pydantic request/response models |
| `src/core/model_resolver.py` | Model alias and generationConfig-based resolution |
| `src/services/generation_handler.py` | MODEL_CONFIG registry, GenerationHandler, image/video pipelines |
| `src/services/flow_client.py` | Upstream Flow API client |

## Key Deliverables

- **19 planned fixtures** covering the highest-risk generation surfaces
- **11 surface categories** represented: model listing, model aliases, OpenAI
  non-streaming, OpenAI streaming, Gemini non-streaming, Gemini streaming,
  request normalization, response conversion, streaming conversion, error behavior,
  custom continuation
- **3 fixture modes** defined: static-doc-example (5), mocked-internal-response (14),
  runtime-capture-required (0 assigned IDs; 6 candidates identified in plan)
- **Priority tiers**: 6 priority-1 fixtures recommended for first test harness slice
- **Sanitization requirements** documented for all fixture types
- **Test harness directory layout** planned for future implementation
- **Streaming comparison strategy** documented for chunk-order-tolerant assertions

## Verification Checklist

- [x] No Python source files modified
- [x] No static/admin UI files modified
- [x] No config defaults modified
- [x] No Docker, compose, dependency, test, script, README, or LICENSE files modified
- [x] No translation performed
- [x] No refactoring or feature additions
- [x] No executable test harness code created
- [x] No fixture JSON files with real data created
- [x] No real tokens, cookies, account IDs, or upstream secrets included
- [x] `git diff --name-only` confirms only docs/ files changed
- [x] All documents use cautious wording ("planned fixture", "observed in source",
  "to be confirmed during fixture implementation", "runtime capture required")
- [x] No bypass, evasion, or upstream-protection avoidance instructions

## Note

This sprint is **documentation-only and planning-only**. All deliverables are
planning documents that guide future fixture and test harness implementation.
No runtime behavior has been changed or tested. No executable code has been created.
The fork remains clearly unofficial.
