# Generation Fixture Matrix

> **Sprint 005C — Additional Static Generation Fixtures**
> Three skeleton fixtures created in Sprint 005A: FX-ML-001, FX-ON-001, FX-OS-003.
> Sprint 005B added offline static shape assertions for all three fixtures
> (see `tests/compatibility/test_static_generation_fixtures.py`).
> Sprint 005C adds three additional static fixture files: FX-ON-002, FX-GN-001, FX-OS-002.
> Assertions for the Sprint 005C fixtures are not yet implemented (planned for Sprint 005D).
> Route-level behavior is not yet tested. Remaining fixtures are planned but not yet implemented.

---

## Purpose

This document provides a fixture-by-fixture matrix for planned generation
compatibility tests. Each entry describes a planned fixture, the endpoint it
exercises, the surface category, the intended fixture mode, the input/output
shapes to preserve and verify, compatibility risk, supporting source references,
sensitive data handling notes, and recommended test-harness priority.

All entries use cautious wording. Behavior described here is observed in source
docs and has not been confirmed by runtime testing. To be confirmed during
fixture implementation.

---

## Fixture ID Convention

Fixture IDs follow the pattern: `FX-{CATEGORY}-{SEQ}`

| Prefix | Category |
|--------|----------|
| `FX-ML` | Model listing |
| `FX-ON` | OpenAI non-streaming |
| `FX-OS` | OpenAI streaming |
| `FX-GN` | Gemini non-streaming |
| `FX-GS` | Gemini streaming |
| `FX-CV` | Request/response conversion |
| `FX-ER` | Error behavior |
| `FX-CX` | Custom extension (e.g., `extend://`) |

---

## Fixture Matrix

### FX-ML-001 — GET /v1/models response shape

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ML-001` |
| **Endpoint** | `GET /v1/models` |
| **Method** | GET |
| **Surface category** | model listing |
| **Fixture mode** | static-doc-example |
| **Skeleton status** | ✅ Skeleton created in Sprint 005A (`tests/fixtures/generation/model-list/openai-model-list.json`) |
| **Tested status** | ✅ Static shape assertions added in Sprint 005B (`tests/compatibility/test_static_generation_fixtures.py`) — route-level behavior not tested |
| **Input shape to preserve** | None (no request body); API key in auth header |
| **Output shape to verify** | `{ "object": "list", "data": [{ "id": "<str>", "object": "model", "owned_by": "flow2api", "description": "<str>" }] }` |
| **Compatibility risk** | high |
| **Source references** | `API_SURFACE_INVENTORY.md` §GET /v1/models; `MODEL_COMPATIBILITY_MAP.md` §/v1/models response shape; `routes.py` L788–L801 |
| **Sensitive data notes** | No sensitive data in response. API key placeholder required in auth header. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-ML-002 — GET /v1/models/aliases response shape

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ML-002` |
| **Endpoint** | `GET /v1/models/aliases` |
| **Method** | GET |
| **Surface category** | model aliases |
| **Fixture mode** | static-doc-example |
| **Input shape to preserve** | None (no request body); API key in auth header |
| **Output shape to verify** | `{ "object": "list", "data": [{ "id": "<str>", "object": "model", "owned_by": "flow2api", "description": "<str>", "is_alias": true }] }` |
| **Compatibility risk** | medium |
| **Source references** | `API_SURFACE_INVENTORY.md` §GET /v1/models/aliases; `MODEL_COMPATIBILITY_MAP.md` §Model Aliases Endpoint Behavior; `routes.py` L804–L819 |
| **Sensitive data notes** | No sensitive data. API key placeholder required. |
| **Test-harness priority** | 2 |

---

### FX-ML-003 — GET /v1beta/models response shape

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ML-003` |
| **Endpoint** | `GET /v1beta/models` |
| **Method** | GET |
| **Surface category** | model listing |
| **Fixture mode** | static-doc-example |
| **Input shape to preserve** | None (no request body); API key via `x-goog-api-key` header or `?key=` |
| **Output shape to verify** | `{ "models": [{ "name": "models/{id}", "displayName": "<str>", "description": "<str>", "version": "flow2api", "inputTokenLimit": 0, "outputTokenLimit": 0, "supportedGenerationMethods": ["generateContent", "streamGenerateContent"] }] }` |
| **Compatibility risk** | high |
| **Source references** | `API_SURFACE_INVENTORY.md` §Gemini models; `MODEL_COMPATIBILITY_MAP.md` §Gemini model resource shape; `routes.py` L822–L832, L131–L144 |
| **Sensitive data notes** | No sensitive data. API key placeholder required. |
| **Test-harness priority** | 2 |

---

### FX-ON-001 — POST /v1/chat/completions non-streaming text

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ON-001` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI non-streaming |
| **Fixture mode** | mocked-internal-response |
| **Skeleton status** | ✅ Skeleton created in Sprint 005A (`tests/fixtures/generation/openai-non-streaming/text-basic-request.json`, `text-basic-response.json`) |
| **Tested status** | ✅ Static shape assertions added in Sprint 005B (`tests/compatibility/test_static_generation_fixtures.py`) — route-level behavior not tested |
| **Input shape to preserve** | `{ "model": "<model-id>", "messages": [{"role": "user", "content": "<text>"}], "stream": false }` |
| **Output shape to verify** | `{ "id": "chatcmpl-<ts>", "object": "chat.completion", "created": <int>, "model": "flow2api", "choices": [{ "index": 0, "message": {"role": "assistant", "content": "<text>"}, "finish_reason": "stop" }] }` |
| **Compatibility risk** | high |
| **Source references** | `GENERATION_CONTRACT.md` §OpenAI-compatible non-streaming response; `STREAMING_CONTRACT_NOTES.md`; `generation_handler.py` L2282–L2321 |
| **Sensitive data notes** | Use synthetic prompt text. No real media URLs. Placeholder API key. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-ON-002 — POST /v1/chat/completions image result formatting

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ON-002` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI non-streaming |
| **Fixture mode** | mocked-internal-response |
| **Skeleton status** | ✅ Static fixture file created in Sprint 005C (`tests/fixtures/generation/openai-non-streaming/image-result-request.json`, `image-result-response.json`) |
| **Tested status** | ⬜ Static shape assertions not yet added (planned for Sprint 005D) — route-level behavior not tested |
| **Input shape to preserve** | `{ "model": "<image-model-id>", "messages": [{"role": "user", "content": "generate an image of ..."}], "stream": false }` |
| **Output shape to verify** | Response `choices[0].message.content` contains `![Generated Image](<url>)` pattern. Additive `url` field may be present. |
| **Compatibility risk** | high |
| **Source references** | `GENERATION_CONTRACT.md` §Non-Streaming Response Observations; `API_COMPATIBILITY_NOTES.md` §Response Fields; `generation_handler.py` L2282 |
| **Sensitive data notes** | Use placeholder media URL: `https://placeholder.example.invalid/media/test-image.jpg`. No real fifeUrl values. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-ON-003 — POST /v1/chat/completions video result formatting

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ON-003` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI non-streaming |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | `{ "model": "<video-model-id>", "messages": [{"role": "user", "content": "generate a video of ..."}], "stream": false }` |
| **Output shape to verify** | Response `choices[0].message.content` contains HTML video tag: `` ```html\n<video src='<url>' controls></video>\n``` ``. Additive `url` field may be present. |
| **Compatibility risk** | high |
| **Source references** | `GENERATION_CONTRACT.md` §Non-Streaming Response Observations; `generation_handler.py` L2282 |
| **Sensitive data notes** | Use placeholder media URL: `https://placeholder.example.invalid/media/test-video.mp4`. No real fifeUrl values. |
| **Test-harness priority** | 2 |

---

### FX-OS-001 — POST /v1/chat/completions streaming text

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-OS-001` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI streaming |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | `{ "model": "<model-id>", "messages": [{"role": "user", "content": "<text>"}], "stream": true }` |
| **Output shape to verify** | SSE stream: `data: {"id":"chatcmpl-<ts>","object":"chat.completion.chunk","created":<int>,"model":"flow2api","choices":[{"index":0,"delta":{"role":"assistant",...},"finish_reason":null}]}\n\n` followed by `data: [DONE]\n\n` |
| **Compatibility risk** | high |
| **Source references** | `STREAMING_CONTRACT_NOTES.md` §OpenAI-compatible SSE framing; `API_COMPATIBILITY_NOTES.md` §Streaming/SSE; `routes.py` L717–L737 |
| **Sensitive data notes** | Use synthetic prompt text. Placeholder API key. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-OS-002 — reasoning_content streaming progress messages

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-OS-002` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI streaming |
| **Fixture mode** | mocked-internal-response |
| **Skeleton status** | ✅ Static fixture file created in Sprint 005C (`tests/fixtures/generation/openai-streaming/reasoning-progress.sse.txt`) |
| **Tested status** | ⬜ Static shape assertions not yet added (planned for Sprint 005D) — route-level behavior not tested |
| **Input shape to preserve** | Same as `FX-OS-001`; model triggers image/video generation |
| **Output shape to verify** | Intermediate SSE chunks contain `delta.reasoning_content` (not `delta.content`) with progress/status text. `finish_reason` is `null` on these chunks. |
| **Compatibility risk** | medium |
| **Source references** | `STREAMING_CONTRACT_NOTES.md` §OpenAI-Compatible Streaming Chunk Shape; `generation_handler.py` L2255–L2280 |
| **Sensitive data notes** | Use synthetic progress text: "Uploading image...", "Generating...", etc. |
| **Test-harness priority** | 2 |

---

### FX-OS-003 — data: [DONE] OpenAI stream termination

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-OS-003` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | OpenAI streaming |
| **Fixture mode** | mocked-internal-response |
| **Skeleton status** | ✅ Skeleton created in Sprint 005A (`tests/fixtures/generation/openai-streaming/done-termination.sse.txt`) |
| **Tested status** | ✅ Static shape assertions added in Sprint 005B (`tests/compatibility/test_static_generation_fixtures.py`) — route-level behavior not tested |
| **Input shape to preserve** | Same as `FX-OS-001` |
| **Output shape to verify** | After all content chunks, the stream yields exactly `data: [DONE]\n\n` as the final SSE frame. No further data follows. |
| **Compatibility risk** | high |
| **Source references** | `STREAMING_CONTRACT_NOTES.md` §Finish / Terminal Chunk Behavior; `routes.py` L737 |
| **Sensitive data notes** | No sensitive data. Structural assertion only. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-GN-001 — POST /v1beta/models/{model}:generateContent non-streaming

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-GN-001` |
| **Endpoint** | `POST /v1beta/models/{model}:generateContent` |
| **Method** | POST |
| **Surface category** | Gemini non-streaming |
| **Fixture mode** | mocked-internal-response |
| **Skeleton status** | ✅ Static fixture file created in Sprint 005C (`tests/fixtures/generation/gemini-non-streaming/text-basic-request.json`, `text-basic-response.json`) |
| **Tested status** | ⬜ Static shape assertions not yet added (planned for Sprint 005D) — route-level behavior not tested |
| **Input shape to preserve** | `{ "contents": [{"role": "user", "parts": [{"text": "<prompt>"}]}], "generationConfig": {"imageConfig": {"aspectRatio": "16:9"}} }` |
| **Output shape to verify** | `{ "candidates": [{ "content": {"role": "model", "parts": [...]}, "finishReason": "STOP", "index": 0 }], "modelVersion": "<model>" }` — parts contain `inlineData`, `fileData`, or `text` |
| **Compatibility risk** | high |
| **Source references** | `GENERATION_CONTRACT.md` §Gemini-compatible non-streaming response; `API_COMPATIBILITY_NOTES.md`; `routes.py` L654–L671, L892–L935 |
| **Sensitive data notes** | Use synthetic prompt text. Placeholder media URLs. Placeholder API key. |
| **Test-harness priority** | 1 (first slice) |

---

### FX-GS-001 — POST /v1beta/models/{model}:streamGenerateContent streaming

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-GS-001` |
| **Endpoint** | `POST /v1beta/models/{model}:streamGenerateContent` |
| **Method** | POST |
| **Surface category** | Gemini streaming |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | `{ "contents": [{"role": "user", "parts": [{"text": "<prompt>"}]}] }` |
| **Output shape to verify** | SSE stream: each chunk `data: {"candidates":[{"index":0,"content":{"role":"model","parts":[{"text":"..."}]},"finishReason":"STOP"}],"modelVersion":"<model>"}\n\n`. Final chunk has `finishReason: "STOP"`. Stream ends without `[DONE]` sentinel. |
| **Compatibility risk** | high |
| **Source references** | `STREAMING_CONTRACT_NOTES.md` §Gemini-compatible SSE framing; `routes.py` L740–L785, L685–L714 |
| **Sensitive data notes** | Use synthetic prompt text. Placeholder API key. |
| **Test-harness priority** | 2 |

---

### FX-GS-002 — Gemini stream termination without [DONE] sentinel

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-GS-002` |
| **Endpoint** | `POST /v1beta/models/{model}:streamGenerateContent` |
| **Method** | POST |
| **Surface category** | Gemini streaming |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | Same as `FX-GS-001` |
| **Output shape to verify** | After the last Gemini-shaped event (with `finishReason: "STOP"`), the stream terminates. No `data: [DONE]\n\n` frame is emitted. The internal OpenAI `[DONE]` sentinel is consumed and skipped. |
| **Compatibility risk** | high |
| **Source references** | `STREAMING_CONTRACT_NOTES.md` §Gemini stream; `routes.py` L756–L757 |
| **Sensitive data notes** | No sensitive data. Structural assertion only. |
| **Test-harness priority** | 2 |

---

### FX-CV-001 — Gemini-to-internal request conversion

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-CV-001` |
| **Endpoint** | `POST /v1beta/models/{model}:generateContent` (or `/v1/chat/completions` with `contents`) |
| **Method** | POST |
| **Surface category** | request normalization |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | Gemini request: `{ "contents": [{"role": "user", "parts": [{"text": "prompt"}, {"inlineData": {"mimeType": "image/png", "data": "<base64-placeholder>"}}]}], "generationConfig": {"imageConfig": {"aspectRatio": "1:1"}}, "systemInstruction": {"role": "user", "parts": [{"text": "You are a helpful assistant."}]} }` |
| **Output shape to verify** | Internal `NormalizedGenerationRequest` has: `model` resolved to a `MODEL_CONFIG` key, `prompt` = systemInstruction + user text, `images` = decoded base64 image bytes (or empty list for text-only) |
| **Compatibility risk** | high |
| **Source references** | `REQUEST_RESPONSE_CONVERSION_MAP.md` §Conversion from Gemini to Internal; `GENERATION_CONTRACT.md` §Gemini-Compatible Request Flow; `routes.py` L454–L481 |
| **Sensitive data notes** | Use synthetic base64 placeholder (short, clearly fake). Synthetic prompt text. |
| **Test-harness priority** | 3 |

---

### FX-CV-002 — Internal/OpenAI-like response to Gemini conversion

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-CV-002` |
| **Endpoint** | `POST /v1beta/models/{model}:generateContent` |
| **Method** | POST |
| **Surface category** | response conversion |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | Internal handler result (OpenAI format): `{ "choices": [{"message": {"content": "![Generated Image](https://placeholder.example.invalid/media/test.jpg)"}, "finish_reason": "stop"}] }` |
| **Output shape to verify** | Gemini format: `{ "candidates": [{"content": {"role": "model", "parts": [{"inlineData": {"mimeType": "image/jpeg", "data": "<base64-placeholder>"}}]}, "finishReason": "STOP", "index": 0}], "modelVersion": "<model>" }` |
| **Compatibility risk** | high |
| **Source references** | `REQUEST_RESPONSE_CONVERSION_MAP.md` §Conversion from Internal/OpenAI-like Response to Gemini Format; `routes.py` L654–L671, L633–L651 |
| **Sensitive data notes** | Use placeholder media URL. Synthetic base64 in output assertion. |
| **Test-harness priority** | 3 |

---

### FX-CV-003 — Streaming conversion: OpenAI chunks to Gemini events

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-CV-003` |
| **Endpoint** | `POST /v1beta/models/{model}:streamGenerateContent` |
| **Method** | POST |
| **Surface category** | streaming conversion |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | Internal OpenAI-format stream chunks: `{"choices":[{"delta":{"reasoning_content":"Uploading..."},"finish_reason":null}]}` → `{"choices":[{"delta":{"content":"![Image](url)"},"finish_reason":"stop"}]}` |
| **Output shape to verify** | Converted Gemini events: `{"candidates":[{"index":0,"content":{"role":"model","parts":[{"text":"Uploading..."}]}}]}` → `{"candidates":[{"index":0,"content":{"role":"model","parts":[{"text":"![Image](url)"}],"finishReason":"STOP"}}]}` |
| **Compatibility risk** | high |
| **Source references** | `REQUEST_RESPONSE_CONVERSION_MAP.md` §Streaming response conversion; `routes.py` L685–L714, L740–L785 |
| **Sensitive data notes** | Use synthetic progress text and placeholder URLs. |
| **Test-harness priority** | 3 |

---

### FX-CX-001 — extend:// video continuation input

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-CX-001` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | custom continuation |
| **Fixture mode** | mocked-internal-response |
| **Input shape to preserve** | `{ "model": "<extend-model-id>", "messages": [{"role": "user", "content": [{"type": "text", "text": "continue this video"}, {"type": "image_url", "image_url": {"url": "extend://test-media-id-placeholder"}}]}], "stream": false }` |
| **Output shape to verify** | Internal `NormalizedGenerationRequest` has `video_media_id = "test-media-id-placeholder"`. Route accepts the `extend://` scheme without error. |
| **Compatibility risk** | medium |
| **Source references** | `API_COMPATIBILITY_NOTES.md` §extend:// Scheme; `GENERATION_CONTRACT.md` §Upload/Media References; `routes.py` L316–L317 |
| **Sensitive data notes** | Use clearly synthetic media ID: `test-media-id-placeholder`. No real upstream media IDs. |
| **Test-harness priority** | 3 |

---

### FX-ER-001 — Representative OpenAI error response

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ER-001` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | error behavior |
| **Fixture mode** | static-doc-example |
| **Input shape to preserve** | `{ "model": "<invalid-model-id>", "messages": [{"role": "user", "content": "test"}], "stream": false }` |
| **Output shape to verify** | `{ "error": { "message": "<str>", "type": "<str>", "code": "generation_failed", "status_code": <int> } }` with HTTP status matching `status_code` |
| **Compatibility risk** | medium |
| **Source references** | `GENERATION_CONTRACT.md` §OpenAI-compatible errors; `routes.py` L516–L525; `generation_handler.py` L2323–L2336 |
| **Sensitive data notes** | No sensitive data. Synthetic error message text. |
| **Test-harness priority** | 2 |

---

### FX-ER-002 — Representative Gemini error response

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ER-002` |
| **Endpoint** | `POST /v1beta/models/{model}:generateContent` |
| **Method** | POST |
| **Surface category** | error behavior |
| **Fixture mode** | static-doc-example |
| **Input shape to preserve** | `{ "contents": [{"role": "user", "parts": [{"text": "test"}]}] }` with an invalid or unavailable model |
| **Output shape to verify** | `{ "error": { "code": <int>, "message": "<str>", "status": "<GEMINI_STATUS_STRING>" } }` — status from `GEMINI_STATUS_MAP` (e.g., 400→INVALID_ARGUMENT, 500→INTERNAL) |
| **Compatibility risk** | medium |
| **Source references** | `GENERATION_CONTRACT.md` §Gemini-compatible errors; `routes.py` L57–L68, L532–L539 |
| **Sensitive data notes** | No sensitive data. Synthetic error message text. |
| **Test-harness priority** | 2 |

---

### FX-ON-004 — Accepted-but-not-forwarded fields

| Field | Value |
|-------|-------|
| **Fixture ID** | `FX-ON-004` |
| **Endpoint** | `POST /v1/chat/completions` |
| **Method** | POST |
| **Surface category** | request normalization |
| **Fixture mode** | static-doc-example |
| **Input shape to preserve** | `{ "model": "<model-id>", "messages": [{"role": "user", "content": "<text>"}], "stream": false, "temperature": 0.7, "max_tokens": 512, "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]} }` |
| **Output shape to verify** | Request is accepted without error. `temperature`, `max_tokens`, and `responseModalities` do not appear in the internal upstream call (observed in source: not forwarded). Response is structurally valid. |
| **Compatibility risk** | medium |
| **Source references** | `REQUEST_RESPONSE_CONVERSION_MAP.md` §OpenAI-Style Request Fields; `GENERATION_CONTRACT.md`; `models.py` L235–L241, L285–L300 |
| **Sensitive data notes** | No sensitive data. Synthetic prompt text. |
| **Test-harness priority** | 3 |

---

## Matrix Summary

| Fixture ID | Endpoint (short) | Category | Mode | Risk | Priority |
|------------|------------------|----------|------|------|----------|
| FX-ML-001 | GET /v1/models | model listing | static-doc-example | high | 1 |
| FX-ML-002 | GET /v1/models/aliases | model aliases | static-doc-example | medium | 2 |
| FX-ML-003 | GET /v1beta/models | model listing | static-doc-example | high | 2 |
| FX-ON-001 | POST /v1/chat/completions (text) | OpenAI non-streaming | mocked-internal-response | high | 1 |
| FX-ON-002 | POST /v1/chat/completions (image) | OpenAI non-streaming | mocked-internal-response | high | 1 |
| FX-ON-003 | POST /v1/chat/completions (video) | OpenAI non-streaming | mocked-internal-response | high | 2 |
| FX-ON-004 | POST /v1/chat/completions (extra fields) | request normalization | static-doc-example | medium | 3 |
| FX-OS-001 | POST /v1/chat/completions (stream) | OpenAI streaming | mocked-internal-response | high | 1 |
| FX-OS-002 | POST /v1/chat/completions (reasoning) | OpenAI streaming | mocked-internal-response | medium | 2 |
| FX-OS-003 | POST /v1/chat/completions ([DONE]) | OpenAI streaming | mocked-internal-response | high | 1 |
| FX-GN-001 | POST ...:generateContent | Gemini non-streaming | mocked-internal-response | high | 1 |
| FX-GS-001 | POST ...:streamGenerateContent | Gemini streaming | mocked-internal-response | high | 2 |
| FX-GS-002 | POST ...:streamGenerateContent (no [DONE]) | Gemini streaming | mocked-internal-response | high | 2 |
| FX-CV-001 | Gemini → internal conversion | request normalization | mocked-internal-response | high | 3 |
| FX-CV-002 | internal → Gemini conversion (non-stream) | response conversion | mocked-internal-response | high | 3 |
| FX-CV-003 | internal → Gemini conversion (stream) | streaming conversion | mocked-internal-response | high | 3 |
| FX-CX-001 | extend:// video continuation | custom continuation | mocked-internal-response | medium | 3 |
| FX-ER-001 | OpenAI error response | error behavior | static-doc-example | medium | 2 |
| FX-ER-002 | Gemini error response | error behavior | static-doc-example | medium | 2 |

**Total planned fixtures:** 19

**Sprint 005A progress:** 3 skeleton fixtures created (FX-ML-001, FX-ON-001, FX-OS-003).

**Sprint 005B progress:** Static shape assertions added for all 3 skeleton fixtures. Route-level behavior is not yet tested.

**Sprint 005C progress:** 3 additional static fixture files created (FX-ON-002, FX-GN-001, FX-OS-002). Assertions not yet added.

**By priority:**
- Priority 1 (first slice): 6 fixtures
- Priority 2: 7 fixtures
- Priority 3: 6 fixtures

**By mode:**
- static-doc-example: 5 fixtures
- mocked-internal-response: 14 fixtures
- runtime-capture-required: 0 (identified in plan but not given fixture IDs yet; see [GENERATION_FIXTURE_PLAN.md](GENERATION_FIXTURE_PLAN.md) §Runtime-Capture-Required Fixture Candidates)
