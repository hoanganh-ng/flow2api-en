# Generation Contract

> **Sprint 003 — Generation Contract Deep Dive**
> Documentation-only. No runtime behavior changes.

## Purpose

This document captures the observed generation contract for flow2api — the path from an incoming OpenAI-compatible or Gemini-compatible HTTP request through to the upstream Flow API call and back. It is based on source inspection only and uses cautious wording ("observed in source", "appears to") where behavior has not been confirmed by runtime fixtures.

## Source Files Inspected

| File | Lines | Role |
|------|-------|------|
| `src/api/routes.py` | 1–1003 | HTTP route entrypoints, request normalization, response shaping, SSE streaming |
| `src/core/models.py` | 1–301 | Pydantic request/response models |
| `src/core/model_resolver.py` | 1–634 | Alias resolution: simplified model name + generationConfig → internal MODEL_CONFIG key |
| `src/services/generation_handler.py` | 1–2467 | `MODEL_CONFIG` registry, `GenerationHandler.handle_generation`, image/video pipelines, response formatting |
| `src/services/flow_client.py` | 1–3123 | Upstream Flow API client: upload, image generation, video generation, polling |
| `src/core/account_tiers.py` | (referenced) | Paygate tier checks and model-tier gating |
| `src/services/file_cache.py` | (referenced) | Local file caching for generated media |
| `src/core/auth.py` | (referenced) | API key verification dependency |

## Generation Route Entrypoints

### 1. POST /v1/chat/completions (OpenAI-compatible)

- **Observed in:** `src/api/routes.py` L850–L889
- **Request model:** `ChatCompletionRequest` (defined in `src/core/models.py` L285–L300)
- **Key fields:** `model`, `messages` (optional), `stream` (bool, default False), `contents` (optional Gemini passthrough), `generationConfig` (optional), `image` (deprecated), `temperature`, `max_tokens`
- **Auth:** `verify_api_key_flexible` dependency
- **Flow:**
  1. Normalize request via `_normalize_openai_request` → `NormalizedGenerationRequest`
  2. Resolve model name via `_resolve_request_model` → `resolve_model_name`
  3. If `stream=True` → `StreamingResponse` with `_iterate_openai_stream` (media_type `text/event-stream`)
  4. If `stream=False` → collect all chunks via `_collect_non_stream_result`, parse JSON, return `JSONResponse`

### 2. POST /v1beta/models/{model}:generateContent (Gemini-compatible)

- **Observed in:** `src/api/routes.py` L892–L935
- **Also mounted at:** `/models/{model}:generateContent`
- **Request model:** `GeminiGenerateContentRequest` (defined in `src/core/models.py` L275–L282)
- **Key fields:** `contents` (List[GeminiContent]), `generationConfig` (optional), `systemInstruction` (optional)
- **Flow:**
  1. Normalize via `_normalize_gemini_request` → `NormalizedGenerationRequest`
  2. Collect non-stream result
  3. Enrich payload with direct URL via `_enrich_payload_with_direct_url`
  4. If error → Gemini error response; otherwise → `_build_gemini_success_payload`

### 3. POST /v1beta/models/{model}:streamGenerateContent (Gemini-compatible streaming)

- **Observed in:** `src/api/routes.py` L938–L973
- **Also mounted at:** `/models/{model}:streamGenerateContent`
- **Query param:** `alt` (optional, observed but not actively used in the handler logic)
- **Flow:**
  1. Normalize via `_normalize_gemini_request`
  2. Return `StreamingResponse` with `_iterate_gemini_stream` (media_type `text/event-stream`)

## OpenAI-Compatible Request Flow

```
Client POST /v1/chat/completions
  → verify_api_key_flexible (auth)
  → _normalize_openai_request(request)
      → if messages present:
          → _extract_prompt_and_images_from_openai_messages
              → parses last message content (string or multimodal array)
              → extracts image_url items → downloads images
              → detects extend://MEDIA_ID for video continuation
          → _resolve_request_model(model, request)
          → _append_openai_reference_images (for image models, scans history)
      → if contents present (Gemini passthrough):
          → delegates to _normalize_gemini_request path
  → if stream:
      → StreamingResponse(_iterate_openai_stream)
  → else:
      → _collect_non_stream_result → JSONResponse
```

**Observed in:** `src/api/routes.py` L423–L451, L850–L889

## Gemini-Compatible Request Flow

```
Client POST /v1beta/models/{model}:generateContent
  → verify_api_key_flexible (auth)
  → _normalize_gemini_request(model, request)
      → _resolve_request_model(model, request)
      → _extract_prompt_and_images_from_gemini_contents
          → finds last "user" role content
          → extracts text parts, inlineData (base64 images), fileData (URL images)
      → extracts systemInstruction text
      → if media model: sanitize prompt and optionally drop systemInstruction
      → prepend systemInstruction to prompt
  → _collect_non_stream_result
  → _build_gemini_success_payload
      → extracts OpenAI-style choices[0].message.content
      → converts to Gemini candidates[0].content.parts (inlineData/fileData/text)
```

**Observed in:** `src/api/routes.py` L454–L481, L892–L935, L654–L671

## Shared Generation Handler Flow

The `GenerationHandler.handle_generation` async generator (`src/services/generation_handler.py` L1026–L1381) is the single unified generation entrypoint for both OpenAI and Gemini routes.

**High-level sequence:**

1. **Model validation** — checks `model` against `MODEL_CONFIG` dict (L1063)
2. **Token selection** — `load_balancer.select_token` (L1103–L1118)
3. **Token AT validation** — `token_manager.ensure_valid_token` (L1172)
4. **Tier gate** — `supports_model_for_tier` check (L1186)
5. **Project ensure** — `token_manager.ensure_project_exists` (L1197)
6. **Remote browser prefill** — `flow_client.prefill_remote_browser_pool` (L1208)
7. **Branch by type:**
   - Image → `_handle_image_generation` (L1218)
   - Video → `_handle_video_generation` (L1229)
8. **Post-generation:** record usage, log request, handle errors

### Image Generation Sub-flow

**Observed in:** `src/services/generation_handler.py` L1391–L1672

1. Upload input images via `flow_client.upload_image` (if any)
2. Call `flow_client.generate_image` → returns `(result, session_id, perf_trace)`
3. Extract `fifeUrl` from `result.media[0].image.generatedImage.fifeUrl`
4. If upsample configured → `flow_client.upsample_image` → cache result locally
5. If cache enabled → `file_cache.download_and_cache` → local URL
6. Yield completion response (stream chunk or full JSON)

### Video Generation Sub-flow

**Observed in:** `src/services/generation_handler.py` L1674–L1958

1. Determine `video_type`: `t2v`, `i2v`, `r2v`, or `extend`
2. Tier-based model key adjustment (`_resolve_video_model_key_for_tier`)
3. Upload images if applicable (I2V: start/end frames; R2V: reference images)
4. Call appropriate `flow_client` method:
   - T2V → `generate_video_text`
   - I2V (2 frames) → `generate_video_start_end`
   - I2V (1 frame) → `generate_video_start_image`
   - R2V → `generate_video_reference_images`
   - Extend → `generate_video_extend`
5. Extract `task_id` from `operations[0].operation.name`
6. Poll via `_poll_video_result` async generator (L1960)

## Where Upstream Flow Client Behavior Begins

The `FlowClient` class (`src/services/flow_client.py` L24) handles all communication with the upstream Google/Flow API:

- **Base URLs:** `config.flow_labs_base_url` (labs.google/fx/api) and `config.flow_api_base_url` (aisandbox-pa.googleapis.com/v1)
- **Image generation:** `POST {api_base_url}/projects/{project_id}/flowMedia:batchGenerateImages` (L1004)
- **Image upload:** `POST {api_base_url}/flow/uploadImage` with fallback to `{api_base_url}:uploadUserImage` (L850–L968)
- **Video generation:** Various endpoints for T2V, I2V, R2V, Extend (L1464+)
- **Auth:** Uses Access Token (AT) derived from Session Token (ST)
- **CAPTCHA:** reCAPTCHA token acquired per attempt via `_get_recaptcha_token`
- **Retries:** Up to `config.flow_max_retries` attempts with CAPTCHA re-solve

## Non-Streaming Response Observations

### OpenAI-compatible non-streaming response

- **Shape:** Standard ChatCompletion response (`src/services/generation_handler.py` L2282–L2321)
  ```
  {
    "id": "chatcmpl-{timestamp}",
    "object": "chat.completion",
    "created": {timestamp},
    "model": "flow2api",
    "choices": [{
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }]
  }
  ```
- **Image content:** Formatted as `![Generated Image]({url})`
- **Video content:** Formatted as `` ```html\n<video src='{url}' controls></video>\n``` ``
- **Observed in:** `_create_completion_response` at L2282

### Gemini-compatible non-streaming response

- **Shape:** Built by `_build_gemini_success_payload` (routes.py L654–L671)
  ```
  {
    "candidates": [{
      "content": {"role": "model", "parts": [...]},
      "finishReason": "STOP",
      "index": 0
    }],
    "modelVersion": "{model}"
  }
  ```
- **Parts conversion:** `_build_gemini_parts_from_output` (routes.py L633–L651) detects markdown images → `inlineData`, HTML video tags → `fileData`, otherwise → `text`

## Error Response Observations

### OpenAI-compatible errors

- **Shape:** `{"error": {"message": "...", "type": "...", "code": "generation_failed", "status_code": N}}`
- **Observed in:** `_create_error_response` at L2323–L2336
- **Status code mapping:** `_get_error_status_code` extracts `error.status_code` from payload (routes.py L516–L525)

### Gemini-compatible errors

- **Shape:** `{"error": {"code": N, "message": "...", "status": "STATUS_STRING"}}`
- **Status string map:** `GEMINI_STATUS_MAP` at routes.py L57–L68
  - 400 → INVALID_ARGUMENT, 401 → UNAUTHENTICATED, 403 → PERMISSION_DENIED, 429 → RESOURCE_EXHAUSTED, 500 → INTERNAL, etc.
- **Observed in:** `_build_gemini_error_payload` at routes.py L532–L539

## Upload/Media References

Generation depends on media upload for image-to-image and image-to-video flows:

- **Upload endpoint:** `flow_client.upload_image` (flow_client.py L820–L972)
  - New API: `POST {api_base_url}/flow/uploadImage`
  - Legacy fallback: `POST {api_base_url}:uploadUserImage` (disabled when project-scoped)
  - Returns `mediaId` (a.k.a. `media.name` or `mediaGenerationId`)
- **Image input type:** For image generation, images are tagged as `IMAGE_INPUT_TYPE_REFERENCE`
- **Video image input:** I2V uses start/end media IDs; R2V uses `IMAGE_USAGE_TYPE_ASSET` references
- **Video extend:** Uses `extend://MEDIA_ID` protocol in OpenAI `image_url` field (routes.py L316–L317)

## High-Risk Unknowns for Later Fixture Tests

1. **Exact upstream response shape** from `batchGenerateImages` — only the `media[0].image.generatedImage.fifeUrl` path is observed; full schema unknown
2. **Video polling response shape** — `_poll_video_result` handles multiple states; exact upstream operation status schema not fully documented
3. **Upsample response format** — `upsample_image` returns base64-encoded image; exact response envelope unknown
4. **Error propagation fidelity** — how upstream 403/reCAPTCHA errors map to client-visible error codes needs fixture verification
5. **Streaming chunk ordering** — the interleaving of progress/status chunks with actual content chunks is observed but not contractually specified
6. **`extend://` protocol** — appears to be a custom convention; upstream compatibility unknown
7. **`generationConfig` passthrough** — extra fields allowed via `ConfigDict(extra="allow")`; which fields upstream actually honors is untested
8. **Model name edge cases** — resolver fallback behavior when a resolved name is not in `MODEL_CONFIG` (returns original name, which then fails validation)
