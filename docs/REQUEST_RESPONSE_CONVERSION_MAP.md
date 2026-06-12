# Request/Response Conversion Map

> **Sprint 003 — Generation Contract Deep Dive**
> Documentation-only. No runtime behavior changes.

## Purpose

This document maps the request and response field conversions between OpenAI-compatible, Gemini-compatible, and internal formats in flow2api. All observations are from source inspection.

## OpenAI-Style Request Fields Observed

The `ChatCompletionRequest` model (`src/core/models.py` L285–L300) accepts:

| Field | Type | Used in generation | Notes |
|-------|------|--------------------| ----|
| `model` | `str` | Yes | Resolved via `resolve_model_name` |
| `messages` | `Optional[List[ChatMessage]]` | Yes | Last message used for prompt + images |
| `stream` | `bool` | Yes | Controls streaming vs. non-streaming |
| `temperature` | `Optional[float]` | No | Accepted but not forwarded to upstream |
| `max_tokens` | `Optional[int]` | No | Accepted but not forwarded to upstream |
| `image` | `Optional[str]` | Yes (deprecated) | URI to image, used if messages have no images |
| `video` | `Optional[str]` | No (deprecated) | Accepted but not observed in generation flow |
| `generationConfig` | `Optional[GenerationConfigParam]` | Yes | Used for model resolution (aspectRatio, imageSize) |
| `contents` | `Optional[List[Any]]` | Yes | Gemini passthrough — delegates to Gemini normalization |
| Extra fields | `ConfigDict(extra="allow")` | Partial | `size`, `quality`, `extra_body` checked by model resolver |

**ChatMessage** (`src/core/models.py` L218–L222):

| Field | Type | Notes |
|-------|------|-------|
| `role` | `str` | `"user"`, `"assistant"`, `"system"` |
| `content` | `Union[str, List[dict]]` | String or multimodal array with `type: "text"` and `type: "image_url"` items |

## Gemini-Style Request Fields Observed

The `GeminiGenerateContentRequest` model (`src/core/models.py` L275–L282):

| Field | Type | Used in generation | Notes |
|-------|------|--------------------| ----|
| `contents` | `List[GeminiContent]` | Yes | Last `"user"` content used for prompt + images |
| `generationConfig` | `Optional[GenerationConfigParam]` | Yes | Used for model resolution |
| `systemInstruction` | `Optional[GeminiContent]` | Yes | Prepended to prompt (unless media model ignores it) |
| Extra fields | `ConfigDict(extra="allow")` | Partial | May carry additional params |

**GeminiContent** (`src/core/models.py` L268–L272):

| Field | Type | Notes |
|-------|------|-------|
| `role` | `Optional[Literal["user", "model"]]` | Defaults to `"user"` if None |
| `parts` | `List[GeminiPart]` | Each part has `text`, `inlineData`, or `fileData` |

**GeminiPart** (`src/core/models.py` L258–L265):

| Field | Type | Notes |
|-------|------|-------|
| `text` | `Optional[str]` | Text content |
| `inlineData` | `Optional[GeminiInlineData]` | Base64 binary data (`mimeType` + `data`) |
| `fileData` | `Optional[GeminiFileData]` | URI reference (`fileUri` + optional `mimeType`) |

**GenerationConfigParam** (`src/core/models.py` L235–L241):

| Field | Type | Notes |
|-------|------|-------|
| `responseModalities` | `Optional[List[str]]` | e.g., `["IMAGE", "TEXT"]` — accepted but not observed to affect generation |
| `imageConfig` | `Optional[ImageConfig]` | `aspectRatio`, `imageSize`, plus extra fields |

## Conversion from Gemini to Internal/OpenAI-like Format

When a Gemini request enters via `/v1/chat/completions` with `contents` field (routes.py L442–L449):

```
GeminiGenerateContentRequest
  → _coerce_gemini_contents(request.contents)
  → _normalize_gemini_request(model, gemini_request)
      → _resolve_request_model(model, request)     # model resolution
      → _extract_prompt_and_images_from_gemini_contents
          → iterate last "user" content parts
          → text parts → joined as prompt
          → inlineData → base64 decoded → image bytes
          → fileData → URL downloaded → image bytes
      → extract systemInstruction text
      → if media model: sanitize prompt, maybe drop systemInstruction
      → prepend systemInstruction to prompt
  → NormalizedGenerationRequest(model, prompt, images)
```

**Observed in:** routes.py L363–L481

When a Gemini request enters via `:generateContent` endpoint (routes.py L892–L935):
- Same normalization path as above
- The model name comes from the URL path parameter

## Conversion from Internal/OpenAI-like Response to Gemini Format

### Non-streaming response conversion

`_build_gemini_success_payload` (routes.py L654–L671):

```
Internal handler result (OpenAI-format JSON):
  {
    "choices": [{"message": {"content": "![Generated Image](url)"}}]
  }

→ _extract_openai_message_content(payload)
    → extracts choices[0].message.content string

→ _build_gemini_parts_from_output(output)
    → detects markdown images → inlineData parts (downloaded + base64 encoded)
    → detects HTML video tags → fileData parts
    → otherwise → text part

→ Final Gemini response:
  {
    "candidates": [{
      "content": {"role": "model", "parts": [...]},
      "finishReason": "STOP",
      "index": 0
    }],
    "modelVersion": "{resolved_model}"
  }
```

### Streaming response conversion

`_convert_openai_stream_chunk_to_gemini_event` (routes.py L685–L714):

```
OpenAI chunk:
  {"choices": [{"delta": {"reasoning_content": "..."}, "finish_reason": null}]}

→ extract text from delta.reasoning_content or delta.content
→ _normalize_finish_reason(finish_reason)
    → "stop" → "STOP"
    → "length" → "MAX_TOKENS"
    → "content_filter" → "SAFETY"

→ Gemini event:
  {"candidates": [{"index": 0, "content": {"role": "model", "parts": [...]}, "finishReason": "..."}], "modelVersion": "..."}

→ Wrapped as: "data: {json}\n\n"
```

**Image/video parts in streaming:** `_build_gemini_parts_from_output` is called per-chunk, so each text chunk is checked for markdown image/video patterns. This means image URLs in streaming Gemini responses may be converted to `inlineData` (downloaded and base64-encoded) on the fly.

## Streaming Conversion Boundaries

The internal generation handler appears to produce OpenAI-format chunks in all observed paths. Conversion to Gemini format happens at the route layer:

```
GenerationHandler.handle_generation(stream=True)
  → yields OpenAI-format "data: {json}\n\n" strings

For OpenAI endpoint (/v1/chat/completions):
  → _iterate_openai_stream
      → pass-through if starts with "data: "
      → re-wrap if not
      → append "data: [DONE]\n\n"

For Gemini endpoint (:streamGenerateContent):
  → _iterate_gemini_stream
      → strip "data: " prefix
      → skip "[DONE]" sentinel
      → parse JSON
      → convert via _convert_openai_stream_chunk_to_gemini_event
      → errors → Gemini error format + stream termination
```

**Key boundary:** The handler emits `reasoning_content` for progress updates and `content` for the final result. The Gemini converter prefers `reasoning_content` over `content` (routes.py L695), so progress messages are preserved in the Gemini stream.

## Fields That Must Not Be Renamed Casually

These field names are part of the external API contract:

### OpenAI-compatible (inbound)

- `model`, `messages`, `stream`, `temperature`, `max_tokens` — standard OpenAI fields
- `content` (in messages), `role`, `type`, `text`, `image_url`, `url` — multimodal message structure
- `image` — flow2api-specific extension (deprecated but still used)
- `generationConfig`, `contents` — Gemini passthrough fields accepted in OpenAI endpoint

### OpenAI-compatible (outbound)

- `id`, `object`, `created`, `model`, `choices`, `message`, `delta`, `content`, `role`, `finish_reason`, `index` — standard ChatCompletion fields
- `reasoning_content` — custom extension in streaming delta
- `error`, `message`, `type`, `code`, `status_code` — error response fields
- `url` — flow2api-specific direct URL field added to response

### Gemini-compatible (inbound)

- `contents`, `role`, `parts`, `text`, `inlineData`, `mimeType`, `data`, `fileData`, `fileUri` — standard Gemini fields
- `generationConfig`, `responseModalities`, `imageConfig`, `aspectRatio`, `imageSize`
- `systemInstruction`

### Gemini-compatible (outbound)

- `candidates`, `content`, `role`, `parts`, `finishReason`, `index`, `modelVersion` — standard Gemini response fields
- `inlineData`, `fileData`, `text` — part types
- `error`, `code`, `message`, `status` — Gemini error format
- `name`, `displayName`, `description`, `version`, `inputTokenLimit`, `outputTokenLimit`, `supportedGenerationMethods` — model resource fields

### Internal (between route and handler)

- `NormalizedGenerationRequest` fields: `model`, `prompt`, `images`, `messages`, `video_media_id`
- `MODEL_CONFIG` entry fields: `type`, `model_name`, `model_key`, `aspect_ratio`, `video_type`, `supports_images`, `upsample`, etc.

## Unknowns and Fixtures Needed

1. **`responseModalities` field** — accepted in `GenerationConfigParam` but not observed to influence generation behavior; to be confirmed whether upstream honors it
2. **`temperature` and `max_tokens`** — accepted in `ChatCompletionRequest` but not forwarded; clients may expect these to work for text models
3. **Extra field passthrough** — `ConfigDict(extra="allow")` permits arbitrary fields; which extras upstream clients actually send is unknown
4. **Gemini `safetySettings`** — not observed in the request model; real Gemini API supports it; absence may cause compatibility issues with some clients
5. **Gemini `tools` / `toolConfig`** — not observed in request model; the system instruction sanitizer strips `<tools>` blocks (routes.py L267–L286), suggesting some upstream proxy may inject tool definitions
6. **`extend://` protocol** — custom URI scheme for video continuation; not a standard OpenAI or Gemini convention
7. **Image part download in streaming Gemini conversion** — `_build_gemini_parts_from_output` downloads images during streaming conversion; latency impact and failure mode need fixture testing
8. **Direct URL enrichment for Gemini** — `_enrich_payload_with_direct_url` adds a `url` field before Gemini conversion; its interaction with `_build_gemini_parts_from_output` needs verification
