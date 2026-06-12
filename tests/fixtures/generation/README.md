# Generation Fixtures

This directory contains fixtures for generation endpoint compatibility testing.

## Scope

Generation fixtures cover the text and media generation surfaces:
- Model listing endpoints
- OpenAI-compatible non-streaming generation
- OpenAI-compatible streaming generation

All fixtures are synthetic and sanitized. No real upstream responses are included in Sprint 005A.

## Current Fixtures

### FX-ML-001: OpenAI Model List Response

**File:** `model-list/openai-model-list.json`

**Purpose:** Verifies that `/v1/models` returns a structurally valid OpenAI-compatible model catalog.

**What it verifies:**
- Response has `object: "list"`
- Response has `data` array
- Each model entry has required fields: `id`, `object`, `created`, `owned_by`

**What it does not verify:**
- Exact model IDs or catalog completeness
- Model aliases or resolution behavior
- Runtime model availability

**Runtime capture:** Not required. Static fixture based on documented response shape.

---

### FX-ON-001: OpenAI Non-Streaming Text Basic Request/Response

**Files:**
- `openai-non-streaming/text-basic-request.json`
- `openai-non-streaming/text-basic-response.json`

**Purpose:** Verifies that `POST /v1/chat/completions` with `stream: false` accepts minimal request shape and returns structurally valid response.

**What it verifies:**
- Request accepts `model`, `messages`, `stream: false`
- Response has `id`, `object`, `created`, `model`, `choices`
- Response `choices[0]` has `message.role`, `message.content`, `finish_reason`

**What it does not verify:**
- Actual generation behavior or content
- Model resolution or alias expansion
- Upstream API interaction
- Token usage accuracy

**Runtime capture:** Not required. Static fixture based on documented request/response shapes.

---

### FX-OS-003: OpenAI Streaming [DONE] Termination

**File:** `openai-streaming/done-termination.sse.txt`

**Purpose:** Verifies that OpenAI streaming endpoints terminate with the `data: [DONE]` sentinel.

**What it verifies:**
- SSE stream contains at least one `data:` line with JSON chunk
- SSE stream terminates with exactly `data: [DONE]`
- No trailing data after `[DONE]` sentinel

**What it does not verify:**
- Exact chunk timing or ordering
- Progress message (`reasoning_content`) behavior
- Media URL formatting in chunks
- Upstream streaming behavior

**Runtime capture:** Not required. Static fixture based on documented SSE termination pattern.

---

## What Is Not Yet Included

- Gemini endpoint fixtures (planned for future sprint)
- Media generation fixtures (images, videos)
- Error response fixtures
- Request conversion fixtures
- Runtime-captured fixtures from live upstream

See `docs/GENERATION_FIXTURE_MATRIX.md` for the complete fixture plan.
