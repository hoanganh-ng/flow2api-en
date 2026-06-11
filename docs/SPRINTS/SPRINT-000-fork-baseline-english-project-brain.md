# SPRINT-000: Fork Baseline & English Project Brain

**Status**: In Progress
**Date**: 2026-06-11
**Type**: Documentation only

## Goal

Create a documentation-only fork baseline and English project brain. This sprint must not change runtime behavior.

## Scope

### In Scope

- Inspect the entire repository structure
- Create English documentation scaffolding
- Establish fork identity and principles
- Add a non-destructive English notice to README.md
- Preserve upstream license and attribution
- Document initial module boundary assumptions
- Document known high-risk areas
- Document migration roadmap stages
- Record initial ADR (Architecture Decision Record)

### Out of Scope

- Source code refactoring
- Dependency updates
- Formatting passes on runtime files
- Docker changes
- Config changes
- Endpoint changes
- Test behavior changes
- New runtime features
- Removal of existing Chinese docs/content
- Translation of source code comments

## Deliverables

### Created Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project brain — repository layout, tech stack, high-risk areas, key commands |
| `docs/PROJECT_STATE.md` | Fork identity, current state, documentation status |
| `docs/PRODUCT_OVERVIEW.md` | What the product does, API layers, deployment modes |
| `docs/ROADMAP.md` | 7-stage migration roadmap from docs to TypeScript rewrite |
| `docs/ARCHITECTURE.md` | System overview, runtime flow, data persistence, config flow |
| `docs/MODULE_BOUNDARIES.md` | 10 initial module boundaries with risk ratings |
| `docs/GLOSSARY.md` | Terms and abbreviations used in the project |
| `docs/UPSTREAM_BASELINE.md` | Upstream project info, repo structure, dependencies, unknowns |
| `docs/SECURITY_AND_COMPLIANCE.md` | Security considerations, licensing, anti-abuse statement |
| `docs/DECISIONS/ADR-0001-fork-principles.md` | Architecture Decision Record for fork principles |
| `docs/SPRINTS/README.md` | Sprint index and conventions |
| `docs/SPRINTS/SPRINT-000-fork-baseline-english-project-brain.md` | This document |

### Modified Files

| File | Change |
|------|--------|
| `README.md` | Additive English notice at top (no removal of existing content) |

## Constraints

- Preserve the original MIT license and attribution
- Make the fork clearly unofficial
- Do not change runtime behavior
- Do not change API behavior
- Do not change authentication, token refresh, captcha workflows, proxy behavior, generation behavior, Docker behavior, default configs, model lists, or admin UI behavior
- Do not design or implement anything for abuse, evasion, bypassing access controls, or avoiding upstream protections
- Treat token handling, captcha/browser behavior, proxy behavior, upstream client behavior, and generation request/response compatibility as high-risk areas

## Module Boundary Assumptions (Initial)

1. HTTP/API compatibility layer (`src/api/routes.py`)
2. Upstream Flow client behavior (`src/services/flow_client.py`)
3. Token/account lifecycle (`src/services/token_manager.py`, `src/core/account_tiers.py`)
4. Browser/captcha/session lifecycle (`src/services/browser_captcha*.py`, `extension/`)
5. Proxy/network configuration (`src/services/proxy_manager.py`)
6. Generation/media handling (`src/services/generation_handler.py`, `src/services/file_cache.py`)
7. Admin UI/static assets (`src/api/admin.py`, `static/`)
8. Config/persistence (`src/core/config.py`, `src/core/database.py`)
9. Observability (`src/core/monitoring.py`, `src/core/logger.py`)
10. Load balancing/concurrency (`src/services/load_balancer.py`, `src/services/concurrency_manager.py`)

## Known Unknowns

See [UPSTREAM_BASELINE.md](../UPSTREAM_BASELINE.md) for the full list of explicit unknowns requiring source analysis in later sprints.

## Verification Checklist

- [ ] `git diff --stat` shows only documentation files added + README notice
- [ ] `git diff --name-only` confirms no runtime files modified
- [ ] LICENSE file is preserved unchanged
- [ ] README.md has only additive changes
- [ ] No source code files in `src/`, `extension/`, `static/`, `tests/` are modified
- [ ] No Docker files are modified
- [ ] No config files are modified
- [ ] `requirements.txt` is unchanged

## Observations

- `admin.py` (2200+ lines) and `database.py` (1950+ lines) are the largest files — likely candidates for decomposition in future sprints
- The codebase has extensive Chinese comments throughout — these are intentional and should be preserved
- The extension directory contains a standalone Chrome extension (Manifest V3) with its own lifecycle
- Multiple docker-compose files support different deployment scenarios
- Test coverage is limited (6 test files, mostly focused on specific features)
- The `generation_handler.py` contains the master `MODEL_CONFIG` dictionary — this is the single source of truth for all supported models
