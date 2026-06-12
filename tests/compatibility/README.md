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
| `helpers/shape_assertions.py` | Shallow structural assertion helpers for OpenAI model list, chat completion request/response, and SSE `[DONE]` termination |
| `test_static_generation_fixtures.py` | Executable `unittest.TestCase` tests for the three Sprint 005A fixtures |

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
| FX-OS-003 | `generation/openai-streaming/done-termination.sse.txt` | At least one `data:` event, blank-line SSE framing, final line is `data: [DONE]` |

## What Is Not Yet Tested

- Route-level behavior (requires FastAPI TestClient and runtime imports — future sprint)
- Streaming chunk sequence comparison
- Gemini endpoint shapes
- Error response shapes
- Mocked handler output tests

Future sprints may add mocked route-level tests that exercise the FastAPI
routes with a test client. Those tests will live in a separate directory
and will import the runtime application.
