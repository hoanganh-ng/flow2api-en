# Sprint 001B — Safe README Translation

**Status:** Active
**Date:** 2025-06-11
**Type:** Documentation-only (no runtime changes)

---

## Sprint Goal

Make the repository English-friendly at the README level while preserving the original Chinese README content and avoiding all runtime behavior changes.

## Scope

- Translate the root `README.md` into English.
- Preserve the original Chinese README as `README.zh-CN.md`.
- Update `docs/TRANSLATION_PLAN.md` to reflect README translation completion.
- Update `docs/PROJECT_STATE.md` and `docs/SPRINTS/README.md` to reflect sprint status.
- All prose translations are cautious: "Based on upstream README", "Observed during source mapping", "To be confirmed during API contract extraction".

## Out of Scope

- Python source files (`src/`)
- Static/admin UI files (`static/`)
- Configuration defaults (`config/`)
- Docker, compose, dependencies, tests, scripts, LICENSE
- Source comments translation
- UI text translation
- Log/error/API response text translation
- Config key, endpoint path, model name, provider name translation
- Token/captcha/proxy/session-related runtime strings
- Any change that may affect runtime behavior

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Modified | Replaced with English-first README |
| `README.zh-CN.md` | Created | Faithful copy of original Chinese README |
| `docs/TRANSLATION_PLAN.md` | Modified | Marked README translation as completed (Sprint 001B) |
| `docs/SPRINTS/SPRINT-001B-safe-readme-translation.md` | Created | This sprint document |
| `docs/PROJECT_STATE.md` | Modified | Updated sprint status and document table |
| `docs/SPRINTS/README.md` | Modified | Added Sprint 001B to sprint index |

## Verification Checklist

- [x] `README.zh-CN.md` preserves the previous `README.md` content faithfully
- [x] `README.md` is English-first
- [x] No runtime strings were translated
- [x] No UI strings were translated
- [x] No source comments were translated
- [x] Config keys, endpoint paths, model names, provider names, and command snippets were preserved exactly
- [x] All Docker commands, environment variables, and code blocks remain unchanged
- [x] Upstream attribution and license notice preserved
- [x] Fork clearly marked as unofficial
- [x] No instructions for abuse, evasion, or bypassing access controls added
- [x] `docs/TRANSLATION_PLAN.md` updated to reflect Sprint 001B completion
- [x] `docs/PROJECT_STATE.md` updated with Sprint 001B status
- [x] `docs/SPRINTS/README.md` updated with Sprint 001B entry
- [x] Git diff confirms only README and docs files changed (no `src/`, `config/`, `docker/`, `extension/`, `static/`, `tests/`, `main.py`, `requirements.txt`, `Dockerfile*`, `docker-compose*.yml`, `LICENSE`)

## Notes

- This sprint is README/docs-only. No runtime behavior is affected.
- The English README uses cautious language: "Based on upstream README", "Observed during source mapping", "To be confirmed during API contract extraction".
- Sensitive systems (token lifecycle, captcha/browser workflows, proxy behavior, upstream client behavior, account/session handling) are described at boundary level only.
- Future translation phases (source comments, UI, logs, errors) are clearly separated in `docs/TRANSLATION_PLAN.md`.
