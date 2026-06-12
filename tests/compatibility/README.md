# Offline Compatibility Fixture Tests

This directory contains **offline** compatibility fixture tests for flow2api-en.

## What These Tests Do

These tests load the static fixture files created in Sprint 005A
(`tests/fixtures/generation/`) and verify their **structural shape** against
the documented OpenAI-compatible API envelopes.

They are the first executable safety net for the project's generation
compatibility surface.

## Key Properties

| Property | Value |
|----------|-------|
| Offline | Yes — no network access, no upstream calls |
| Deterministic | Yes — fixtures are static files |
| Runtime app import | No — the FastAPI app is never imported |
| Real secrets/tokens | No — all fixtures are synthetic and sanitized |
| Dependencies | Standard library only (no pytest required) |

## Files

| File | Purpose |
|------|---------|
| `helpers/fixture_loader.py` | Loads JSON and text fixtures from `tests/fixtures/` using `pathlib` and `json` |
| `helpers/shape_assertions.py` | Shallow structural assertion helpers for OpenAI model list, chat completion request/response, image result response, Gemini generateContent request/response, SSE `[DONE]` termination, and SSE reasoning_content progress |
| `test_static_generation_fixtures.py` | Executable `unittest.TestCase` tests for the Sprint 005A fixtures (FX-ML-001, FX-ON-001, FX-OS-003) and Sprint 005C fixtures (FX-ON-002, FX-GN-001, FX-OS-002) |

## Running the Tests

Using `unittest` (no extra dependencies):

```bash
# From the repository root
python -m unittest tests.compatibility.test_static_generation_fixtures
```

Using `pytest` (if available):

```bash
pytest tests/compatibility/test_static_generation_fixtures.py
```

## Fixtures Covered

| Fixture ID | Fixture file | What is verified |
|------------|-------------|-----------------|
| FX-ML-001 | `generation/model-list/openai-model-list.json` | `object: "list"`, `data[]` array, each item has `id`, `object`, `created`, `owned_by` |
| FX-ON-001 (request) | `generation/openai-non-streaming/text-basic-request.json` | `model`, `messages[]` (non-empty, each with `role`/`content`), `stream: false` |
| FX-ON-001 (response) | `generation/openai-non-streaming/text-basic-response.json` | `id`, `object`, `created`, `model`, `choices[]` (non-empty, first has `index`/`message`/`finish_reason`), `usage` |
| FX-ON-002 (request) | `generation/openai-non-streaming/image-result-request.json` | `model`, `messages[]` (non-empty), `stream: false` — reuses base chat completion request shape |
| FX-ON-002 (response) | `generation/openai-non-streaming/image-result-response.json` | OpenAI chat completion base shape plus assistant message content containing a markdown image reference (`![Generated Image](…)`) |
| FX-GN-001 (request) | `generation/gemini-non-streaming/text-basic-request.json` | `contents[]` (non-empty), each content has `parts[]`, at least one part has `text` |
| FX-GN-001 (response) | `generation/gemini-non-streaming/text-basic-response.json` | `candidates[]` (non-empty), candidate content has `parts[]`, at least one part has `text` |
| FX-OS-002 | `generation/openai-streaming/reasoning-progress.sse.txt` | At least one `data:` event, blank-line SSE framing, parseable JSON payloads with `object: "chat.completion.chunk"`, `choices[0].delta.reasoning_content` present |
| FX-OS-003 | `generation/openai-streaming/done-termination.sse.txt` | At least one `data:` event, blank-line SSE framing, final line is `data: [DONE]` |

> **Note:** All tests in this directory are offline/static only. They verify
> fixture file shape and structure. They do **not** test route-level behavior,
> HTTP responses, or runtime application logic.

## What Is Not Yet Tested

- Route-level behavior (requires FastAPI TestClient and runtime imports — future sprint)
- Streaming chunk sequence comparison
- Error response shapes
- Mocked handler output tests

Future sprints may add mocked route-level tests that exercise the FastAPI
routes with a test client. Those tests will live in a separate directory
and will import the runtime application.
