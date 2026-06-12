# Sprint 005D — Additional Static Fixture Assertions

> **Status:** Active / In Progress
> **Type:** Offline static fixture assertions — no runtime changes

---

## Sprint Goal

Extend the existing offline static compatibility fixture tests to cover the
three Sprint 005C fixtures:

- FX-ON-002 — OpenAI image result formatting
- FX-GN-001 — Gemini non-streaming request/response
- FX-OS-002 — OpenAI streaming reasoning_content/progress chunk

This sprint adds shape assertion helpers and `unittest.TestCase` tests only.
It does **not** test route-level behavior, import the runtime FastAPI
application, or call upstream services.

---

## Context

Sprint 005A created the first sanitized static generation fixture skeleton
(FX-ML-001, FX-ON-001, FX-OS-003).

Sprint 005B added an offline fixture loader
(`tests/compatibility/helpers/fixture_loader.py`), shallow shape assertion
helpers (`tests/compatibility/helpers/shape_assertions.py`), and executable
`unittest.TestCase` tests (`tests/compatibility/test_static_generation_fixtures.py`)
for all three Sprint 005A fixtures.

Sprint 005C added three additional static fixture files (FX-ON-002, FX-GN-001,
FX-OS-002) without adding any tests or assertions.

Sprint 005D closes the assertion gap by adding offline static shape
assertions for the Sprint 005C fixtures.

---

## Scope

### Shape Assertion Helpers Added

| Helper function | Fixture ID | Description |
|-----------------|------------|-------------|
| `assert_openai_image_result_response_shape` | FX-ON-002 | OpenAI image result response: base chat completion shape plus markdown image marker in `choices[0].message.content` |
| `assert_gemini_generate_content_request_shape` | FX-GN-001 | Gemini generateContent request: `contents[]` with `parts[]`, at least one part has `text` |
| `assert_gemini_generate_content_response_shape` | FX-GN-001 | Gemini generateContent response: `candidates[]` with `content.parts[]`, at least one part has `text` |
| `assert_sse_reasoning_progress_shape` | FX-OS-002 | SSE reasoning_content progress: `data:` events with `chat.completion.chunk` shape, `delta.reasoning_content` present |

### Tests Added

| Test class | Fixture ID | What is tested |
|------------|------------|---------------|
| `FXON002ImageResultRequestShapeTests` | FX-ON-002 | `model`, `messages[]` non-empty, `stream: false`, base chat completion request shape |
| `FXON002ImageResultResponseShapeTests` | FX-ON-002 | OpenAI chat completion base shape, assistant message content contains markdown image reference |
| `FXGN001GeminiRequestShapeTests` | FX-GN-001 | `contents[]` non-empty, each content has `parts[]`, at least one part has `text` |
| `FXGN001GeminiResponseShapeTests` | FX-GN-001 | `candidates[]` non-empty, candidate content has `parts[]`, at least one part has `text` |
| `FXOS002SSEReasoningProgressShapeTests` | FX-OS-002 | At least one `data:` event, blank-line SSE framing, parseable JSON chunks, `object: "chat.completion.chunk"`, `delta.reasoning_content` present, `[DONE]` not required |

### Files Changed

| File | Change |
|------|--------|
| `tests/compatibility/helpers/shape_assertions.py` | Added four new assertion helpers |
| `tests/compatibility/test_static_generation_fixtures.py` | Added loading tests and shape assertion test classes for FX-ON-002, FX-GN-001, FX-OS-002 |
| `tests/compatibility/README.md` | Added FX-ON-002, FX-GN-001, FX-OS-002 to covered fixtures; clarified offline/static scope |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Marked FX-ON-002, FX-GN-001, FX-OS-002 as having static shape assertions added |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 005D as additional static fixture assertion coverage |
| `docs/PROJECT_STATE.md` | Marked Sprint 005C completed, Sprint 005D active |
| `docs/SPRINTS/README.md` | Added Sprint 005D to sprint index; marked Sprint 005C completed |
| `docs/SPRINTS/SPRINT-005D-additional-static-fixture-assertions.md` | This document |

---

## Out of Scope

- Route-level behavior tests (requires FastAPI TestClient — future sprint)
- Mocked generation-handler tests (future sprint)
- Runtime application imports
- Upstream service calls or real upstream response capture
- New fixture files (only assertions for existing Sprint 005C fixtures)
- Fixture loader changes (not required for this sprint)
- Changes to runtime source files (`src/`), config, Docker, compose, scripts,
  admin UI, static files, dependencies, or license
- Translation of any files or strings
- Streaming chunk sequence comparison
- Error response shapes (future sprint)

---

## Verification Checklist

- [x] JSON fixture files validate with `python -m json.tool`
- [x] All compatibility fixture tests pass:
      `python -m unittest tests.compatibility.test_static_generation_fixtures -v`
- [x] No runtime files modified (`src/`, `config/`, `docker/`, `extension/`,
      `static/`, `main.py`, `requirements.txt`, `Dockerfile*`, `docker-compose*.yml`, `LICENSE`)
- [x] No upstream services called
- [x] No real tokens, secrets, cookies, or account identifiers included
- [x] No new dependencies added
- [x] `git diff --name-only` includes only the files listed in "Files Changed"
- [x] Route-level behavior is not tested
- [x] Fork remains clearly unofficial

---

## Notes

This sprint adds **offline static fixture assertions only**. All tests remain
fully offline and deterministic. The fixture loader (`fixture_loader.py`) is
unchanged because the existing `load_json` and `load_text` functions already
support all fixture types needed for Sprint 005D.
