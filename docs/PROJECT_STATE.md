# PROJECT_STATE.md

## Fork Identity

| Field | Value |
|-------|-------|
| **Fork name** | flow2api-en |
| **Upstream** | [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api) |
| **Upstream license** | MIT (Copyright © 2025 TheSmallHanCat) |
| **Fork status** | Unofficial — not endorsed by upstream author |
| **Current sprint** | Sprint 002 — API Surface Inventory |

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

## What Is Not Yet Done

- Source-level module documentation (inline English comments)
- API contract specification with full request/response schemas (Sprint 002 inventory is path-level only)
- Test harness / compatibility fixtures
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
| Sprint 002 — API Surface Inventory | 🔄 Active | Documentation-only inventory of HTTP/WS API surface from source inspection |

## Next Steps

See [ROADMAP.md](ROADMAP.md) for the full migration roadmap.
See [SPRINT-000](SPRINTS/SPRINT-000-fork-baseline-english-project-brain.md) for the baseline sprint.
See [SPRINT-001](SPRINTS/SPRINT-001-existing-system-map.md) for the completed system map sprint.
See [SPRINT-001A](SPRINTS/SPRINT-001A-english-surface-audit.md) for the completed audit sprint.
See [SPRINT-001B](SPRINTS/SPRINT-001B-safe-readme-translation.md) for the completed README translation sprint.
See [SPRINT-001C](SPRINTS/SPRINT-001C-safe-translation-allowlist.md) for the completed translation allowlist sprint.
See [SPRINT-002](SPRINTS/SPRINT-002-api-surface-inventory.md) for the current API surface inventory sprint.
See [TRANSLATION_PLAN.md](TRANSLATION_PLAN.md) for the phased translation approach.
See [TRANSLATION_ALLOWLIST.md](TRANSLATION_ALLOWLIST.md) for the authoritative translation classification.
See [API_SURFACE_INVENTORY.md](API_SURFACE_INVENTORY.md) for the detailed API surface inventory.
See [API_ENDPOINT_INDEX.md](API_ENDPOINT_INDEX.md) for the concise endpoint table.
See [API_COMPATIBILITY_NOTES.md](API_COMPATIBILITY_NOTES.md) for compatibility-sensitive behavior observations.
