# Translation Allowlist

**Sprint:** 001C — Safe Translation Allowlist
**Date:** 2025-06-11
**Status:** Active
**Scope:** Documentation-only. No runtime, source, UI, or config files were modified.

---

## Purpose

This document classifies every remaining Chinese-language surface in the repository into one of three categories:

1. **Allowed** — safe to translate in the next documentation-only sprint.
2. **Requires careful dedicated sprint** — translatable but needs focused review and testing.
3. **Denied** — must not be translated without an explicit contract decision.

The goal is to prevent future translation sprints from accidentally changing runtime behavior, breaking API contracts, or corrupting data.

---

## Current Translation Status

| Surface | Status |
|---------|--------|
| Project-brain docs (`docs/`) | English (Sprint 000, 001, 001A) |
| Root `README.md` | English (Sprint 001B) |
| Original Chinese README | Preserved as `README.zh-CN.md` (Sprint 001B) |
| Source code comments/docstrings | Chinese — untranslated |
| Static/admin UI text | Chinese — untranslated |
| Extension UI text | Chinese — untranslated |
| Config comments | Chinese — untranslated |
| Dockerfile comments | Chinese — untranslated |
| Log messages | Chinese — untranslated |
| Runtime error/validation strings | Chinese — untranslated |
| Test fixture strings | Chinese — untranslated |

**Han character scan (post-Sprint 001B):** 34 files, ~2,406 lines containing Chinese characters. Excluding `README.zh-CN.md` (preserved intentionally, 260 lines), the actionable surface is ~31 files, ~2,146 lines.

---

## Allowed for Next Safe Translation Sprint

These surfaces are documentation-only or developer-facing metadata with zero runtime effect. Translating them carries negligible risk.

| # | File / Group | Surface Type | Lines | Risk | Recommendation | Reason |
|---|-------------|-------------|-------|------|----------------|--------|
| A1 | `Dockerfile` | Comment | 1 | None | Translate comment only | Build comment, no runtime effect |
| A2 | `Dockerfile.headed` | Comment | 1 | None | Translate comment only | Build comment, no runtime effect |
| A3 | `.gitignore` | Comment | 1 | None | Translate comment only | VCS ignore comment, no runtime effect |
| A4 | `config/setting_example.toml` | Inline comments | 15 | None | Translate comments only; preserve all keys and values | Example config file; comments are documentation, keys/values are runtime identifiers |
| A5 | `docs/GLOSSARY.md` | Upstream name reference | 1 | None | Leave as-is (attribution) | Contains upstream author name reference; not translatable content |
| A6 | `docs/ENGLISH_SURFACE_AUDIT.md` | Brief Chinese example in audit table | 1 | None | Leave as-is (audit evidence) | Chinese text is quoted as audit evidence, not prose to translate |
| A7 | `docs/TRANSLATION_PLAN.md` | Chinese log example in Phase 2.3 | 1 | None | Leave as-is (example citation) | Chinese text is a quoted example illustrating log content |
| A8 | `README.md` | Chinese link text | 2 | None | Leave as-is | Contains a link to `README.zh-CN.md` and a YesCaptcha referral URL; both are intentional references |

**Total allowed scope:** ~22 lines across 8 items. Items A5–A8 are recommended to be left as-is rather than translated.

---

## Requires Careful Dedicated Sprint

These surfaces are translatable but require focused review, testing, and coordination. Each group should be addressed in its own dedicated sprint.

### Group B1: Python Source Comments and Docstrings

| File | Lines | Surface Type | Risk | Recommendation | Reason |
|------|-------|-------------|------|----------------|--------|
| `src/services/browser_captcha_personal.py` | 570 | Comments, docstrings, log messages, runtime strings | Mixed | Dedicated sprint; separate comments from runtime strings | Largest file; comments safe but runtime strings must be denied (see Group C) |
| `src/services/flow_client.py` | 324 | Comments, docstrings, log messages, error strings | Mixed | Dedicated sprint; separate comments from runtime strings | Second-largest; same mixed-risk pattern |
| `src/services/generation_handler.py` | 251 | Comments, model label strings, config descriptions | Mixed | Dedicated sprint; comments safe, model labels denied | MODEL_CONFIG comments safe; model identifiers must not change |
| `src/services/browser_captcha.py` | 148 | Comments, docstrings, log messages | Mixed | Dedicated sprint | Same mixed-risk pattern |
| `src/api/admin.py` | 131 | Comments, docstrings, runtime error messages, log strings | Mixed | Dedicated sprint; comments safe, error strings denied | RuntimeError messages are runtime-sensitive |
| `src/services/token_manager.py` | 72 | Comments, docstrings, log messages | Mixed | Dedicated sprint | Log messages require monitoring review |
| `src/core/model_resolver.py` | 58 | Comments, mapping descriptions | Low | Dedicated sprint | Comments are safe; mapping identifiers must not change |
| `src/core/config.py` | 27 | Docstrings (config field descriptions) | Low | Dedicated sprint | Docstrings accessible via `__doc__` but not used for control flow |
| `src/core/models.py` | 40 | Comments (dataclass field descriptions) | Low | Dedicated sprint | Comments only; field names must not change |
| `src/services/load_balancer.py` | 29 | Log messages, runtime error strings | Mixed | Dedicated sprint; log/error strings denied | Error tuples returned to callers |
| `src/services/file_cache.py` | 12 | Docstrings, user-facing error string | Mixed | Dedicated sprint; error string denied | One user-facing error string is runtime-sensitive |
| `src/api/routes.py` | 12 | Log messages, comments | Mixed | Dedicated sprint | Log messages require monitoring review |
| `src/core/logger.py` | 8 | Comments, docstrings | Low | Dedicated sprint | Safe documentation-only content |
| `src/main.py` | 6 | Comments | Low | Dedicated sprint | Safe documentation-only content |
| `src/services/proxy_manager.py` | 10 | Docstrings, validation error string | Mixed | Dedicated sprint; validation string denied | ValueError text shown to users |
| `src/services/concurrency_manager.py` | 4 | Comments | Low | Dedicated sprint | Safe documentation-only content |
| `src/core/database.py` | 11 | Comments (schema column descriptions) | Low | Dedicated sprint | Comments only; schema identifiers must not change |

**Total: ~1,625 lines across 17 files.**

**Critical note:** Within each file, comments and docstrings are safe, but log messages, error strings, and validation strings are **denied** (see Group C). A dedicated source-comment sprint must carefully distinguish safe comments from runtime-sensitive strings on a line-by-line basis.

### Group B2: Static/Admin UI Text

| File | Lines | Surface Type | Risk | Recommendation | Reason |
|------|-------|-------------|------|----------------|--------|
| `static/manage.html` | 341 | Page title, nav labels, tab names, form labels, button text, JS alerts, status messages | Medium | Dedicated UI sprint; test all admin workflows after | Largest UI surface; JS strings may be referenced by selectors or logic |
| `static/test.html` | 43 | Page title, form labels, placeholder text, default prompt value | Medium | Dedicated UI sprint | User-visible test page |
| `static/login.html` | 8 | Page title, form labels, button text, login status message | Medium | Dedicated UI sprint | User-visible login page |

**Total: ~392 lines across 3 files.**

### Group B3: Browser Extension UI

| File | Lines | Surface Type | Risk | Recommendation | Reason |
|------|-------|-------------|------|----------------|--------|
| `extension/options.html` | 6 | UI labels, placeholder text, hint text | Medium | Dedicated UI sprint (combine with B2) | User-visible extension options |
| `extension/options.js` | 4 | Validation messages, status strings | Medium | Dedicated UI sprint (combine with B2) | Validation messages may be compared by string matching |

**Total: ~10 lines across 2 files.**

### Group B4: Test Fixture Strings

| File | Lines | Surface Type | Risk | Recommendation | Reason |
|------|-------|-------------|------|----------------|--------|
| `tests/test_veo_lite_support.py` | 5 | Chinese prompt strings ("猫猫", "变身猫猫") | Medium | Dedicated test sprint; review if Chinese input is intentional | May test Chinese-language input handling specifically |
| `tests/test_browser_captcha_personal.py` | 2 | Chinese error message, failure text | Medium | Dedicated test sprint | May test Chinese error handling |
| `tests/test_flow_client_upload.py` | 1 | Chinese assertion failure message | Medium | Dedicated test sprint | Assertion message translation is low-risk but should be reviewed |

**Total: ~8 lines across 3 files.**

### Group B5: Dockerfile Comments (if not covered in Group A)

| File | Lines | Surface Type | Risk | Recommendation | Reason |
|------|-------|-------------|------|----------------|--------|
| `Dockerfile` | 1 | Comment | None | Already in Allowed (A1) | — |
| `Dockerfile.headed` | 1 | Comment | None | Already in Allowed (A2) | — |

---

## Denied Until Explicit Contract Decision

These surfaces are part of the runtime contract. Translating them could break API compatibility, monitoring, database integrity, or external integrations. **Do not translate these in any sprint without an explicit contract decision document.**

| # | Surface | Files | Risk | Reason |
|---|---------|-------|------|--------|
| C1 | API response text | `src/api/routes.py`, `src/api/admin.py` | Critical | Response bodies consumed by downstream clients |
| C2 | Runtime error messages | `src/api/admin.py` (RuntimeError), `src/services/load_balancer.py` (error tuples), `src/services/proxy_manager.py` (ValueError), `src/services/file_cache.py` (user-facing error) | Critical | May propagate to API responses; clients may match on text |
| C3 | Log messages | `src/services/load_balancer.py`, `src/api/admin.py`, `src/api/routes.py`, `src/services/token_manager.py`, `src/services/browser_captcha.py`, `src/services/browser_captcha_personal.py`, `src/services/flow_client.py`, `src/main.py` | High | External monitoring, log parsers, or grep-based alerting may depend on Chinese log text |
| C4 | Endpoint paths | `src/api/routes.py` | Critical | Part of the API contract; no Chinese paths found (already English) |
| C5 | Config keys and enum values | `config/setting_example.toml`, `src/core/config.py` | Critical | Runtime identifiers; already English. Keys and values must not change |
| C6 | Model names and provider names | `src/core/model_resolver.py`, `src/services/generation_handler.py`, `src/core/models.py` | Critical | API-facing identifiers consumed by clients |
| C7 | Database column names, defaults, enum strings | `src/core/database.py` | Critical | Schema integrity; stored values must match code expectations |
| C8 | Token lifecycle runtime strings | `src/services/token_manager.py` | Critical | Parsed, compared, or stored during token lifecycle |
| C9 | Captcha/session runtime strings | `src/services/browser_captcha.py`, `src/services/browser_captcha_personal.py`, `src/services/browser_captcha_extension.py`, `src/services/browser_cookie_utils.py` | Critical | Used in captcha solving, session management, cookie extraction |
| C10 | Proxy runtime strings | `src/services/proxy_manager.py`, `src/services/flow_client.py`, `src/services/file_cache.py` | Critical | Proxy URL parsing, routing, and fallback logic |
| C11 | Upstream API interaction strings | `src/services/flow_client.py` | Critical | Request/response contracts with upstream Google Labs / AI Sandbox APIs |
| C12 | README.zh-CN.md | Root | None | Intentionally preserved Chinese original; do not modify |

---

## File-by-File Classification

| File Path | Category | Action |
|-----------|----------|--------|
| `Dockerfile` | Allowed (A1) | Translate comment in next safe sprint |
| `Dockerfile.headed` | Allowed (A2) | Translate comment in next safe sprint |
| `.gitignore` | Allowed (A3) | Translate comment in next safe sprint |
| `config/setting_example.toml` | Allowed (A4) | Translate comments only in next safe sprint |
| `docs/GLOSSARY.md` | Allowed (A5) | Leave as-is (attribution) |
| `docs/ENGLISH_SURFACE_AUDIT.md` | Allowed (A6) | Leave as-is (audit evidence) |
| `docs/TRANSLATION_PLAN.md` | Allowed (A7) | Leave as-is (example citation) |
| `README.md` | Allowed (A8) | Leave as-is (link references) |
| `README.zh-CN.md` | Denied (C12) | Do not modify; preserved Chinese original |
| `src/api/admin.py` | Careful (B1) + Denied (C2, C3) | Comments/docstrings in dedicated sprint; error/log strings denied |
| `src/api/routes.py` | Careful (B1) + Denied (C1, C3) | Comments in dedicated sprint; log/response strings denied |
| `src/core/config.py` | Careful (B1) + Denied (C5) | Docstrings in dedicated sprint; config keys/values denied |
| `src/core/database.py` | Careful (B1) + Denied (C7) | Comments in dedicated sprint; schema identifiers denied |
| `src/core/logger.py` | Careful (B1) | Comments/docstrings in dedicated sprint |
| `src/core/model_resolver.py` | Careful (B1) + Denied (C6) | Comments in dedicated sprint; model identifiers denied |
| `src/core/models.py` | Careful (B1) + Denied (C6) | Comments in dedicated sprint; field names denied |
| `src/main.py` | Careful (B1) | Comments in dedicated sprint |
| `src/services/browser_captcha.py` | Careful (B1) + Denied (C3, C9) | Comments in dedicated sprint; log/runtime strings denied |
| `src/services/browser_captcha_personal.py` | Careful (B1) + Denied (C3, C9) | Comments in dedicated sprint; log/runtime strings denied |
| `src/services/browser_captcha_extension.py` | Denied (C9) | Runtime strings only; no significant comments |
| `src/services/browser_cookie_utils.py` | Denied (C9) | Runtime strings only |
| `src/services/concurrency_manager.py` | Careful (B1) | Comments in dedicated sprint |
| `src/services/file_cache.py` | Careful (B1) + Denied (C2, C10) | Docstrings in dedicated sprint; error/proxy strings denied |
| `src/services/flow_client.py` | Careful (B1) + Denied (C3, C10, C11) | Comments in dedicated sprint; log/proxy/upstream strings denied |
| `src/services/generation_handler.py` | Careful (B1) + Denied (C6) | Comments in dedicated sprint; model identifiers denied |
| `src/services/load_balancer.py` | Careful (B1) + Denied (C2, C3) | Comments in dedicated sprint; error/log strings denied |
| `src/services/proxy_manager.py` | Careful (B1) + Denied (C2, C10) | Docstrings in dedicated sprint; validation/proxy strings denied |
| `src/services/token_manager.py` | Careful (B1) + Denied (C3, C8) | Comments in dedicated sprint; log/token strings denied |
| `static/login.html` | Careful (B2) | Dedicated UI sprint |
| `static/manage.html` | Careful (B2) | Dedicated UI sprint |
| `static/test.html` | Careful (B2) | Dedicated UI sprint |
| `extension/options.html` | Careful (B3) | Dedicated UI sprint |
| `extension/options.js` | Careful (B3) | Dedicated UI sprint |
| `tests/test_browser_captcha_personal.py` | Careful (B4) | Dedicated test sprint |
| `tests/test_flow_client_upload.py` | Careful (B4) | Dedicated test sprint |
| `tests/test_veo_lite_support.py` | Careful (B4) | Dedicated test sprint |

---

## Recommended Next Sprint

**Sprint 002 — Safe Comment Translation (Phase 1)**

Scope:
- Translate comments in `Dockerfile`, `Dockerfile.headed`, `.gitignore` (items A1–A3).
- Translate inline comments in `config/setting_example.toml` (item A4), preserving all keys and values.

This is the lowest-risk translation work remaining and can be completed quickly.

**Subsequent sprints (in recommended order):**
1. **Sprint 003** — Python source comments and docstrings (Group B1), with strict line-by-line separation from denied runtime strings.
2. **Sprint 004** — Static/admin UI and extension UI (Groups B2, B3), as a single coordinated UI pass.
3. **Sprint 005** — Test fixture review (Group B4), determining which Chinese content is semantically meaningful.
4. **Sprint 006+** — Contract decision sprints for denied surfaces (Group C), if ever needed.

---

## Verification Notes

- Han character scan method: Python script using Unicode Han range (`\u4e00–\u9fff`, `\u3400–\u4dbf`), excluding `.git/`, `__pycache__/`, `.venv/`, `node_modules/`, build outputs, logs, and binary files.
- Scan date: 2025-06-11 (post-Sprint 001B).
- All classifications are conservative: when uncertain, the surface is classified as "denied."
- This allowlist should be re-verified before each translation sprint to confirm no drift.
- No runtime, source, UI, config, Docker, compose, dependency, test, or script files were modified during this sprint.
