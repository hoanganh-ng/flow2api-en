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

- Error response fixtures
- Request conversion fixtures
- Runtime-captured fixtures from live upstream
- Video result formatting fixtures
- Gemini streaming fixtures

See `docs/GENERATION_FIXTURE_MATRIX.md` for the complete fixture plan.

---

## Sprint 005C Additions

> All fixtures added in Sprint 005C are synthetic and sanitized. No real upstream responses are included. No executable tests are added in Sprint 005C; assertions for these fixtures are planned for Sprint 005D.

---

### FX-ON-002: OpenAI Image Result Formatting

**Files:**
- `openai-non-streaming/image-result-request.json`
- `openai-non-streaming/image-result-response.json`

**Purpose:** Verifies that `POST /v1/chat/completions` with `stream: false` accepts an image-generation request shape and returns a structurally valid response containing an image result in the assistant message content.

**What it verifies:**
- Request accepts `model`, `messages`, `stream: false`
- Response has `id`, `object`, `created`, `model`, `choices`, `usage`
- Response `choices[0].message.content` contains a markdown image link pattern `![Generated Image](<url>)`

**What it does not verify:**
- Actual image generation behavior
- Exact runtime image URL formatting (the representative markdown image link used here is synthetic; exact runtime formatting remains to be confirmed by later fixtures)
- Model resolution or alias expansion for image models
- Upstream API interaction
- Whether an additive `url` field is present in the response

**Runtime capture:** Not required. Static fixture based on documented response shapes.

---

### FX-GN-001: Gemini Non-Streaming Request/Response

**Files:**
- `gemini-non-streaming/text-basic-request.json`
- `gemini-non-streaming/text-basic-response.json`

**Purpose:** Verifies that `POST /v1beta/models/{model}:generateContent` accepts a minimal Gemini-compatible request and returns a structurally valid response.

**What it verifies:**
- Request accepts `contents` with `role` and `parts` containing `text`
- Optional `generationConfig` object is accepted
- Response has `candidates` array with `content.role`, `content.parts`, `finishReason`, `index`
- Response has `modelVersion`

**What it does not verify:**
- Actual text generation behavior or content correctness
- Model resolution for Gemini path
- Upstream API interaction
- Media (image/video) result formatting in Gemini response
- `inlineData` or `fileData` part types
- `systemInstruction` passthrough behavior

**Runtime capture:** Not required. Static fixture based on documented Gemini request/response shapes.

---

### FX-OS-002: OpenAI Streaming reasoning_content/progress Chunk

**File:** `openai-streaming/reasoning-progress.sse.txt`

**Purpose:** Verifies that OpenAI streaming endpoints emit intermediate progress chunks with `delta.reasoning_content` before the final content chunk.

**What it verifies:**
- SSE stream contains `data:` events with JSON chunk objects
- Chunk objects have OpenAI-style structure: `id`, `object`, `created`, `model`, `choices`
- `choices[0].delta.reasoning_content` is present with synthetic progress text
- `finish_reason` is `null` on progress chunks

**What it does not verify:**
- Exact number or ordering of progress chunks
- Final content chunk or `finish_reason: "stop"` behavior (covered by FX-OS-003 for `[DONE]` termination)
- Stream termination with `data: [DONE]` (covered separately by FX-OS-003)
- Upstream streaming behavior

**Runtime capture:** Not required. Static fixture based on documented `reasoning_content` chunk shape.
