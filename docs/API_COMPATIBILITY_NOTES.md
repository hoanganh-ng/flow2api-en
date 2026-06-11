# API Compatibility Notes

> **Status:** Documentation-only observations. No runtime behavior has been changed or tested.
> **Sprint:** 002 — API Surface Inventory
> **Last updated:** 2025 (Sprint 002)

---

## Purpose

This document identifies behavior that downstream clients are likely to depend on.
It is intended to guide a future fixture-based compatibility test harness.
All observations use cautious language because they are based on static source
inspection, not on verified runtime behavior.

---

## Endpoints Likely Expected by OpenAI-Compatible Clients

### POST /v1/chat/completions

Observed in source (`src/api/routes.py` line 850).

This is the single entry point that OpenAI SDK and compatible libraries will call
for all generation tasks (text-to-image, text-to-video, image-to-video, etc.).

Clients likely depend on:

- Standard `ChatCompletionRequest` fields: `model`, `messages`, `stream`, `temperature`, `max_tokens`.
- The `messages` array supporting both plain text content and multimodal content
  (array of `{ type: "text", text: ... }` and `{ type: "image_url", image_url: { url: ... } }` items).
- The `model` field accepting string model identifiers returned by `/v1/models`.
- Non-streaming response: standard OpenAI chat completion JSON envelope
  (`{ id, object: "chat.completion", choices: [{ message: { role, content }, finish_reason }] }`).
- Streaming response: SSE `data: {json}\n\n` format with delta chunks and final `data: [DONE]\n\n`.

**Compatibility risk: high.** Any deviation from the standard envelope (field names,
nesting, status codes) will break OpenAI SDK integrations.

### GET /v1/models

Observed in source (`src/api/routes.py` line 788).

Clients likely depend on:

- Response shape: `{ "object": "list", "data": [{ "id", "object": "model", "owned_by" }] }`.
- Each model `id` being a valid model identifier accepted by `/v1/chat/completions`.

**Compatibility risk: high.** The `owned_by` field is observed to always be `"flow2api"` —
this is non-standard but unlikely to cause breakage. The `description` field is an
additive extension not present in official OpenAI responses.

---

## Endpoints Likely Expected by Gemini-Compatible Clients

### POST /v1beta/models/{model}:generateContent

Observed in source (`src/api/routes.py` line 892).

Clients likely depend on:

- Standard Gemini `GenerateContentRequest` body: `{ contents, generationConfig, systemInstruction }`.
- Response shape: Gemini `GenerateContentResponse` with `candidates[].content.parts[]`.
- Parts containing `inlineData` (for images) or `fileData` (for videos) or `text`.
- Error envelope: `{ error: { code, message, status } }` where status is a Gemini status string.

**Compatibility risk: high.** The response shape conversion from internal OpenAI format
to Gemini format (observed in `_build_gemini_success_payload`) must faithfully reproduce
the expected Gemini envelope.

### POST /v1beta/models/{model}:streamGenerateContent

Observed in source (`src/api/routes.py` line 938).

Clients likely depend on:

- SSE streaming with Gemini-shaped delta chunks.
- Each chunk having `candidates[].content.parts[]` and optional `finishReason`.
- The `modelVersion` field in each chunk.

**Compatibility risk: high.** The internal conversion from OpenAI stream chunks to
Gemini-shaped events (observed in `_convert_openai_stream_chunk_to_gemini_event`)
is a critical compatibility layer.

### GET /v1beta/models and GET /models

Observed in source (`src/api/routes.py` lines 822–823).

Clients likely depend on:

- Response shape: `{ models: [{ name, displayName, description, version, supportedGenerationMethods }] }`.
- `supportedGenerationMethods` including `"generateContent"` and `"streamGenerateContent"`.

**Compatibility risk: medium.** The `version` field is always `"flow2api"` (observed
in `_build_gemini_model_resource`), which differs from official Gemini API version strings.
Clients that validate this field may need adjustment.

### Auth: `x-goog-api-key` header and `?key=` query param

Observed in source (`src/core/auth.py` line 44).

Gemini SDK clients typically send the API key via the `x-goog-api-key` header or
`?key=` query parameter, not via `Authorization: Bearer`. This endpoint appears to
support both mechanisms.

**Compatibility risk: high.** Removing or changing these auth channels would break
official Gemini SDK integrations.

---

## Request Fields That Appear Compatibility-Sensitive

### OpenAI Request (`ChatCompletionRequest`)

Observed in source (`src/core/models.py` line 285).

| Field | Compatibility Sensitivity | Notes |
|-------|--------------------------|-------|
| `model` | high | Must match `/v1/models` IDs; aliases resolved via `model_resolver.py` |
| `messages` | high | Standard OpenAI chat messages format; multimodal content arrays supported |
| `stream` | high | Boolean; controls SSE vs JSON response |
| `temperature` | medium | Accepted but behavior depends on upstream model |
| `max_tokens` | medium | Accepted but behavior depends on upstream model |
| `image` | low | Deprecated field; appears to be a legacy shortcut |
| `video` | low | Deprecated field |
| `generationConfig` | medium | Gemini extension field; enables model resolution via `responseModalities` and `imageConfig` |
| `contents` | medium | Gemini native contents; allows Gemini-shaped requests on OpenAI endpoint |
| Extra fields | medium | `ConfigDict(extra="allow")` — clients may send additional fields that are silently ignored |

### Gemini Request (`GeminiGenerateContentRequest`)

Observed in source (`src/core/models.py` line 275).

| Field | Compatibility Sensitivity | Notes |
|-------|--------------------------|-------|
| `contents` | high | List of `GeminiContent` with `role` and `parts` |
| `generationConfig` | high | `responseModalities` and `imageConfig` affect model resolution |
| `systemInstruction` | medium | GeminiContent; may be prepended to prompt or ignored for media models |

### `generationConfig.imageConfig`

Observed in source (`src/core/models.py` line 225).

| Field | Compatibility Sensitivity | Notes |
|-------|--------------------------|-------|
| `aspectRatio` | high | Values: "16:9", "9:16", "1:1", "4:3", "3:4" — likely affects upstream generation |
| `imageSize` | medium | Values: "2k", "4k" — may affect output resolution |

---

## Response Fields That Appear Compatibility-Sensitive

### OpenAI Chat Completion Response

The internal handler result is parsed and returned directly. Observed fields
(depends on `GenerationHandler.handle_generation` output):

- `choices[].message.content` — contains markdown image links or HTML video tags
- `choices[].finish_reason` — observed values: "stop"
- `url` — additive field containing extracted media URL (observed in `_enrich_payload_with_direct_url`)

**Compatibility sensitivity: high.** OpenAI clients typically read `choices[0].message.content`.
The additive `url` field is a convenience extension.

### Gemini GenerateContent Response

Observed in source (`src/api/routes.py` lines 654–671, `_build_gemini_success_payload`).

- `candidates[0].content.role` = `"model"`
- `candidates[0].content.parts[]` — may contain `inlineData`, `fileData`, or `text`
- `candidates[0].finishReason` = `"STOP"`
- `modelVersion` — resolved model name

**Compatibility sensitivity: high.** Gemini SDK clients depend on the `candidates` array
structure and `parts` format.

---

## Streaming / SSE Behavior That Must Be Preserved

### OpenAI Streaming (`/v1/chat/completions` with `stream: true`)

Observed in source (`src/api/routes.py` lines 717–737, `_iterate_openai_stream`).

- Media type: `text/event-stream`
- Response headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- Each chunk: `data: {json}\n\n` where json is OpenAI-shaped delta
- Termination: `data: [DONE]\n\n`
- Chunks pass through directly from the generation handler when they start with `data: `
- Non-`data:` chunks are JSON-wrapped

### Gemini Streaming (`/v1beta/models/{model}:streamGenerateContent`)

Observed in source (`src/api/routes.py` lines 740–785, `_iterate_gemini_stream`).

- Same media type and headers
- Each chunk: `data: {json}\n\n` where json is Gemini-shaped `{ candidates: [...], modelVersion: "..." }`
- No `[DONE]` terminator observed — stream ends after last chunk
- Error chunks are emitted inline as Gemini error payloads (stream then terminates)
- Internal OpenAI-shaped chunks are converted via `_convert_openai_stream_chunk_to_gemini_event`

**Compatibility sensitivity: high.** Any change to SSE framing, chunk format, or
termination behavior will break streaming clients.

---

## Upload / Media Behavior That Must Be Preserved

### Inline Image Handling

Observed in source (`src/api/routes.py` lines 147–236).

- **Data URLs:** `data:image/...;base64,...` — decoded inline
- **HTTP/HTTPS URLs:** Fetched via `retrieve_image_data()` using `curl_cffi`
- **Local `/tmp/` URLs:** Read from local file cache first, then fall back to HTTP fetch
- **MIME detection:** Magic-byte based for JPEG/PNG/GIF/WebP; fallback to guessed MIME type

### `extend://` Scheme

Observed in source (`src/api/routes.py` line 316).

- `image_url` values starting with `extend://` are treated as video media IDs for
  video continuation workflows. This is a custom scheme not standard to OpenAI or Gemini.

### File Cache Serving

Observed in source (`src/main.py` line 209).

- Generated media files are saved to `tmp/` directory and served via `StaticFiles` mount at `/tmp`.
- URLs in response content point to this mount path (e.g., `http://host/tmp/filename.mp4`).

**Compatibility sensitivity: high.** The URL format and file availability are critical
for clients that download generated media.

---

## Admin API Behavior That Should Be Documented Separately Before Changes

1. **Dual endpoint aliases:** Multiple admin endpoints have paired aliases
   (e.g., `/api/config/proxy` and `/api/proxy/config`). Both may be used by the
   existing frontend. To be confirmed during fixture/test harness sprint.

2. **Response envelope inconsistency:** Some admin endpoints return
   `{ success: true, message: "..." }` while others use FastAPI's default
   `{ detail: "..." }` for errors. To be confirmed.

3. **Hot-reload behavior:** Many admin config endpoints trigger
   `db.reload_config_to_memory()` after updates. This in-memory synchronization
   pattern affects runtime state without restart. To be confirmed.

4. **Admin session token storage:** In-memory `set()` (admin.py line 38).
   Tokens are lost on server restart. No expiration mechanism observed.
   To be confirmed.

5. **Plugin connection token:** `/api/plugin/update-token` uses a separate auth
   mechanism (connection_token) distinct from both admin tokens and API keys.
   To be confirmed.

---

## Areas Requiring Fixture-Based Verification Later

1. **Exact response JSON for `/v1/chat/completions`** — both streaming and non-streaming,
   for each model type (image, video). Requires running generation handler with mock upstream.

2. **Exact response JSON for Gemini `generateContent`** — verify the `candidates[].content.parts[]`
   structure matches official Gemini SDK expectations for each media type.

3. **Model resolution behavior** — verify that `generationConfig.responseModalities` and
   `generationConfig.imageConfig` correctly route to the intended model.
   Source: `src/core/model_resolver.py` (not fully inspected in this sprint).

4. **Error response format consistency** — verify that all error paths return the expected
   envelope (OpenAI vs Gemini) with correct HTTP status codes.

5. **SSE stream format** — verify exact byte-level SSE framing (newline handling, JSON encoding,
   `[DONE]` presence/absence) matches client expectations.

6. **Image fetch fallback chain** — verify the local-cache → proxy → direct-fetch chain
   behaves correctly under various network conditions.

7. **`extend://` video continuation** — verify the full lifecycle of video extension requests.

8. **WebSocket `/captcha_ws` message protocol** — extract and document the exact message schema
   for extension-based captcha solving.

9. **Prometheus metrics names** — enumerate all metric names and labels for monitoring compatibility.

10. **Admin API response shapes** — document exact JSON shapes for all admin endpoints
    to support frontend compatibility testing.

---

## Cautious Language Note

All observations in this document are based on static source inspection using
`grep` and file reads. No runtime testing, fixture execution, or client integration
testing has been performed. Statements use "observed in source," "appears to,"
and "to be confirmed during fixture/test harness sprint" to reflect this limitation.
