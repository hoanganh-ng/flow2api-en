# PROJECT_STATE.md

## Fork Identity

| Field | Value |
|-------|-------|
| **Fork name** | flow2api-en |
| **Upstream** | [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api) |
| **Upstream license** | MIT (Copyright © 2025 TheSmallHanCat) |
| **Fork status** | Unofficial — not endorsed by upstream author |
| **Current sprint** | Sprint 006F — Mocked OpenAI Image-Result Route Contract |

## Purpose

This fork exists to:

1. Provide an English-language documentation and planning layer over the upstream project.
2. Create a structured knowledge base for understanding the system before any rewrite.
3. Serve as the planning workspace for a potential future TypeScript/Node.js rewrite.

## Current Principles

- **No runtime behavior changes** in Sprint 000 or Sprint 001.
- **Upstream compatibility** is preserved unless a future sprint explicitly documents a deviation.
- **Original license and attribution** are retained.
- **Chinese source comments and docs** are left in place; English documentation is additive.
- **Translation status:** The project is English-documented (project brain, system map, sprint plans, root README). A translation allowlist has been created (Sprint 001C) classifying all remaining Chinese surfaces. Source code, UI, logs, and config comments have not yet been translated. See [TRANSLATION_PLAN.md](TRANSLATION_PLAN.md) for the phased approach and [TRANSLATION_ALLOWLIST.md](TRANSLATION_ALLOWLIST.md) for the authoritative classification.

## What Is Documented So Far

| Document | Status |
|----------|--------|
| CLAUDE.md (project brain) | Created |
| docs/PROJECT_STATE.md | Created |
| docs/PRODUCT_OVERVIEW.md | Created |
| docs/ROADMAP.md | Created |
| docs/ARCHITECTURE.md | Created |
| docs/MODULE_BOUNDARIES.md | Created |
| docs/GLOSSARY.md | Created |
| docs/UPSTREAM_BASELINE.md | Created |
| docs/SECURITY_AND_COMPLIANCE.md | Created |
| docs/DECISIONS/ADR-0001-fork-principles.md | Created |
| docs/SPRINTS/README.md | Created |
| docs/SPRINTS/SPRINT-000-fork-baseline-english-project-brain.md | Created |
| docs/SYSTEM_MAP.md | Created (Sprint 001) |
| docs/ENTRYPOINTS.md | Created (Sprint 001) |
| docs/CONFIGURATION_MAP.md | Created (Sprint 001) |
| docs/RISK_REGISTER.md | Created (Sprint 001) |
| docs/SPRINTS/SPRINT-001-existing-system-map.md | Created (Sprint 001) |
| docs/ENGLISH_SURFACE_AUDIT.md | Created (Sprint 001A) |
| docs/TRANSLATION_PLAN.md | Created (Sprint 001A), updated (Sprint 001B) |
| docs/SPRINTS/SPRINT-001A-english-surface-audit.md | Created (Sprint 001A) |
| README.zh-CN.md | Created (Sprint 001B) — original Chinese README preserved |
| README.md | Replaced (Sprint 001B) — English-first README |
| docs/SPRINTS/SPRINT-001B-safe-readme-translation.md | Created (Sprint 001B) |
| docs/TRANSLATION_ALLOWLIST.md | Created (Sprint 001C) — translation allowlist/denylist |
| docs/SPRINTS/SPRINT-001C-safe-translation-allowlist.md | Created (Sprint 001C) |
| docs/API_SURFACE_INVENTORY.md | Created (Sprint 002) — detailed API surface narrative |
| docs/API_ENDPOINT_INDEX.md | Created (Sprint 002) — endpoint table with categories, auth, risk |
| docs/API_COMPATIBILITY_NOTES.md | Created (Sprint 002) — compatibility-sensitive behavior observations |
| docs/SPRINTS/SPRINT-002-api-surface-inventory.md | Created (Sprint 002) |
| docs/GENERATION_CONTRACT.md | Created (Sprint 003) — generation route contract deep dive |
| docs/STREAMING_CONTRACT_NOTES.md | Created (Sprint 003) — streaming behavior observations |
| docs/MODEL_COMPATIBILITY_MAP.md | Created (Sprint 003) — model naming, aliases, and resolution |
| docs/REQUEST_RESPONSE_CONVERSION_MAP.md | Created (Sprint 003) — OpenAI/Gemini conversion boundaries |
| docs/SPRINTS/SPRINT-003-generation-contract-deep-dive.md | Created (Sprint 003) |
| docs/GENERATION_FIXTURE_PLAN.md | Created (Sprint 004) — fixture design, categories, priorities, risks |
| docs/GENERATION_FIXTURE_MATRIX.md | Created (Sprint 004) — 19 planned fixtures with per-fixture detail |
| docs/TEST_HARNESS_PLAN.md | Created (Sprint 004) — future test harness approach and strategy |
| docs/SPRINTS/SPRINT-004-generation-fixture-plan.md | Created (Sprint 004) |
| tests/fixtures/README.md | Created (Sprint 005A) — fixture directory purpose and sanitization policy |
| tests/fixtures/generation/README.md | Created (Sprint 005A) — generation fixture scope and per-fixture docs |
| tests/fixtures/generation/model-list/openai-model-list.json | Created (Sprint 005A) — FX-ML-001 skeleton |
| tests/fixtures/generation/openai-non-streaming/text-basic-request.json | Created (Sprint 005A) — FX-ON-001 request skeleton |
| tests/fixtures/generation/openai-non-streaming/text-basic-response.json | Created (Sprint 005A) — FX-ON-001 response skeleton |
| tests/fixtures/generation/openai-streaming/done-termination.sse.txt | Created (Sprint 005A) — FX-OS-003 skeleton |
| docs/SPRINTS/SPRINT-005A-static-generation-fixture-skeleton.md | Created (Sprint 005A) |
| tests/compatibility/helpers/fixture_loader.py | Created (Sprint 005B) — JSON/text fixture loader (stdlib only) |
| tests/compatibility/helpers/shape_assertions.py | Created (Sprint 005B) — shallow shape assertion helpers |
| tests/compatibility/test_static_generation_fixtures.py | Created (Sprint 005B) — offline static fixture shape tests |
| tests/compatibility/README.md | Created (Sprint 005B) — compatibility test directory documentation |
| docs/SPRINTS/SPRINT-005B-fixture-loader-shape-assertions.md | Created (Sprint 005B) |
| tests/fixtures/generation/openai-non-streaming/image-result-request.json | Created (Sprint 005C) — FX-ON-002 request |
| tests/fixtures/generation/openai-non-streaming/image-result-response.json | Created (Sprint 005C) — FX-ON-002 response |
| tests/fixtures/generation/gemini-non-streaming/text-basic-request.json | Created (Sprint 005C) — FX-GN-001 request |
| tests/fixtures/generation/gemini-non-streaming/text-basic-response.json | Created (Sprint 005C) — FX-GN-001 response |
| tests/fixtures/generation/openai-streaming/reasoning-progress.sse.txt | Created (Sprint 005C) — FX-OS-002 |
| docs/SPRINTS/SPRINT-005C-additional-static-generation-fixtures.md | Created (Sprint 005C) |
| docs/SPRINTS/SPRINT-005D-additional-static-fixture-assertions.md | Created (Sprint 005D) |
| docs/ROUTE_TEST_SEAM_DISCOVERY.md | Created (Sprint 006A) — route test seam analysis |
| docs/GENERATION_ROUTE_TEST_PLAN.md | Created (Sprint 006A) — proposed route-level test plan |
| docs/SPRINTS/SPRINT-006A-route-test-seam-discovery.md | Created (Sprint 006A) |
| tests/compatibility/test_route_conversion_helpers.py | Created (Sprint 006B) — 67 unit tests for 7 route conversion helpers |
| docs/SPRINTS/SPRINT-006B-conversion-layer-unit-tests.md | Created (Sprint 006B) |
| tests/compatibility/test_model_catalog_routes.py | Created (Sprint 006C) — 95 unit tests for model catalog helpers and read-only routes |
| docs/SPRINTS/SPRINT-006C-model-catalog-read-only-route-characterization.md | Created (Sprint 006C) |
| docs/GENERATION_ROUTE_DEPENDENCY_MAP.md | Created (Sprint 006D) — route signatures and dependency chains |
| docs/GENERATION_ROUTE_MOCKING_PLAN.md | Created (Sprint 006D) — fake-handler interface and test matrix |
| docs/SPRINTS/SPRINT-006D-mocked-generation-route-seam-discovery.md | Created (Sprint 006D) |
| tests/compatibility/test_generation_routes_non_streaming.py | Created (Sprint 006E) — 6 mocked non-streaming generation route tests |
| docs/SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md | Created (Sprint 006E) |
| tests/compatibility/test_generation_route_image_result.py | Created (Sprint 006F) — 5 mocked image-result route tests |
| docs/SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md | Created (Sprint 006F) |

## What Is Not Yet Done

- Source-level module documentation (inline English comments)
- API contract specification with full request/response schemas (Sprint 002 inventory is path-level only)
- Executable test harness / fixture loader / assertion utilities — Sprint 005B added first offline static shape assertions; Sprint 005C added additional fixture files; Sprint 005D added static shape assertions for Sprint 005C fixtures; Sprint 006A discovered safe route-level test seams; Sprint 006B added 67 conversion-layer unit tests importing `src.api.routes`; Sprint 006C added 95 model catalog and read-only route characterization tests; Sprint 006D documented generation route dependency maps and mocking plan; Sprint 006E added 6 mocked non-streaming generation route tests with fake handler; Sprint 006F added 5 mocked image-result route tests; streaming and media route tests remain future work
- Rewrite scaffolding
- Runtime strings, UI text, log messages, error strings — not yet translated; classified in [TRANSLATION_ALLOWLIST.md](TRANSLATION_ALLOWLIST.md)

## Sprint History

| Sprint | Status | Description |
|--------|--------|-------------|
| Sprint 000 — Fork baseline and English project brain | ✅ Completed | Documentation baseline and English project brain created |
| Sprint 001 — Existing System Map | ✅ Completed | Source-based system map, entrypoints, config map, risk register |
| Sprint 001A — English Surface Audit | ✅ Completed | Audit of Chinese-language surfaces, translation plan (audit-only) |
| Sprint 001B — Safe README Translation | ✅ Completed | English README created, original Chinese preserved as README.zh-CN.md |
| Sprint 001C — Safe Translation Allowlist | ✅ Completed | Translation allowlist/denylist created; classified all remaining Chinese surfaces |
| Sprint 002 — API Surface Inventory | ✅ Completed | Documentation-only inventory of HTTP/WS API surface from source inspection |
| Sprint 003 — Generation Contract Deep Dive | ✅ Completed | Documentation-only deep dive of generation contract from source inspection |
| Sprint 004 — Generation Fixture Plan | ✅ Completed | Documentation-only fixture plan for future generation compatibility tests |
| Sprint 005A — Static Generation Fixture Skeleton | ✅ Completed | First sanitized static fixture skeleton (FX-ML-001, FX-ON-001, FX-OS-003) |
| Sprint 005B — Fixture Loader & Shape Assertions | ✅ Completed | Offline static fixture shape assertions for Sprint 005A fixtures |
| Sprint 005C — Additional Static Generation Fixtures | ✅ Completed | Additional sanitized static fixture files (FX-ON-002, FX-GN-001, FX-OS-002) |
| Sprint 005D — Additional Static Fixture Assertions | ✅ Completed | Offline static shape assertions for Sprint 005C fixtures |
| Sprint 006A — Route Test Seam Discovery | ✅ Completed | Discovery-only analysis of safest route-level test seams |
| Sprint 006B — Conversion-Layer Unit Tests | ✅ Completed | 67 unit tests for 7 pure conversion helpers in `src.api.routes` |
| Sprint 006C — Model Catalog and Read-Only Route Characterization | ✅ Completed | 95 unit tests for model catalog helpers and read-only model route functions |
| Sprint 006D — Mocked Generation Route Seam Discovery | ✅ Completed | Discovery-only documentation of generation route dependencies and mocking plan |
| Sprint 006E — Mocked Non-Streaming Generation Route Tests | ✅ Completed | 6 mocked non-streaming generation route tests with fake handler |
| Sprint 006F — Mocked OpenAI Image-Result Route Contract | ✅ Completed | 5 mocked image-result route tests with network/media helper guards |

## Next Steps

See [ROADMAP.md](ROADMAP.md) for the full migration roadmap.
See [SPRINT-000](SPRINTS/SPRINT-000-fork-baseline-english-project-brain.md) for the baseline sprint.
See [SPRINT-001](SPRINTS/SPRINT-001-existing-system-map.md) for the completed system map sprint.
See [SPRINT-001A](SPRINTS/SPRINT-001A-english-surface-audit.md) for the completed audit sprint.
See [SPRINT-001B](SPRINTS/SPRINT-001B-safe-readme-translation.md) for the completed README translation sprint.
See [SPRINT-001C](SPRINTS/SPRINT-001C-safe-translation-allowlist.md) for the completed translation allowlist sprint.
See [SPRINT-002](SPRINTS/SPRINT-002-api-surface-inventory.md) for the completed API surface inventory sprint.
See [SPRINT-003](SPRINTS/SPRINT-003-generation-contract-deep-dive.md) for the completed generation contract deep dive sprint.
See [SPRINT-004](SPRINTS/SPRINT-004-generation-fixture-plan.md) for the completed generation fixture plan sprint.
See [SPRINT-005A](SPRINTS/SPRINT-005A-static-generation-fixture-skeleton.md) for the completed static generation fixture skeleton sprint.
See [SPRINT-005B](SPRINTS/SPRINT-005B-fixture-loader-shape-assertions.md) for the completed fixture loader and shape assertions sprint.
See [SPRINT-005C](SPRINTS/SPRINT-005C-additional-static-generation-fixtures.md) for the completed additional static generation fixtures sprint.
See [SPRINT-005D](SPRINTS/SPRINT-005D-additional-static-fixture-assertions.md) for the completed additional static fixture assertions sprint.
See [SPRINT-006A](SPRINTS/SPRINT-006A-route-test-seam-discovery.md) for the completed route test seam discovery sprint.
See [SPRINT-006B](SPRINTS/SPRINT-006B-conversion-layer-unit-tests.md) for the completed conversion-layer unit tests sprint.
See [SPRINT-006C](SPRINTS/SPRINT-006C-model-catalog-read-only-route-characterization.md) for the completed model catalog and read-only route characterization sprint.
See [SPRINT-006D](SPRINTS/SPRINT-006D-mocked-generation-route-seam-discovery.md) for the completed mocked generation route seam discovery sprint.
See [SPRINT-006E](SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md) for the completed mocked non-streaming generation route tests sprint.
See [SPRINT-006F](SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md) for the completed mocked OpenAI image-result route contract sprint.
See [ROUTE_TEST_SEAM_DISCOVERY.md](ROUTE_TEST_SEAM_DISCOVERY.md) for the route test seam analysis.
See [GENERATION_ROUTE_TEST_PLAN.md](GENERATION_ROUTE_TEST_PLAN.md) for the proposed route-level test plan.
See [TRANSLATION_PLAN.md](TRANSLATION_PLAN.md) for the phased translation approach.
See [TRANSLATION_ALLOWLIST.md](TRANSLATION_ALLOWLIST.md) for the authoritative translation classification.
See [API_SURFACE_INVENTORY.md](API_SURFACE_INVENTORY.md) for the detailed API surface inventory.
See [API_ENDPOINT_INDEX.md](API_ENDPOINT_INDEX.md) for the concise endpoint table.
See [API_COMPATIBILITY_NOTES.md](API_COMPATIBILITY_NOTES.md) for compatibility-sensitive behavior observations.
See [GENERATION_CONTRACT.md](GENERATION_CONTRACT.md) for the generation contract deep dive.
See [STREAMING_CONTRACT_NOTES.md](STREAMING_CONTRACT_NOTES.md) for streaming behavior observations.
See [MODEL_COMPATIBILITY_MAP.md](MODEL_COMPATIBILITY_MAP.md) for model naming and resolution details.
See [REQUEST_RESPONSE_CONVERSION_MAP.md](REQUEST_RESPONSE_CONVERSION_MAP.md) for OpenAI/Gemini conversion boundaries.
See [GENERATION_FIXTURE_PLAN.md](GENERATION_FIXTURE_PLAN.md) for the fixture design and prioritization plan.
See [GENERATION_FIXTURE_MATRIX.md](GENERATION_FIXTURE_MATRIX.md) for the per-fixture detail matrix (3 skeletons created in Sprint 005A; static shape assertions added in Sprint 005B; 3 additional fixture files added in Sprint 005C; static shape assertions for Sprint 005C fixtures added in Sprint 005D; 6 mocked non-streaming route tests added in Sprint 006E; 5 mocked image-result route tests added in Sprint 006F).
See [TEST_HARNESS_PLAN.md](TEST_HARNESS_PLAN.md) for the planned test harness approach.
See [GENERATION_ROUTE_DEPENDENCY_MAP.md](GENERATION_ROUTE_DEPENDENCY_MAP.md) for generation route signatures and dependency chains.
See [GENERATION_ROUTE_MOCKING_PLAN.md](GENERATION_ROUTE_MOCKING_PLAN.md) for the fake-handler interface and test matrix.
See [SPRINT-006E](SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md) for the completed mocked non-streaming generation route tests sprint.
See [SPRINT-006F](SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md) for the completed mocked OpenAI image-result route contract sprint.
