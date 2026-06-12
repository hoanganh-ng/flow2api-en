# Sprint 003 — Generation Contract Deep Dive

## Sprint Goal

Create a documentation-only deep dive of the generation contract — the highest compatibility-risk surface in flow2api. The deliverables are source-inspection-based documents covering generation routes, streaming behavior, model compatibility, and request/response conversion.

## Scope

- Inspect generation-related source files: `routes.py`, `models.py`, `model_resolver.py`, `generation_handler.py`, `flow_client.py`, and helper modules
- Document the generation route entrypoints and their request/response shapes
- Document streaming behavior (SSE framing, chunk shapes, terminal behavior)
- Document model naming, aliases, resolution, and compatibility-sensitive names
- Document request/response conversion between OpenAI and Gemini formats
- Identify unknowns requiring runtime fixture capture in a future sprint

## Out of Scope

- Runtime behavior changes of any kind
- Source code modifications (Python, static, config, Docker, tests, etc.)
- Translation of any files
- Refactoring or feature additions
- Test harness or fixture creation (deferred to a later sprint)
- Token, captcha, browser, proxy, or session behavior deep dives (boundary-level only)
- Upstream abuse, evasion, or bypass documentation

## Files Changed

### Created

| File | Description |
|------|-------------|
| `docs/GENERATION_CONTRACT.md` | Generation route entrypoints, request flows, handler pipeline, error responses, upload dependencies, high-risk unknowns |
| `docs/STREAMING_CONTRACT_NOTES.md` | Streaming endpoints, SSE framing, chunk shapes (OpenAI/Gemini), terminal behavior, error handling during streams |
| `docs/MODEL_COMPATIBILITY_MAP.md` | Model listing endpoints, aliases, MODEL_CONFIG registry, resolution logic, model families, compatibility-sensitive names |
| `docs/REQUEST_RESPONSE_CONVERSION_MAP.md` | Field-level conversion map: OpenAI↔Gemini↔internal, streaming boundaries, fields that must not be renamed |
| `docs/SPRINTS/SPRINT-003-generation-contract-deep-dive.md` | This file |

### Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Marked Sprint 002 completed, Sprint 003 active, added Sprint 003 documents |
| `docs/SPRINTS/README.md` | Added Sprint 003 to sprint index, marked Sprint 002 completed |

## Source Files Inspected

| File | Lines | Role |
|------|-------|------|
| `src/api/routes.py` | 1–1003 | HTTP route entrypoints, normalization, response shaping, SSE |
| `src/core/models.py` | 1–301 | Pydantic request/response models |
| `src/core/model_resolver.py` | 1–634 | Alias + generationConfig → internal model key resolution |
| `src/services/generation_handler.py` | 1–2467 | MODEL_CONFIG registry, GenerationHandler, image/video pipelines |
| `src/services/flow_client.py` | 1–3123 | Upstream Flow API client (upload, generate, poll) |
| `src/core/account_tiers.py` | (referenced) | Paygate tier model gating |
| `src/services/file_cache.py` | (referenced) | Local media caching |
| `src/core/auth.py` | (referenced) | API key verification |

## Verification Checklist

- [x] No Python source files modified
- [x] No static/admin UI files modified
- [x] No config defaults modified
- [x] No Docker, compose, dependency, test, script, README, or LICENSE files modified
- [x] No translation performed
- [x] No refactoring or feature additions
- [x] `git diff --name-only` confirms only docs/ files changed
- [x] All documents use cautious wording ("observed in source", "appears to", "to be confirmed")
- [x] No secrets, tokens, cookies, or environment values included
- [x] No bypass, evasion, or upstream-protection avoidance instructions

## Note

This sprint is **documentation-only**. All findings are based on source code inspection and have not been verified by runtime testing. The identified unknowns are intended to drive fixture/test harness work in a future sprint.
