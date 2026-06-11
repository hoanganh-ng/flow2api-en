# English Surface Audit

**Sprint:** 001A — English Surface Audit
**Date:** 2025-06-11
**Status:** Complete
**Scope:** Audit-only; no runtime files were modified.

---

## Search Method

A Python script using the Unicode Han range (`\u4e00-\u9fff`, `\u3400-\u4dbf`) was run across the entire repository, excluding `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, build outputs, logs, and binary files.

---

## Summary by Area

| Area | Files | Lines with Chinese | Approx. Chinese chars | Primary content type |
|------|-------|--------------------|-----------------------|----------------------|
| `src/` | 17 | 1,713 | ~16,804 | Comments, docstrings, log messages, runtime error strings |
| `static/` | 3 | 392 | ~3,888 | Admin UI labels, placeholders, page titles, JS text |
| Root files | 4 | 263 | ~2,274 | README.md (bulk), Dockerfile comments, .gitignore comment |
| `config/` | 1 | 15 | ~197 | Inline config comments |
| `extension/` | 2 | 10 | ~99 | Browser extension UI labels, validation messages |
| `tests/` | 3 | 8 | ~40 | Test fixture strings (prompts, error messages) |
| `docs/` | 1 | 1 | ~2 | Brief upstream name reference in GLOSSARY.md |

**Total: ~31 files, ~2,402 lines, ~23,304 Chinese characters**

---

## Detailed File Inventory

### `src/` — Python source (HIGH volume, MIXED risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `src/services/browser_captcha_personal.py` | 570 | ~6,428 | Comments, docstrings, log messages, runtime strings |
| `src/services/flow_client.py` | 324 | ~2,628 | Comments, docstrings, log messages, error strings |
| `src/services/generation_handler.py` | 251 | ~2,197 | Comments, model label strings, config descriptions |
| `src/services/browser_captcha.py` | 148 | ~1,607 | Comments, docstrings, log messages |
| `src/api/admin.py` | 131 | ~1,125 | Comments, runtime error messages (raised exceptions), log strings |
| `src/services/token_manager.py` | 72 | ~598 | Comments, docstrings, log messages |
| `src/core/model_resolver.py` | 58 | ~485 | Comments, mapping descriptions |
| `src/core/config.py` | 27 | ~442 | Docstrings (config field descriptions) |
| `src/core/models.py` | 40 | ~292 | Comments (dataclass field descriptions) |
| `src/services/load_balancer.py` | 29 | ~319 | Log messages, runtime error strings (returned to callers) |
| `src/services/file_cache.py` | 12 | ~164 | Docstrings, one user-facing error string |
| `src/api/routes.py` | 12 | ~113 | Log messages, comments |
| `src/core/logger.py` | 8 | ~93 | Comments, docstrings |
| `src/main.py` | 6 | ~101 | Comments |
| `src/services/proxy_manager.py` | 10 | ~91 | Docstrings, one validation error string |
| `src/services/concurrency_manager.py` | 4 | ~77 | Comments |
| `src/core/database.py` | 11 | ~44 | Comments (schema column descriptions) |

**Risk notes for `src/`:**
- **HIGH risk:** `load_balancer.py` returns Chinese strings in runtime error tuples (e.g., extension route errors). `admin.py` raises `RuntimeError` with Chinese messages. `proxy_manager.py` raises `ValueError` with Chinese validation text. `file_cache.py` has a user-facing Chinese error string. These are runtime-sensitive.
- **MEDIUM risk:** Log messages throughout `src/` are in Chinese. Translating them could affect log parsing or monitoring.
- **LOW risk:** Inline comments and docstrings are documentation-only and safe to translate.

---

### `static/` — Frontend HTML/JS (MEDIUM volume, MEDIUM risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `static/manage.html` | 341 | ~3,555 | Page title, nav labels, tab names, form labels, button text, JS alert strings, status messages |
| `static/test.html` | 43 | ~291 | Page title, form labels, placeholder text, default prompt value |
| `static/login.html` | 8 | ~42 | Page title, form labels, button text, login status message |

**Risk notes for `static/`:**
- These are user-visible admin UI strings. Translation is desirable but must be coordinated — partial translation creates an inconsistent UI.
- Some JS strings (e.g., status messages, alerts) are embedded inline and may be referenced by selectors or logic.

---

### Root files (LOW volume, LOW risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `README.md` | 260 | ~2,247 | Full project README in Chinese (features, usage, config, deployment) |
| `Dockerfile.headed` | 1 | ~14 | Dockerfile comment |
| `Dockerfile` | 1 | ~4 | Dockerfile comment |
| `.gitignore` | 1 | ~9 | Comment |

**Risk notes for root files:**
- `README.md` is pure documentation — safe to translate or replace with an English version.
- Dockerfile and `.gitignore` comments are safe to translate.

---

### `config/` — Configuration example (LOW volume, MEDIUM risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `config/setting_example.toml` | 15 | ~197 | Inline comments describing config options |

**Risk notes for `config/`:**
- The comments are safe to translate. Config keys and values must NOT be translated.

---

### `extension/` — Browser extension (LOW volume, MEDIUM risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `extension/options.html` | 6 | ~74 | UI labels, placeholder text, hint text |
| `extension/options.js` | 4 | ~25 | Validation messages, status strings |

**Risk notes for `extension/`:**
- UI labels and validation messages are user-visible. Safe to translate but should be done as a coordinated UI pass.

---

### `tests/` — Test fixtures (LOW volume, MEDIUM risk)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `tests/test_veo_lite_support.py` | 5 | ~14 | Chinese prompt strings used as test inputs ("猫猫", "变身猫猫") |
| `tests/test_browser_captcha_personal.py` | 2 | ~15 | Chinese error message string, Chinese failure text |
| `tests/test_flow_client_upload.py` | 1 | ~11 | Chinese assertion failure message |

**Risk notes for `tests/`:**
- Test fixture strings may be intentionally Chinese (testing Chinese prompt handling). Translation could break test intent.

---

### `docs/` — Existing English documentation (NEGLIGIBLE)

| File | Lines | Chars | Content types present |
|------|-------|-------|-----------------------|
| `docs/GLOSSARY.md` | 1 | ~2 | Brief upstream author name reference |

**Risk notes for `docs/`:**
- No action needed. The reference is an attribution/name, not translatable content.

---

## Risk Classification Summary

| Risk Level | Description | Approximate scope |
|------------|-------------|-------------------|
| **HIGH** | Runtime error/validation strings returned to callers or raised in exceptions | ~15–20 distinct strings across `load_balancer.py`, `admin.py`, `proxy_manager.py`, `file_cache.py` |
| **MEDIUM** | Log messages (could affect monitoring/parsing), UI strings (coordinated translation needed), test fixtures (may be intentional) | ~600+ lines across `src/`, `static/`, `extension/`, `tests/` |
| **LOW** | Comments, docstrings, README, Dockerfile/gitignore comments | ~1,500+ lines — bulk of Chinese content, safe to translate |

---

## Highest-Risk Translation Surfaces

1. **`src/services/load_balancer.py`** — Returns Chinese error strings in runtime tuples consumed by other services.
2. **`src/api/admin.py`** — Raises `RuntimeError` with Chinese messages that may propagate to API responses.
3. **`src/services/proxy_manager.py`** — `ValueError` with Chinese validation text shown to users.
4. **`src/services/file_cache.py`** — User-facing Chinese error string for missing dependencies.
5. **`static/manage.html`** — Largest UI surface; JS strings intertwined with logic.
6. **`tests/test_veo_lite_support.py`** — Chinese prompt fixtures may test Chinese input handling specifically.

---

## Recommended Next Steps

See [TRANSLATION_PLAN.md](TRANSLATION_PLAN.md) for the full translation classification and phased approach.
