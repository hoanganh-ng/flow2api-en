# Sprint 001 — Existing System Map

| Field | Value |
|-------|-------|
| **Sprint** | 001 |
| **Name** | Existing System Map |
| **Status** | Active |
| **Predecessor** | [Sprint 000](SPRINT-000-fork-baseline-english-project-brain.md) (completed) |
| **Type** | Documentation-only |

## Goal

Create a documentation-only system map of the current repository based on actual source inspection. This provides the foundation for contract-first migration planning before any refactor or rewrite.

## Scope

### In Scope

- Inspect the repository structure and all Python source files.
- Document the top-level layout, major modules, and their observed responsibilities.
- Document application entrypoints, startup/shutdown behavior, and static serving.
- Map all configuration sources, precedence rules, and runtime settings.
- Identify high-risk areas and register them for deeper analysis in later sprints.
- Catalog current test coverage areas and gaps.
- Identify unknowns that require later contract extraction.

### Out of Scope

- Modifying any Python source files.
- Modifying frontend/static runtime assets.
- Modifying Docker, compose, config defaults, dependencies, tests, or scripts.
- Refactoring or translating source code comments.
- Changing any runtime behavior.
- Adding or removing features.
- Committing changes (commit is deferred to explicit user request).

## Constraints

- **No runtime behavior changes.** This sprint must not change authentication, token refresh, captcha workflows, proxy behavior, generation behavior, streaming behavior, model lists, upload behavior, or admin UI behavior.
- **Preserve license and attribution.** The fork remains clearly unofficial.
- **Source-based statements only.** Use cautious language ("observed in source", "appears to", "to be confirmed").
- **No secrets or bypass instructions.** Do not include real tokens or operational bypass instructions.

## Deliverables

| Document | Status | Description |
|----------|--------|-------------|
| `docs/SYSTEM_MAP.md` | ✅ Created | Top-level layout, module responsibilities, coupling analysis, runtime flows |
| `docs/ENTRYPOINTS.md` | ✅ Created | Startup entrypoints, FastAPI app, lifespan, Docker, API endpoints |
| `docs/CONFIGURATION_MAP.md` | ✅ Created | Config files, TOML sections, DB persistence, proxy/token/admin config |
| `docs/RISK_REGISTER.md` | ✅ Created | 11 high-risk areas with source areas, preservation requirements, sprint targets |
| `docs/PROJECT_STATE.md` | ✅ Updated | Sprint 000 marked completed, Sprint 001 marked active |
| `docs/SPRINTS/README.md` | ✅ Updated | Sprint index updated with Sprint 001 |
| `docs/SPRINTS/SPRINT-001-existing-system-map.md` | ✅ Created | This document |

## Key Findings

### Largest Files

| File | Lines | % of Total |
|------|-------|-----------|
| `browser_captcha_personal.py` | 13,309 | 40.8% |
| `flow_client.py` | 3,123 | 9.6% |
| `generation_handler.py` | 2,467 | 7.6% |
| `admin.py` | 2,207 | 6.8% |
| `browser_captcha.py` | 2,122 | 6.5% |
| `database.py` | 1,950 | 6.0% |

### Architecture Observations

- **Monolithic Python application** with FastAPI as the web framework.
- **SQLite** for persistence (no external database dependency).
- **TOML** for initial configuration, **database** for runtime configuration.
- **Three browser captcha implementations** (Playwright headed, nodriver personal, Chrome extension bridge).
- **Dual API compatibility**: OpenAI and Gemini request/response formats.
- **Complex concurrency model**: soft limits, hard limits, pending tracking, stagger delays.

### Biggest Risks Discovered

1. **R-03: Captcha/browser subsystem** — 13,309 lines in a single file; most complex and fragile part of the system.
2. **R-01: Upstream client** — sole interface with Google APIs; 3,123 lines with inline request shapes (observed in source).
3. **R-08: Admin security** — credentials appear stored without hashing; CORS configured as wildcard; in-memory sessions (observed in source; to be confirmed).
4. **R-11: Test coverage** — edge-case-only testing; no integration or contract tests.

### Unknowns Needing Later Contract Extraction

- Complete upstream API request/response schemas.
- Full admin API endpoint inventory.
- Exact streaming SSE chunk schemas.
- Database schema completeness and migration history.
- Extension WebSocket message protocol.
- Error taxonomy across all subsystems.

## Verification Checklist

- [x] Repository structure inspected (`find`, `wc -l`).
- [x] All major Python source files read and analyzed.
- [x] `docs/SYSTEM_MAP.md` created with source-based content.
- [x] `docs/ENTRYPOINTS.md` created with source-based content.
- [x] `docs/CONFIGURATION_MAP.md` created with source-based content.
- [x] `docs/RISK_REGISTER.md` created with 11 risk entries.
- [x] `docs/PROJECT_STATE.md` updated (Sprint 000 completed, Sprint 001 active).
- [x] `docs/SPRINTS/README.md` updated (sprint index).
- [x] Git diff confirmed: only documentation files changed.
- [x] No Python source files modified.
- [x] No runtime assets modified.
- [x] No Docker/compose/config/dependency files modified.
- [x] Fork remains clearly unofficial.
- [x] License and attribution preserved.
