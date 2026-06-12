# Sprint 005C — Additional Static Generation Fixtures

> **Status:** Active / In Progress
> **Type:** Fixture files only — no executable tests, no runtime changes

---

## Sprint Goal

Add the next small group of sanitized static generation fixtures to the
flow2api-en repository. This sprint extends the fixture collection started in
Sprint 005A (FX-ML-001, FX-ON-001, FX-OS-003) with three additional fixtures
covering image result formatting, Gemini non-streaming, and streaming progress
chunks.

No tests or shape assertions are added in this sprint. Assertions for these
fixtures are planned for Sprint 005D.

---

## Context

Sprint 005A created the first sanitized static generation fixture skeleton
with three fixtures:

- FX-ML-001 — OpenAI model list response shape
- FX-ON-001 — OpenAI non-streaming text request/response shape
- FX-OS-003 — OpenAI streaming `data: [DONE]` termination shape

Sprint 005B added offline fixture loader and shape assertions for all three
Sprint 005A fixtures.

Sprint 005C adds the next batch of static fixtures based on the priorities
identified in [GENERATION_FIXTURE_PLAN.md](../GENERATION_FIXTURE_PLAN.md) and
the fixture matrix in [GENERATION_FIXTURE_MATRIX.md](../GENERATION_FIXTURE_MATRIX.md).

---

## Scope

### Fixtures Created

| Fixture ID | Description | Files |
|------------|-------------|-------|
| FX-ON-002 | OpenAI image result formatting | `tests/fixtures/generation/openai-non-streaming/image-result-request.json`, `image-result-response.json` |
| FX-GN-001 | Gemini non-streaming request/response | `tests/fixtures/generation/gemini-non-streaming/text-basic-request.json`, `text-basic-response.json` |
| FX-OS-002 | OpenAI streaming reasoning_content/progress chunk | `tests/fixtures/generation/openai-streaming/reasoning-progress.sse.txt` |

### Documentation Updated

| File | Change |
|------|--------|
| `tests/fixtures/generation/README.md` | Added FX-ON-002, FX-GN-001, FX-OS-002 entries |
| `docs/GENERATION_FIXTURE_MATRIX.md` | Marked FX-ON-002, FX-GN-001, FX-OS-002 as static fixture files created; not yet tested |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 005C as additional static fixture expansion |
| `docs/PROJECT_STATE.md` | Marked Sprint 005B completed, Sprint 005C active |
| `docs/SPRINTS/README.md` | Added Sprint 005C to sprint index |

---

## Out of Scope

The following are explicitly out of scope for Sprint 005C:

- Executable tests or shape assertions for the new fixtures (planned for Sprint 005D)
- Runtime behavior changes of any kind
- Modifications to Python runtime source files under `src/`
- Modifications to static/admin UI files
- Modifications to config defaults
- Modifications to Docker, compose, dependencies, scripts, README files, or LICENSE
- Translation of any files
- Refactoring of runtime code
- Route handler modifications
- Importing or starting the FastAPI application
- Calling upstream services
- Capturing real upstream responses
- Including real tokens, cookies, account identifiers, local secrets, upstream secrets, or personally identifying data
- Changing endpoints, auth behavior, request/response behavior, streaming behavior, upload behavior, token behavior, captcha/browser/session behavior, proxy behavior, model list behavior, or admin UI behavior
- Fixture loader utility changes
- New test files or test infrastructure

---

## Files Changed

### Created

- `tests/fixtures/generation/openai-non-streaming/image-result-request.json`
- `tests/fixtures/generation/openai-non-streaming/image-result-response.json`
- `tests/fixtures/generation/gemini-non-streaming/text-basic-request.json`
- `tests/fixtures/generation/gemini-non-streaming/text-basic-response.json`
- `tests/fixtures/generation/openai-streaming/reasoning-progress.sse.txt`
- `docs/SPRINTS/SPRINT-005C-additional-static-generation-fixtures.md`

### Modified

- `tests/fixtures/generation/README.md`
- `docs/GENERATION_FIXTURE_MATRIX.md`
- `docs/TEST_HARNESS_PLAN.md`
- `docs/PROJECT_STATE.md`
- `docs/SPRINTS/README.md`

---

## Verification Checklist

- [ ] JSON fixtures validate with `python -m json.tool`
- [ ] Existing Sprint 005B static fixture tests pass without regression: `python -m unittest tests.compatibility.test_static_generation_fixtures -v`
- [ ] `git status --short` shows only expected files
- [ ] `git diff --name-only` confirms no runtime files changed
- [ ] No executable tests, loaders, or scripts created
- [ ] No upstream calls made
- [ ] All fixture content is synthetic and sanitized
- [ ] No real tokens, secrets, cookies, account IDs, or upstream URLs present

---

## Fixture Content Notes

### FX-ON-002

The image result response uses a clearly synthetic markdown image link:
`![Generated Image](https://placeholder.example.invalid/media/test-image.jpg)`.
Exact runtime formatting of image results remains to be confirmed by later
fixtures or runtime capture. The fixture represents the documented shape
but does not claim to match the exact runtime output byte-for-byte.

### FX-GN-001

The Gemini request includes a small `generationConfig` object with
`temperature: 0.7` as an example of an accepted-but-not-forwarded field
(documented in Sprint 003). The response uses the documented
`candidates[].content.parts[]` structure with synthetic text content.

### FX-OS-002

The streaming fixture contains two `data:` events with `reasoning_content`
progress chunks. This fixture focuses on the progress chunk shape only.
Stream termination (`data: [DONE]`) is covered separately by FX-OS-003
and is not included in this fixture.
