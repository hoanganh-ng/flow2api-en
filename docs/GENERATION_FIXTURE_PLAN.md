# Generation Fixture Plan

> **Sprint 004 — Generation Fixture Plan**
> Documentation-only planning document. No runtime behavior changes.
> No executable fixtures or test harness code have been created.

---

## Purpose

This document outlines a planned fixture strategy for future compatibility testing
of the flow2api generation surface. It identifies which endpoints, request shapes,
response shapes, and streaming behaviors are candidates for fixture-based verification,
and classifies them by implementation mode and priority.

The goal is to prepare a roadmap so that a future test-harness sprint can proceed
without re-deriving scope from earlier documentation.

---

## Scope

This plan covers the generation-related API surfaces identified in Sprint 002
([API_SURFACE_INVENTORY.md](../API_SURFACE_INVENTORY.md),
[API_ENDPOINT_INDEX.md](../API_ENDPOINT_INDEX.md)) and Sprint 003
([GENERATION_CONTRACT.md](../GENERATION_CONTRACT.md),
[STREAMING_CONTRACT_NOTES.md](../STREAMING_CONTRACT_NOTES.md),
[MODEL_COMPATIBILITY_MAP.md](../MODEL_COMPATIBILITY_MAP.md),
[REQUEST_RESPONSE_CONVERSION_MAP.md](../REQUEST_RESPONSE_CONVERSION_MAP.md)).

Specifically:

- `GET /v1/models`
- `GET /v1/models/aliases`
- `GET /v1beta/models` (and `/models` duplicate mount)
- `POST /v1/chat/completions` (non-streaming and streaming)
- `POST /v1beta/models/{model}:generateContent`
- `POST /v1beta/models/{model}:streamGenerateContent`
- Internal request normalization and response conversion layers
- `extend://` video continuation behavior (observed in source, routes.py L316)
- Streaming termination differences (OpenAI `data: [DONE]` vs. Gemini no sentinel)
- `reasoning_content` progress message format
- Representative error responses

---

## Non-Goals

The following are explicitly out of scope for this planning document and for any
future fixture implementation that follows this plan:

- Real upstream response captures containing real tokens, cookies, account identifiers,
  session tokens, or personally identifying data
- Executable test harness code (this is a plan only)
- Admin API fixtures (token management, proxy config, captcha config, plugin config)
- WebSocket `/captcha_ws` message protocol fixtures
- Health/metrics endpoint fixtures
- Static file serving fixtures
- Runtime behavior changes of any kind
- Source code modifications
- Translation of any files
- Refactoring or feature additions
- Bypass, evasion, or upstream-protection avoidance instructions

---

## Fixture Design Principles

1. **Sanitization first.** All fixture data must be free of real credentials, tokens,
   cookies, account IDs, session identifiers, upstream secrets, and personally
   identifying information. Use clearly synthetic placeholder values throughout.

2. **Shape over content.** Fixtures verify structural compatibility (field names,
   nesting, types, presence/absence), not semantic correctness of generated media.

3. **Boundary-level only.** Token selection, captcha solving, browser automation,
   proxy routing, and session lifecycle are boundary-level concerns. Fixtures should
   mock these at the boundary, not attempt to reproduce them.

4. **Cautious wording.** Fixture descriptions use "planned fixture," "observed in source
   docs," "to be confirmed during fixture implementation," and "runtime capture required"
   to reflect that behavior has not been verified by runtime testing.

5. **Reproducibility.** Static and mocked fixtures should be fully reproducible without
   network access or upstream service availability.

6. **Fork-unofficial status.** The fork is clearly unofficial. Fixtures do not imply
   endorsement by or affiliation with the upstream project or Google.

---

## Sanitization Requirements

All fixture data must satisfy the following before being committed to the repository:

| Category | Requirement |
|----------|-------------|
| API keys | Replace with `test-api-key-placeholder` or equivalent |
| Access tokens | Replace with `test-at-placeholder` |
| Session tokens | Replace with `test-st-placeholder` |
| Admin tokens | Replace with `test-admin-token-placeholder` |
| Connection tokens | Replace with `test-connection-token-placeholder` |
| Cookies | Omit entirely or replace with `test-cookie-placeholder` |
| Account IDs / emails | Replace with `test-account@example.invalid` or synthetic ID |
| Project IDs | Replace with `test-project-id` |
| Upstream URLs | Replace host with `upstream-placeholder.example.invalid` |
| Media URLs | Replace with `https://placeholder.example.invalid/media/test.jpg` |
| IP addresses | Use RFC 5737 documentation range (e.g., `192.0.2.1`) |
| Timestamps | Use fixed epoch values (e.g., `1700000000`) |
| `fifeUrl` / media IDs | Replace with synthetic placeholder strings |
| reCAPTCHA tokens | Replace with `test-recaptcha-token-placeholder` |

A pre-commit check (future implementation) should scan fixture files for patterns
matching real credential formats before they are added.

---

## Fixture Categories

### Static Fixture Candidates

Fixtures that can be constructed entirely from source inspection and documented
contracts, without requiring any runtime capture.

- Model listing response shapes (`/v1/models`, `/v1/models/aliases`, `/v1beta/models`)
- Request body shapes for each supported endpoint
- Error response envelopes (OpenAI format, Gemini format)
- Gemini model resource shape (single model lookup)

### Mocked-Internal-Response Fixture Candidates

Fixtures that represent the internal handler output format (observed in source)
and are intended to exercise the route-layer conversion logic without calling
upstream services.

- OpenAI non-streaming text completion response
- OpenAI non-streaming image result response (markdown image format)
- OpenAI non-streaming video result response (HTML video tag format)
- OpenAI streaming text chunks (progress + final content + `[DONE]`)
- Gemini non-streaming response (converted from internal OpenAI format)
- Gemini streaming events (converted from internal OpenAI chunks)
- `reasoning_content` progress messages (OpenAI stream delta)
- Internal OpenAI-to-Gemini response conversion (non-streaming)
- `extend://` video continuation request shape

### Runtime-Capture-Required Fixture Candidates

Fixtures that cannot be reliably constructed from source inspection alone and
will require a live (or carefully mocked) upstream service to capture.

- Full upstream `batchGenerateImages` response shape (observed field path:
  `media[0].image.generatedImage.fifeUrl`; full schema unknown)
- Video polling operation status progression (observed in `_poll_video_result`,
  generation_handler.py L1960+; exact state schema unknown)
- Upsample response format (base64 image; exact envelope unknown)
- Exact streaming chunk timing and ordering for image vs. video generation
- Token selection and load balancer output under various configurations
- File cache naming conventions for generated media

---

## First Implementation Priority

Based on compatibility risk (from Sprint 002/003) and client-impact likelihood,
the recommended first fixture implementation priority is:

1. **`POST /v1/chat/completions` non-streaming text completion** — highest client
   dependency; standard OpenAI envelope must be structurally correct
2. **`POST /v1/chat/completions` streaming text** — SSE framing, delta chunk shape,
   `[DONE]` sentinel are all client-critical
3. **`GET /v1/models`** — model discovery; first call most clients make
4. **`POST /v1/chat/completions` image result formatting** — primary media output
   for OpenAI-compatible clients
5. **`POST /v1beta/models/{model}:generateContent` non-streaming** — Gemini SDK
   clients depend on `candidates[].content.parts[]` structure
6. **Gemini stream termination (no `[DONE]` sentinel)** — behavioral difference
   that may cause client hangs if not preserved
7. **Representative error response (OpenAI and Gemini)** — error handling paths

---

## Risks and Unknowns

1. **Upstream response schema uncertainty.** The full upstream `batchGenerateImages`
   response schema is unknown. Fixtures based on partial field paths
   (`media[0].image.generatedImage.fifeUrl`) may miss required fields or misrepresent
   nesting. Runtime capture is required to confirm.

2. **Video polling state machine.** The exact sequence of operation states
   (pending, running, complete, failed) and their response shapes are observed in
   source but not exhaustively documented. To be confirmed during fixture
   implementation.

3. **Chunk ordering non-determinism.** Progress/status chunks are interleaved with
   content chunks based on upstream polling intervals. Fixture-based tests may need
   to be order-tolerant or use a normalized comparison approach.

4. **`extend://` protocol stability.** The custom URI scheme is a flow2api convention,
   not standard OpenAI or Gemini behavior. Clients that depend on it are already
   coupling to a non-standard extension. Fixture tests should verify the input is
   accepted and the internal routing is correct, but cannot verify upstream handling.

5. **`generationConfig` passthrough fields.** `responseModalities`, `temperature`,
   `max_tokens`, and other accepted-but-not-forwarded fields are documented in
   Sprint 003. Fixture tests should confirm they are accepted without error,
   but cannot verify upstream behavior.

6. **Image download during streaming Gemini conversion.** `_build_gemini_parts_from_output`
   downloads images during streaming conversion (routes.py L633–L651). Fixture tests
   for Gemini streaming with image output will require either a mock HTTP server or
   runtime capture.

7. **Model config count and aliases.** After `_apply_veo_3_1_model_updates`, the
   total MODEL_CONFIG key count is large and depends on import-time side effects.
   To be confirmed by runtime inspection.

8. **Tier-based model key mutation.** `_resolve_video_model_key_for_tier` can change
   model keys at runtime. Fixture tests for model resolution should cover the base
   (non-tier-mutated) path first.

---

## Recommended Next Sprint

The recommended next sprint is a **documentation-only test harness plan refinement
and first-slice fixture design sprint** that:

1. Finalizes the fixture matrix (see [GENERATION_FIXTURE_MATRIX.md](../GENERATION_FIXTURE_MATRIX.md))
   with concrete placeholder JSON shapes
2. Designs the test harness directory layout (see [TEST_HARNESS_PLAN.md](../TEST_HARNESS_PLAN.md))
3. Creates sanitized static fixture JSON files for the highest-priority fixtures
4. Implements a minimal test harness skeleton that can load and validate fixture shapes
5. Does not call upstream services or require real credentials

That sprint should remain documentation-adjacent (fixture files + test scaffolding)
and should not modify runtime source code.
