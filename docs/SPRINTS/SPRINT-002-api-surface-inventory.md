# Sprint 002 — API Surface Inventory

| Field | Value |
|-------|-------|
| **Sprint ID** | 002 |
| **Name** | API Surface Inventory |
| **Status** | 🔄 Active |
| **Type** | Documentation-only |

---

## Sprint Goal

Create a comprehensive, source-verified inventory of every HTTP and WebSocket
endpoint exposed by flow2api-en. This inventory establishes the contract baseline
required before any refactor, rewrite, or compatibility test harness can be built.

---

## Scope

1. **Inspect source files** for route declarations, handlers, auth mechanisms,
   streaming behavior, and request/response models.

2. **Document the API surface** in three complementary views:
   - `API_SURFACE_INVENTORY.md` — detailed narrative inventory
   - `API_ENDPOINT_INDEX.md` — concise endpoint table with metadata
   - `API_COMPATIBILITY_NOTES.md` — compatibility-sensitive behavior observations

3. **Update project state documents** to reflect Sprint 001C completion and
   Sprint 002 activation.

---

## Out of Scope

- Runtime behavior changes of any kind
- Modification of Python source files
- Modification of static/admin UI files
- Modification of config defaults
- Modification of Docker, compose, dependencies, tests, scripts
- Modification of README.md or README.zh-CN.md
- Modification of LICENSE
- Translation of any text
- Refactoring, feature addition, or endpoint changes
- Contract extraction with request/response schemas (deferred to future sprint)
- Fixture-based verification (deferred to future sprint)
- Runtime testing of any endpoint

---

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `docs/API_SURFACE_INVENTORY.md` | Created | Detailed API surface narrative |
| `docs/API_ENDPOINT_INDEX.md` | Created | Concise endpoint table with categories, auth, streaming, risk |
| `docs/API_COMPATIBILITY_NOTES.md` | Created | Compatibility-sensitive behavior observations |
| `docs/SPRINTS/SPRINT-002-api-surface-inventory.md` | Created | This sprint document |
| `docs/PROJECT_STATE.md` | Updated | Sprint 001C completed, Sprint 002 active |
| `docs/SPRINTS/README.md` | Updated | Sprint index updated |

---

## Source Files Inspected

| File | Inspection Method |
|------|-------------------|
| `src/main.py` | Full read |
| `src/api/routes.py` | Full read |
| `src/api/admin.py` | Full read (2207 lines, multiple ranges) |
| `src/core/auth.py` | Full read |
| `src/core/models.py` | Full read |
| `src/core/monitoring.py` | Partial read (metrics setup) |
| `src/services/generation_handler.py` | Grep for `MODEL_CONFIG` |

Additional grep searches performed:
- `FastAPI|APIRouter|@app\.|@router\.|include_router|mount\(` across all `*.py`
- Route decorator patterns across `src/`

---

## Findings Summary

| Metric | Value |
|--------|-------|
| Total endpoints discovered | 67 |
| OpenAI-compatible endpoints | 3 |
| Gemini-compatible endpoints | 8 |
| Admin API endpoints | 47 |
| Extension / Captcha endpoints | 2 |
| Health/metrics endpoints | 2 |
| Static/UI endpoints | 5 |
| Highest-risk surfaces | OpenAI `/v1/chat/completions`, Gemini `generateContent`/`streamGenerateContent`, model listing |

---

## Verification Checklist

- [x] All route decorators in `src/api/routes.py` enumerated
- [x] All route decorators in `src/api/admin.py` enumerated
- [x] All app-level routes in `src/main.py` enumerated
- [x] Auth mechanisms documented for each endpoint category
- [x] Streaming behavior documented (SSE format, headers, termination)
- [x] Error response patterns documented
- [x] Compatibility-sensitive behavior identified
- [x] No Python source files modified
- [x] No static/UI files modified
- [x] No config files modified
- [x] No Docker/compose/dependency files modified
- [x] No README files modified
- [x] No test files modified
- [x] `git diff --name-only` shows only expected docs/ files

---

## Notes

- This sprint is **documentation-only**. No runtime behavior has been changed or tested.
- All observations use cautious language ("observed in source," "appears to")
  because they are based on static inspection, not runtime verification.
- Duplicate/aliased endpoint pairs have been noted but not yet confirmed as
  actively used by the existing frontend.
- The WebSocket message protocol for `/captcha_ws` and the exact generation handler
  output format are flagged as unknowns requiring deeper contract extraction.
