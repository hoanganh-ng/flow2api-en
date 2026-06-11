# Translation Plan

**Sprint:** 001A — English Surface Audit
**Date:** 2025-06-11
**Status:** Planning document — no translations have been applied yet.

---

## Overview

This document classifies every Chinese-language surface identified in the [English Surface Audit](ENGLISH_SURFACE_AUDIT.md) into one of three translation phases. The goal is to guide future sprints so that translations are applied safely, without breaking runtime behavior or API contracts.

---

## Phase 1 — Safe to Translate Soon

These surfaces are documentation-only or developer-facing. Translating them carries negligible runtime risk.

### 1.1 README.md (root)

- **Content:** Full project README — features, usage instructions, configuration, deployment guide.
- **Risk:** None. Pure documentation consumed by humans.
- **Approach:** Replace with an English README. Preserve the original Chinese README as `README.zh-CN.md` for upstream compatibility if desired.

### 1.2 Inline comments in Python source (`src/`)

- **Content:** `# comment` lines in all 17 source files (~1,500+ lines).
- **Risk:** None. Comments are stripped at bytecode compilation and have no runtime effect.
- **Approach:** Translate comment-by-comment during a dedicated sprint. Do not alter any code logic, string literals, or indentation.
- **Files affected:** All files under `src/`, particularly `browser_captcha_personal.py` (570 lines), `flow_client.py` (324 lines), `generation_handler.py` (251 lines), `browser_captcha.py` (148 lines), `admin.py` (131 lines).

### 1.3 Docstrings in Python source (`src/`)

- **Content:** Triple-quoted docstrings describing functions, classes, and parameters.
- **Risk:** Very low. Docstrings are accessible via `__doc__` at runtime but are not used for control flow or API responses in this codebase.
- **Approach:** Translate alongside comments in the same sprint. Preserve parameter names and type references exactly.
- **Files affected:** `config.py` (27 lines), `models.py` (40 lines), `model_resolver.py` (58 lines), `logger.py` (8 lines), `proxy_manager.py` (10 lines), `file_cache.py` (12 lines), `concurrency_manager.py` (4 lines), `token_manager.py` (72 lines).

### 1.4 Dockerfile comments

- **Content:** Single-line Chinese comments in `Dockerfile` and `Dockerfile.headed`.
- **Risk:** None. Comments only.
- **Approach:** Translate inline.

### 1.5 `.gitignore` comment

- **Content:** One Chinese comment line.
- **Risk:** None.
- **Approach:** Translate inline.

### 1.6 `config/setting_example.toml` comments

- **Content:** Inline comments explaining each config option (15 lines, ~197 chars).
- **Risk:** None for the comments. Config keys and values must NOT be translated.
- **Approach:** Translate comments only. Leave all keys, values, and identifiers untouched.

### 1.7 Developer-only notes

- **Content:** Any `TODO`, `FIXME`, `NOTE` style comments in Chinese.
- **Risk:** None.
- **Approach:** Translate during the comment sprint.

---

## Phase 2 — Translate Carefully Later

These surfaces are user-visible or may interact with runtime logic. Translation requires careful review and testing.

### 2.1 Admin UI static HTML (`static/`)

- **Files:** `manage.html` (341 lines, ~3,555 chars), `login.html` (8 lines, ~42 chars), `test.html` (43 lines, ~291 chars).
- **Content:** Page titles, navigation labels, tab names, form labels, button text, placeholder text, status messages, alert strings.
- **Risk:** Medium. Some JS strings may be compared in event handlers or conditionals. Partial translation creates an inconsistent UI.
- **Approach:** Translate as a single coordinated UI pass. Test all admin workflows after translation. Keep a mapping of old → new strings for reference.

### 2.2 Browser extension UI (`extension/`)

- **Files:** `options.html` (6 lines, ~74 chars), `options.js` (4 lines, ~25 chars).
- **Content:** Labels, placeholders, validation messages, status strings.
- **Risk:** Medium. Validation messages in `options.js` may be compared by string matching.
- **Approach:** Translate in the same sprint as the admin UI for consistency. Test extension connection flow.

### 2.3 Log messages (`src/`)

- **Files:** Spread across `load_balancer.py`, `admin.py`, `routes.py`, `token_manager.py`, `browser_captcha.py`, `browser_captcha_personal.py`, `flow_client.py`, `main.py`.
- **Content:** Structured log lines with Chinese descriptions (e.g., `[LOAD_BALANCER] 开始选择Token ...`).
- **Risk:** Medium. External monitoring, log parsers, or grep-based alerting may depend on existing Chinese log text.
- **Approach:** Translate only after confirming no external systems parse these logs by Chinese keyword. Consider adding English log messages alongside Chinese ones during a transition period.

### 2.4 Runtime error and validation strings (`src/`)

- **Files:** `load_balancer.py` (route error strings), `admin.py` (RuntimeError messages), `proxy_manager.py` (ValueError text), `file_cache.py` (dependency error string).
- **Content:** ~15–20 distinct strings returned to callers or raised in exceptions.
- **Risk:** High. These strings may appear in API error responses consumed by downstream clients. Translating them could break client-side error matching.
- **Approach:** Introduce English error codes or enums first, then attach English messages. Keep Chinese strings as fallback during a transition period. Requires an explicit contract decision sprint.

### 2.5 Test fixture strings (`tests/`)

- **Files:** `test_veo_lite_support.py` (Chinese prompt inputs), `test_browser_captcha_personal.py` (Chinese error string), `test_flow_client_upload.py` (Chinese assertion message).
- **Content:** Chinese prompt text used as test inputs and expected values.
- **Risk:** Medium. Chinese prompts may be testing Chinese-language input handling specifically. Translating them could change test intent.
- **Approach:** Review each test to determine if the Chinese content is semantically meaningful or arbitrary. Replace only arbitrary fixtures; preserve semantically meaningful ones.

---

## Phase 3 — Do Not Translate Without Explicit Contract Decision

These surfaces are part of the runtime contract. Changing them could break API compatibility, database integrity, or external integrations.

### 3.1 API field names and endpoint paths

- **Status:** No Chinese field names or paths were found in this audit. The API surface already uses English identifiers.
- **Action:** No translation needed. Document this finding for future reference.

### 3.2 Config keys and values

- **Files:** `config/setting_example.toml`, `src/core/config.py`.
- **Content:** Config keys (e.g., `captcha_method`, `personal_max_resident_tabs`) are already English. Values like `"extension"`, `"yescaptcha"`, `"browser"`, `"personal"` are runtime enums.
- **Action:** Do NOT translate keys or enum values. Only translate surrounding comments (Phase 1).

### 3.3 Database schema and stored values

- **Files:** `src/core/database.py`.
- **Content:** Column names are English. Chinese comments describe columns but are not part of the schema.
- **Action:** Do NOT translate column names, default values, or enum strings stored in the database. Translate descriptive comments only (Phase 1).

### 3.4 Model names and provider names

- **Files:** `src/core/model_resolver.py`, `src/services/generation_handler.py`, `src/core/models.py`.
- **Content:** Model identifiers (e.g., `veo_3_1_t2v_fast_portrait`, `GEM_PIX_2`, `IMAGEN_3_5`) are already English/code-style. Chinese text around them is descriptive comments.
- **Action:** Do NOT translate model names, provider identifiers, or API-facing labels. Translate surrounding comments only (Phase 1).

### 3.5 Token, captcha, proxy, and session runtime strings

- **Files:** `src/services/token_manager.py`, `src/services/browser_captcha.py`, `src/services/browser_captcha_personal.py`, `src/services/proxy_manager.py`, `src/services/load_balancer.py`.
- **Content:** Runtime strings used in token lifecycle, captcha solving, proxy configuration, and session management.
- **Action:** Do NOT translate any string that is compared, parsed, or stored as part of runtime state. Treat all such strings as contract until proven otherwise.

---

## Recommended Sprint Sequence

| Sprint | Scope | Phase |
|--------|-------|-------|
| Sprint 002 | Translate `README.md` + Dockerfile/gitignore comments | Phase 1.1, 1.4, 1.5 |
| Sprint 003 | Translate `config/setting_example.toml` comments | Phase 1.6 |
| Sprint 004 | Translate Python comments and docstrings (`src/`) | Phase 1.2, 1.3, 1.7 |
| Sprint 005 | Translate admin UI (`static/`) and extension UI (`extension/`) | Phase 2.1, 2.2 |
| Sprint 006 | Translate log messages with transition strategy | Phase 2.3 |
| Sprint 007 | Introduce English error codes/enums, migrate runtime strings | Phase 2.4 |
| Sprint 008+ | Review and update test fixtures | Phase 2.5 |

Each sprint should include verification steps confirming no runtime behavior changed.

---

## General Translation Rules

1. **Never translate a string that is compared, parsed, hashed, or stored in the database** without an explicit contract decision.
2. **Preserve all code identifiers** — variable names, function names, class names, parameter names.
3. **Preserve all config keys, enum values, and API field names.**
4. **When in doubt, classify as risky** and defer to a later sprint.
5. **Test after every translation sprint** — run the full test suite and manually verify admin UI workflows.
6. **Keep the fork clearly unofficial** — do not imply endorsement by the upstream author.
7. **Preserve license and attribution** in all files.
