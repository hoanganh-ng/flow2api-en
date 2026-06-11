# PROJECT_STATE.md

## Fork Identity

| Field | Value |
|-------|-------|
| **Fork name** | flow2api-en |
| **Upstream** | [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api) |
| **Upstream license** | MIT (Copyright © 2025 TheSmallHanCat) |
| **Fork status** | Unofficial — not endorsed by upstream author |
| **Current sprint** | Sprint 001 — Existing System Map |

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

## What Is Not Yet Done

- Source-level module documentation (inline English comments)
- API contract specification with request/response schemas
- Test harness / compatibility fixtures
- Rewrite scaffolding

## Sprint History

| Sprint | Status | Description |
|--------|--------|-------------|
| Sprint 000 — Fork baseline and English project brain | ✅ Completed | Documentation baseline and English project brain created |
| Sprint 001 — Existing System Map | 🔄 Active | Source-based system map, entrypoints, config map, risk register |

## Next Steps

See [ROADMAP.md](ROADMAP.md) for the full migration roadmap.
See [SPRINT-000](SPRINTS/SPRINT-000-fork-baseline-english-project-brain.md) for the baseline sprint.
See [SPRINT-001](SPRINTS/SPRINT-001-existing-system-map.md) for the current sprint.
