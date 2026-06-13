# Sprints

This directory contains sprint planning and retrospective documents for the flow2api-en fork.

## Sprint Index

| Sprint | Name | Status | Description |
|--------|------|--------|-------------|
| [000](SPRINT-000-fork-baseline-english-project-brain.md) | Fork Baseline & English Project Brain | ✅ Completed | Documentation-only fork baseline, no runtime changes |
| [001](SPRINT-001-existing-system-map.md) | Existing System Map | ✅ Completed | Source-based system map, entrypoints, config map, risk register |
| [001A](SPRINT-001A-english-surface-audit.md) | English Surface Audit | ✅ Completed | Audit of Chinese-language surfaces, translation plan (audit-only) |
| [001B](SPRINT-001B-safe-readme-translation.md) | Safe README Translation | ✅ Completed | English README created, original Chinese preserved as README.zh-CN.md |
| [001C](SPRINT-001C-safe-translation-allowlist.md) | Safe Translation Allowlist | ✅ Completed | Translation allowlist/denylist created; classified all remaining Chinese surfaces |
| [002](SPRINT-002-api-surface-inventory.md) | API Surface Inventory | ✅ Completed | Documentation-only inventory of HTTP/WS API surface from source inspection |
| [003](SPRINT-003-generation-contract-deep-dive.md) | Generation Contract Deep Dive | ✅ Completed | Documentation-only deep dive of generation contract from source inspection |
| [004](SPRINT-004-generation-fixture-plan.md) | Generation Fixture Plan | ✅ Completed | Documentation-only fixture plan for future generation compatibility tests |
| [005A](SPRINT-005A-static-generation-fixture-skeleton.md) | Static Generation Fixture Skeleton | ✅ Completed | First sanitized static fixture skeleton (FX-ML-001, FX-ON-001, FX-OS-003) |
| [005B](SPRINT-005B-fixture-loader-shape-assertions.md) | Fixture Loader & Shape Assertions | ✅ Completed | Offline static fixture shape assertions for Sprint 005A fixtures |
| [005C](SPRINT-005C-additional-static-generation-fixtures.md) | Additional Static Generation Fixtures | ✅ Completed | Additional sanitized static fixture files (FX-ON-002, FX-GN-001, FX-OS-002) |
| [005D](SPRINT-005D-additional-static-fixture-assertions.md) | Additional Static Fixture Assertions | ✅ Completed | Offline static shape assertions for Sprint 005C fixtures |
| [006A](SPRINT-006A-route-test-seam-discovery.md) | Route Test Seam Discovery | ✅ Completed | Discovery-only analysis of safest route-level test seams |
| [006B](SPRINT-006B-conversion-layer-unit-tests.md) | Conversion-Layer Unit Tests | ✅ Completed | 67 unit tests for 7 pure conversion helpers in `src.api.routes` |
| [006C](SPRINT-006C-model-catalog-read-only-route-characterization.md) | Model Catalog & Read-Only Route Characterization | ✅ Completed | 95 unit tests for model catalog helpers and read-only model route functions |
| [006D](SPRINT-006D-mocked-generation-route-seam-discovery.md) | Mocked Generation Route Seam Discovery | ✅ Completed | Discovery-only documentation of generation route dependencies and mocking plan |

## Sprint Conventions

- Each sprint document describes scope, deliverables, constraints, and verification steps
- Sprints must not change runtime behavior unless explicitly scoped
- High-risk areas require explicit sprint scope before modification
- Sprint documents are immutable once accepted (create a new sprint for corrections)
