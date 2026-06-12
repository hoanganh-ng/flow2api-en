# Test Fixtures

This directory contains sanitized, synthetic fixture data for flow2api compatibility testing.

## Purpose

Fixtures provide reproducible test data for verifying API response shapes, streaming behavior, and request/response conversion without calling upstream services.

## Sanitization Policy

All fixtures in this directory are sanitized and synthetic unless explicitly marked otherwise:

- No real API keys, tokens, or credentials
- No real cookies or session identifiers
- No real account IDs or personally identifying information
- No real upstream responses (Sprint 005A uses only synthetic placeholders)
- Placeholder values use the format `test-{type}-placeholder`

## Fixture Naming Convention

Fixtures are organized by category and use the following naming pattern:

```
{fixture-id}_{short-description}.{extension}
```

Examples:
- `openai-model-list.json` — model catalog response
- `text-basic-request.json` — minimal request shape
- `text-basic-response.json` — response envelope
- `done-termination.sse.txt` — streaming sentinel

## Structure

```
fixtures/
  generation/           # Generation endpoint fixtures
    model-list/         # Model listing responses
    openai-non-streaming/  # Non-streaming request/response pairs
    openai-streaming/   # Streaming SSE sequences
```

## Future Test Harness

A test harness utility (not yet implemented) will load these fixtures to verify:
- Response shape compatibility
- Streaming termination behavior
- Request normalization
- Error response formatting

See `docs/TEST_HARNESS_PLAN.md` for the planned implementation approach.
