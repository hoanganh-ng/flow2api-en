# Sprint 001C — Safe Translation Allowlist

**Date:** 2025-06-11
**Status:** Complete
**Scope:** Audit and planning only. No translation was performed.

---

## Sprint Goal

Create a precise, conservative allowlist and denylist that classifies every remaining Chinese-language surface in the repository. This document guides future translation sprints so they do not accidentally change runtime behavior, break API contracts, or corrupt data.

---

## Scope

- Re-scan the repository for remaining Chinese/Han character surfaces after Sprint 001B.
- Classify each surface into one of three categories: allowed, requires careful sprint, or denied.
- Produce a file-by-file classification table.
- Update the Translation Plan and Project State to reflect Sprint 001C.
- Recommend the next translation sprint.

---

## Out of Scope

- Translating any Chinese text.
- Modifying Python source files.
- Modifying static/admin UI files.
- Modifying config defaults, keys, or values.
- Modifying Docker, compose, dependency, test, or script files.
- Modifying LICENSE.
- Translating source comments, docstrings, log messages, error strings, or UI text.
- Translating API response text, endpoint paths, model names, or provider names.
- Translating token, captcha, proxy, or session-related runtime strings.
- Adding features or removing upstream attribution.

---

## Files Changed

| File | Action |
|------|--------|
| `docs/TRANSLATION_ALLOWLIST.md` | Created — master allowlist/denylist classification |
| `docs/SPRINTS/SPRINT-001C-safe-translation-allowlist.md` | Created — this sprint document |
| `docs/TRANSLATION_PLAN.md` | Updated — added Sprint 001C as allowlist/planning step |
| `docs/PROJECT_STATE.md` | Updated — reflected Sprint 001B completed, Sprint 001C active |
| `docs/SPRINTS/README.md` | Updated — added Sprint 001C to sprint index |

**No other files were modified.**

---

## Key Findings

### Han Character Scan Results

- **Scan method:** Python script using Unicode Han range (`\u4e00–\u9fff`, `\u3400–\u4dbf`).
- **Excluded paths:** `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, build outputs, logs, binary files.
- **Result:** 34 files, ~2,406 lines containing Chinese characters.
- **After excluding `README.zh-CN.md`** (preserved intentionally, 260 lines): ~31 files, ~2,146 lines of actionable surface.

### Classification Summary

| Category | Files | Lines (approx.) | Description |
|----------|-------|-----------------|-------------|
| Allowed for next safe sprint | 8 items | ~22 | Dockerfile comments, .gitignore comment, config comments, docs references |
| Requires careful dedicated sprint | 25 files | ~2,035 | Source comments/docstrings, static UI, extension UI, test fixtures |
| Denied until contract decision | 12 surface groups | Interleaved with above | Runtime errors, logs, API text, config keys, model names, DB values, token/captcha/proxy strings |

### Highest-Risk Denied Surfaces

1. `src/api/admin.py` — RuntimeError messages with Chinese text may propagate to API responses.
2. `src/services/load_balancer.py` — Chinese error strings returned in runtime tuples.
3. `src/services/proxy_manager.py` — ValueError with Chinese validation text.
4. `src/services/file_cache.py` — User-facing Chinese error string.
5. `src/services/browser_captcha_personal.py` — Largest file (13,309 lines); runtime strings interleaved with comments.
6. `src/services/flow_client.py` — Upstream API interaction strings must not change.

---

## Verification Checklist

- [x] No Python source files were modified.
- [x] No static/admin UI files were modified.
- [x] No config files were modified.
- [x] No Docker, compose, dependency, test, or script files were modified.
- [x] No LICENSE file was modified.
- [x] No Chinese text was translated in this sprint.
- [x] `README.md` was not modified (already English from Sprint 001B).
- [x] `README.zh-CN.md` was not modified (preserved from Sprint 001B).
- [x] `git diff --name-only` confirms only docs/ files changed.
- [x] Han character scan confirms current Chinese surface locations.
- [x] All classifications are conservative — "deny for now" when uncertain.

---

## Note

This sprint is **audit and planning only**. No translation was performed. The allowlist created here is the authoritative reference for all future translation sprints. Each future sprint must consult [TRANSLATION_ALLOWLIST.md](../TRANSLATION_ALLOWLIST.md) before modifying any file.
