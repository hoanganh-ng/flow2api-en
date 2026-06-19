# Test Harness Plan

> **Sprint 006P — ASGI Send-Await Backpressure Seam Discovery**
> Sprint 006P discovered the ASGI send-await backpressure seam,
> compared six candidate approaches, confirmed via disposable probe
> that blocked send() deterministically prevents handler advancement,
> and recommended direct StreamingResponse invocation with ASGI
> spec_version "2.4" for the next implementation sprint. See
> [STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md](STREAMING_BACKPRESSURE_SEAM_DISCOVERY.md)
> and
> [SPRINT-006P](SPRINTS/SPRINT-006P-asgi-send-await-backpressure-seam-discovery.md)
> for details.
> Sprint 006O added 1 receive-side streaming disconnect characterization
> test proving exactly one body sent before disconnect, CancelledError
> observed in handler, finally block ran, route iterator terminated,
> no [DONE] or more_body=False emitted.
> See
> [SPRINT-006O](SPRINTS/SPRINT-006O-receive-side-streaming-disconnect-characterization.md)
> for details.
> Sprint 005D added offline static shape assertions for Sprint 005C fixtures
> (FX-ON-002, FX-GN-001, FX-OS-002).
> Sprint 006M added 2 HTTP-level streaming route characterization tests.
> Sprint 006A discovered safe route-level test seams and documented unsafe approaches.
> Sprint 006B added 67 unit tests for 7 pure conversion helpers in `src.api.routes`,
> confirming the import is side-effect-free.
> Sprint 006C added 95 unit tests for model catalog helpers and 4 read-only model
> route functions, confirming fully local behavior.
> Sprint 006D documented generation route dependency chains, the fake-handler
> interface, and a proposed test matrix for mocked generation route tests.
> Sprint 006E added 6 mocked non-streaming generation route tests covering
> text success, handler-uninitialized, and handler-error conversion for both
> OpenAI and Gemini routes.
> Sprint 006F added 5 mocked OpenAI image-result route tests covering the
> FX-ON-002 contract path with network/media helper guards.
> Sprint 006G added 18 mocked OpenAI streaming generator contract tests
> covering SSE framing, reasoning_content progress, [DONE] termination,
> multiple-chunk ordering, empty-stream behavior, mutable-state cleanup,
> and direct handler-exception propagation (no SSE error synthesis,
> no `[DONE]` emitted after failure).
> Sprint 006H added 41 mocked Gemini streaming generator contract tests
> covering Gemini event framing, text conversion, finish-reason mapping,
> reasoning-content behavior, empty stream, non-emitting chunks, handler
> error-payload conversion (with early termination via return), exception
> propagation, argument forwarding, mutable-state cleanup, and the
> no-`[DONE]` termination contract.
> Tests iterate the internal `_iterate_gemini_stream` async generator directly
> without StreamingResponse, TestClient, or HTTP transport.
> Sprint 006I discovered streaming transport seams: StreamingResponse
> construction does not start iteration, direct body_iterator consumption
> is feasible and safe, direct route calls supply the already-resolved api_key
> dependency parameter explicitly (authentication behavior is not exercised),
> and exception timing is well-defined relative to HTTP response start.
> A test matrix of 15 streaming transport tests has been proposed.
> Sprint 006J added 8 StreamingResponse wrapper and body-iterator characterization
> tests covering deferred execution, SSE framing, [DONE] termination,
> handler-unavailable timing, and partial-output exception behavior for both
> OpenAI and Gemini streaming routes. Tests use direct route function calls
> with direct body_iterator consumption; no FastAPI app, TestClient, ASGI
> transport, or HTTP transport is involved.
> Sprint 006K added 6 direct ASGI StreamingResponse send-loop characterization
> tests covering response-start timing, header byte-type and value assertions,
> byte encoding proved via non-ASCII UTF-8 payloads (`Xin chào — 世界`),
> body-message framing with exact per-event message counts,
> `data: [DONE]\n\n` termination as a separate ASGI body message, `more_body`
> flags, normal completion (final empty-body message), and exception propagation
> (response.start sent, no final more_body=False). Tests invoke
> `StreamingResponse.__call__` directly with synthetic ASGI scope
> (spec_version "2.4"), receive, and send callables; no FastAPI app, TestClient,
> HTTPX, or HTTP transport is involved. Sprint 006K.1 strengthened the
> successful tests with exact ASGI message sequence, exact content-body byte
> values, non-ASCII UTF-8 byte preservation, and Gemini event-payload order
> verification. Sprint 006L discovered the HTTP-level streaming test seam,
> comparing TestClient, ASGITransport, ASGI spec_version wrappers,
> `src.main.app` import, and live Uvicorn. It recommended a test-local
> FastAPI app with `routes.router`, dependency override for
> `verify_api_key_flexible`, `generation_handler` patching, and TestClient
> for complete-response HTTP contract assertions. Both TestClient and
> ASGITransport fully buffer the response body before delivery; incremental
> client-side streaming is not possible with either transport.
> Sprint 006M added 2 HTTP-level streaming route characterization tests
> using the recommended test-local FastAPI + `routes.router` + TestClient
> seam. Tests exercise POST /v1/chat/completions (OpenAI) and
> POST /v1beta/models/{model}:streamGenerateContent (Gemini) through the
> full HTTP request path with dependency override and handler patch.
> Assertions cover status codes, SSE headers, fully buffered SSE body
> content, event ordering, [DONE] termination (OpenAI), no-[DONE] (Gemini),
> and handler call arguments. Non-ASCII content (`Xin chào — 世界`) is
> included in both tests.
> See [ROUTE_TEST_SEAM_DISCOVERY.md](ROUTE_TEST_SEAM_DISCOVERY.md),
> [GENERATION_ROUTE_TEST_PLAN.md](GENERATION_ROUTE_TEST_PLAN.md),
> [GENERATION_ROUTE_DEPENDENCY_MAP.md](GENERATION_ROUTE_DEPENDENCY_MAP.md),
> [GENERATION_ROUTE_MOCKING_PLAN.md](GENERATION_ROUTE_MOCKING_PLAN.md),
> [STREAMING_TRANSPORT_SEAM_DISCOVERY.md](STREAMING_TRANSPORT_SEAM_DISCOVERY.md),
> [STREAMING_TRANSPORT_TEST_PLAN.md](STREAMING_TRANSPORT_TEST_PLAN.md),
> [SPRINT-006B](SPRINTS/SPRINT-006B-conversion-layer-unit-tests.md),
> [SPRINT-006C](SPRINTS/SPRINT-006C-model-catalog-read-only-route-characterization.md),
> [SPRINT-006D](SPRINTS/SPRINT-006D-mocked-generation-route-seam-discovery.md),
> [SPRINT-006E](SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md),
> [SPRINT-006F](SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md),
> [SPRINT-006G](SPRINTS/SPRINT-006G-mocked-openai-streaming-generator-contract.md),
> [SPRINT-006H](SPRINTS/SPRINT-006H-mocked-gemini-streaming-generator-contract.md),
> [SPRINT-006I](SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md),
> [SPRINT-006L](SPRINTS/SPRINT-006L-http-level-streaming-test-seam-discovery.md), and
> [SPRINT-006M](SPRINTS/SPRINT-006M-http-level-streaming-route-characterization.md),
> and
> [SPRINT-006N](SPRINTS/SPRINT-006N-streaming-disconnect-cancellation-seam-discovery.md) for details.
> Sprint 006N discovered the streaming disconnect and cancellation seam,
> compared six candidate approaches (A–F), confirmed determinism of a
> coordinated receive-side design with gated handlers, and recommended
> direct StreamingResponse invocation with ASGI spec 2.0 for the next
> implementation sprint. Exactly one disconnect test is recommended
> (OpenAI route; Gemini shares the same StreamingResponse cancellation path).

---

## Purpose

This document describes the planned test harness approach for future generation
compatibility testing in flow2api-en. It covers fixture directory layout, naming
conventions, secret avoidance, mocking strategy, streaming comparison techniques,
and the recommended first implementation slice.

Sprint 005A created the first static fixture skeleton (fixture files only).
Sprint 005B added the first executable offline shape assertion tests using
a standard-library-only fixture loader.
Sprint 005C added three additional static fixture files (FX-ON-002, FX-GN-001, FX-OS-002)
without adding any new tests or assertions.
Sprint 005D added offline static shape assertions for the Sprint 005C fixtures
(FX-ON-002, FX-GN-001, FX-OS-002).
Sprint 006A discovered safe route-level test seams (conversion-layer pure functions,
model listing handlers) and documented unsafe approaches (lifespan, singletons, upstream
calls). See [ROUTE_TEST_SEAM_DISCOVERY.md](ROUTE_TEST_SEAM_DISCOVERY.md) for the full
seam analysis and [GENERATION_ROUTE_TEST_PLAN.md](GENERATION_ROUTE_TEST_PLAN.md) for
the proposed route-level test stages.
Sprint 006B added the first runtime-importing unit tests: 67 offline tests covering
7 pure conversion helpers in `src.api.routes`. Import safety was confirmed.
See [SPRINT-006B](SPRINTS/SPRINT-006B-conversion-layer-unit-tests.md) for details.
Sprint 006C added 95 offline tests covering 5 model catalog helpers and 4 read-only
model route functions (`list_models`, `list_model_aliases`, `list_gemini_models`,
`get_gemini_model`). All tested functions are fully local (no handler, upstream,
database, or network dependencies). See
[SPRINT-006C](SPRINTS/SPRINT-006C-model-catalog-read-only-route-characterization.md)
for details.
Sprint 006D documented the generation route dependency chains, proposed a
fake-handler interface for `handle_generation`, specified request construction
approaches, and defined a test matrix for future mocked generation route tests.
See [GENERATION_ROUTE_DEPENDENCY_MAP.md](GENERATION_ROUTE_DEPENDENCY_MAP.md) and
[GENERATION_ROUTE_MOCKING_PLAN.md](GENERATION_ROUTE_MOCKING_PLAN.md) for details.
Sprint 006E added the first mocked generation route tests: 6 offline tests
covering OpenAI and Gemini non-streaming text success, handler-uninitialized
behavior, and deterministic handler-error conversion. Tests use direct Python
function calls with a fake handler; no FastAPI app, TestClient, HTTP transport,
or network activity is involved. See
[SPRINT-006E](SPRINTS/SPRINT-006E-mocked-non-streaming-generation-route-tests.md)
for details.
Sprint 006F added 5 mocked OpenAI image-result route tests covering the
FX-ON-002 contract path. Tests confirm that the image-result route does not
invoke network or media retrieval helpers (`retrieve_image_data`,
`_load_image_bytes_from_uri`), which are patched to raise if called. See
[SPRINT-006F](SPRINTS/SPRINT-006F-mocked-openai-image-result-route-contract.md)
for details.
Sprint 006G added 18 mocked OpenAI streaming generator contract tests
covering the internal `_iterate_openai_stream` async generator. Tests
characterize SSE framing (raw JSON wrapping and passthrough),
`reasoning_content` preservation (consistent with FX-OS-002), exact
`data: [DONE]\n\n` termination (consistent with FX-OS-003), multiple-chunk
ordering, empty-stream behavior, mutable-state cleanup, and direct
handler-exception propagation. The generator contains no local exception
conversion: exceptions raised by the handler propagate directly to the
caller and interrupt normal stream termination, so the generator does not
emit its final `[DONE]` event. Client-visible HTTP/StreamingResponse
handling of the propagated exception remains out of scope. Tests iterate
the generator directly with `async for`; no `StreamingResponse`,
`TestClient`, or HTTP transport is involved. See
[SPRINT-006G](SPRINTS/SPRINT-006G-mocked-openai-streaming-generator-contract.md)
for details.
Sprint 006H added 41 mocked Gemini streaming generator contract tests
covering the internal `_iterate_gemini_stream` async generator. Tests
characterize Gemini event framing (raw JSON and `data:`-prefixed chunks
converted through `_convert_openai_stream_chunk_to_gemini_event`), text
preservation in Gemini `candidates[0].content.parts`, finish-reason
mapping (stop→STOP, length→MAX_TOKENS, content_filter→SAFETY),
`reasoning_content` appearing as Gemini text (preferred over `content`),
empty-stream behavior (no events, no terminal sentinel), non-emitting
chunk behavior (skipped silently), handler error-payload conversion
(JSON `error` key triggers Gemini error event and early `return`),
exception propagation (no try/except wrapping), argument forwarding
(stream=True, images normalization, video_media_id, base_url_override),
mutable-state cleanup, and the no-`[DONE]` termination contract. The
generator explicitly converts handler error payloads to Gemini error
events using `_build_gemini_error_payload` and terminates via `return`.
Unlike `_iterate_openai_stream`, no terminal sentinel is emitted.
Client-visible HTTP/StreamingResponse handling remains out of scope.
See
[SPRINT-006H](SPRINTS/SPRINT-006H-mocked-gemini-streaming-generator-contract.md)
for details. HTTP-level streaming tests remain deferred to a future sprint.

---

## Recommended Fixture Directory Layout

The following structure is planned for a future sprint. Sprint 005A created the
first fixture files under `tests/fixtures/generation/`. The full layout below
is not yet complete.

```
tests/
  fixtures/
    static/
      # Static fixtures: constructed from source docs, no runtime capture needed
      FX-ML-001_v1_models_response.json
      FX-ML-002_v1_models_aliases_response.json
      FX-ML-003_v1beta_models_response.json
      FX-ER-001_openai_error_response.json
      FX-ER-002_gemini_error_response.json
      FX-ON-004_accepted_extra_fields_request.json
    mocked/
      # Mocked internal responses: handler-output-level fixtures
      FX-ON-001_nonstream_text_input.json
      FX-ON-001_nonstream_text_output.json
      FX-ON-002_nonstream_image_input.json
      FX-ON-002_nonstream_image_output.json
      FX-ON-003_nonstream_video_input.json
      FX-ON-003_nonstream_video_output.json
      FX-OS-001_stream_text_chunks.jsonl
      FX-OS-002_reasoning_content_chunks.jsonl
      FX-OS-003_done_sentinel.jsonl
      FX-GN-001_gemini_nonstream_input.json
      FX-GN-001_gemini_nonstream_output.json
      FX-GS-001_gemini_stream_chunks.jsonl
      FX-GS-002_gemini_stream_no_done.jsonl
      FX-CV-001_gemini_to_internal_input.json
      FX-CV-001_gemini_to_internal_expected.json
      FX-CV-002_internal_to_gemini_input.json
      FX-CV-002_internal_to_gemini_output.json
      FX-CV-003_stream_conversion_input.jsonl
      FX-CV-003_stream_conversion_output.jsonl
      FX-CX-001_extend_input.json
      FX-CX-001_extend_expected_normalized.json
    runtime/
      # Runtime-captured fixtures: require live upstream or careful mocking
      # (empty until a runtime-capture sprint is completed)
      .gitkeep
  harness/
    # Test harness utilities (future)
    fixture_loader.py
    streaming_comparator.py
    shape_assertions.py
    sanitization_checker.py
  test_generation_fixtures.py
  test_streaming_fixtures.py
  test_conversion_fixtures.py
  test_model_listing_fixtures.py
  test_error_fixtures.py
```

---

## Separating Sanitized Static Fixtures from Runtime-Captured Fixtures

### Static fixtures (`tests/fixtures/static/`)

- Constructed entirely from source inspection and documented contracts
- No network access or upstream service required
- Safe to commit to version control without sanitization concerns
- Used to verify response shapes, model listing structures, error envelopes
- Can be hand-written or generated from documented schemas

### Mocked internal-response fixtures (`tests/fixtures/mocked/`)

- Represent the internal handler output format (observed in source)
- Exercise the route-layer conversion logic without calling upstream services
- The generation handler is mocked to return these fixtures directly
- Used to test: OpenAI→Gemini conversion, streaming chunk conversion,
  error response shaping, request normalization
- Require careful construction to match observed internal format exactly

### Runtime-captured fixtures (`tests/fixtures/runtime/`)

- Captured from a live (or carefully mocked) upstream service
- Require sanitization before commit (see below)
- Should not be committed until a sanitization review has been performed
- Used for: upstream response schemas, video polling states, exact chunk timing
- May require periodic refresh if upstream API changes

### Separation rules

1. Static and mocked fixtures must never contain real credentials, tokens, or
   upstream URLs. If a fixture needs a URL, use `placeholder.example.invalid`.
2. Runtime fixtures must pass through a sanitization filter before commit.
3. The `tests/fixtures/runtime/` directory should be listed in `.gitignore` until
   a sanitization review process is established.
4. Fixture tests should be runnable in three modes: `static-only`,
   `static+mocked`, and `all` (including runtime).

---

## Naming Conventions

### Fixture files

- Pattern: `FX-{CATEGORY}-{SEQ}_{short_description}_{role}.json`
  (or `.jsonl` for streaming chunk sequences)
- Category codes: `ML` (model listing), `ON` (OpenAI non-streaming),
  `OS` (OpenAI streaming), `GN` (Gemini non-streaming), `GS` (Gemini streaming),
  `CV` (conversion), `ER` (error), `CX` (custom extension)
- Role suffixes: `_input`, `_output`, `_expected`, `_response`, `_request`,
  `_chunks` (for `.jsonl` streaming sequences)
- IDs must match the fixture matrix in
  [GENERATION_FIXTURE_MATRIX.md](GENERATION_FIXTURE_MATRIX.md)

### Test files

- Pattern: `test_{domain}_fixtures.py`
- Domain grouping: `generation`, `streaming`, `conversion`, `model_listing`, `error`
- Each test function: `test_fx_{category}_{seq}_{description}`
  (e.g., `test_fx_on_001_nonstream_text_shape`)

### Test harness utilities

- `fixture_loader.py` — loads fixture JSON/JSONL by ID, validates schema
- `streaming_comparator.py` — compares streaming chunk sequences
  (order-tolerant where appropriate)
- `shape_assertions.py` — reusable structural assertions for OpenAI and Gemini
  envelopes
- `sanitization_checker.py` — scans fixture content for patterns that resemble
  real credentials

---

## Avoiding Real Secrets, Tokens, and Cookies

### Placeholder convention

All fixtures must use clearly synthetic placeholder values:

| Secret type | Placeholder |
|-------------|-------------|
| API key | `"test-api-key-placeholder"` |
| Access token (AT) | `"test-at-placeholder"` |
| Session token (ST) | `"test-st-placeholder"` |
| Admin session token | `"test-admin-token-placeholder"` |
| Plugin connection token | `"test-connection-token-placeholder"` |
| Cookie | `"test-cookie-placeholder"` or omit entirely |
| Account email | `"test-account@example.invalid"` |
| Project ID | `"test-project-id"` |
| Upstream base URL | `"https://upstream-placeholder.example.invalid"` |
| Media URL | `"https://placeholder.example.invalid/media/test.jpg"` |
| reCAPTCHA token | `"test-recaptcha-token-placeholder"` |
| IP address | RFC 5737 documentation range: `192.0.2.1` |
| Timestamp | Fixed epoch: `1700000000` |

### Pre-commit sanitization check (planned)

A future `sanitization_checker.py` utility should scan all fixture files for:

- Base64 strings longer than 64 characters (potential real tokens)
- Email addresses not matching `*@example.invalid`
- URLs not matching `*.example.invalid` or `*.example.com`
- Strings matching common token patterns (e.g., `eyJ...` for JWT, `admin-` prefix)
- IP addresses outside documentation ranges

This check should run as a pre-commit hook or CI gate before fixtures are merged.

---

## Suggested First Test Harness Slice

The first test harness implementation sprint should target the 6 priority-1
fixtures identified in [GENERATION_FIXTURE_MATRIX.md](GENERATION_FIXTURE_MATRIX.md):

1. `FX-ML-001` — GET /v1/models response shape
2. `FX-ON-001` — POST /v1/chat/completions non-streaming text
3. `FX-ON-002` — POST /v1/chat/completions image result formatting
4. `FX-OS-001` — POST /v1/chat/completions streaming text
5. `FX-OS-003` — data: [DONE] OpenAI stream termination
6. `FX-GN-001` — POST ...:generateContent non-streaming

This slice covers:

- One model listing endpoint (verifying discovery contract)
- Two non-streaming generation shapes (text + image)
- Two streaming behaviors (chunks + termination sentinel)
- One Gemini endpoint (verifying the other compatibility surface)

### What the first slice should include

- `tests/fixtures/static/` and `tests/fixtures/mocked/` directories with
  placeholder JSON files for the 6 fixtures
- A minimal `fixture_loader.py` that reads JSON by fixture ID
- A minimal `shape_assertions.py` with:
  - `assert_openai_chat_completion_shape(response_dict)`
  - `assert_openai_stream_chunk_shape(chunk_dict)`
  - `assert_gemini_generate_content_response_shape(response_dict)`
  - `assert_openai_model_list_shape(response_dict)`
- Test functions for each of the 6 fixtures
- A `sanitization_checker.py` stub that scans fixture files for common secret
  patterns (even if not yet wired to CI)

### What the first slice should not include

- Runtime-captured fixtures
- Tests that call upstream services
- Tests that require real credentials or tokens
- Admin API tests
- WebSocket tests
- Performance or load tests

---

## What Should Be Mocked vs. What Requires Runtime Capture

### Should be mocked (first harness sprint)

| Component | Mock approach |
|-----------|-------------|
| Generation handler output | Return canned OpenAI-format JSON from fixture files |
| Upstream Flow API | Not called; handler is mocked at the yield boundary |
| Token selection / load balancer | Mocked to return a placeholder token |
| File cache | Mocked to return a placeholder URL |
| Model resolver | Use the real resolver with fixture `MODEL_CONFIG` entries, or mock to return known keys |
| Auth (`verify_api_key_flexible`) | Mocked to always pass (test key matches placeholder) |
| Image fetch (for Gemini parts conversion) | Mock HTTP client returns synthetic base64 |

### Requires runtime capture (later sprint)

| Component | Why runtime capture is needed |
|-----------|-----------------------------|
| Full upstream `batchGenerateImages` response | Schema unknown beyond `media[0].image.generatedImage.fifeUrl` |
| Video polling state progression | Exact operation status schema and state transitions unknown |
| Upsample response format | Base64 image envelope not documented from source alone |
| Exact chunk timing / ordering | Depends on upstream polling intervals; non-deterministic |
| Token ST/AT lifecycle | External upstream API contract |
| Captcha service response shapes | Multiple captcha methods with distinct integration surfaces |

---

## What Should Not Be Tested Yet

The following areas are explicitly deferred and should not be included in early
test harness sprints:

1. **Admin API endpoints** — token management, proxy config, generation config,
   captcha config, plugin config, logs, system info. These are lower-risk for
   client compatibility and have complex auth (admin session tokens).

2. **WebSocket `/captcha_ws`** — message protocol is not fully documented.
   Requires separate protocol-level fixture design.

3. **Health and metrics endpoints** — low compatibility risk; Prometheus format
   is well-established.

4. **Static file serving** — HTML pages and `/tmp` mount are simple file
   responses with minimal contract surface.

5. **Extension/plugin token endpoint** — uses a separate auth mechanism
   (connection_token) and is tightly coupled to browser extension behavior.

6. **Token ST/AT conversion** — depends on upstream API contracts external
   to this codebase.

7. **Captcha solving pipeline** — browser, personal, remote_browser, and
   third-party methods each have distinct surfaces not yet documented at
   fixture level.

8. **Proxy manager behavior** — proxy selection and rotation logic is a
   runtime concern that does not affect the client-facing API contract.

9. **Concurrency manager** — internal rate limiting and concurrency control
   are not observable from the client side.

---

## How to Compare Streaming Chunks Safely

Streaming chunk comparison is inherently tricky because:

- Chunk ordering may include non-deterministic progress messages
- Timestamps vary between runs
- The number of progress chunks depends on upstream polling intervals

### Recommended comparison strategy

1. **Parse the SSE stream into a list of chunk dicts.**
   - Split on `\n\n` boundaries
   - Strip `data: ` prefix
   - Parse JSON (skip `[DONE]` sentinel for OpenAI streams)

2. **Normalize timestamps.**
   - Replace all `created`, `id` timestamp fields with a fixed value
   - This allows structural comparison without timestamp sensitivity

3. **Classify chunks by type.**
   - **Progress chunks:** `delta.reasoning_content` is present, `delta.content`
     is absent, `finish_reason` is `null`
   - **Content chunks:** `delta.content` is present
   - **Terminal chunk:** `finish_reason` is `"stop"` (or Gemini `finishReason`
     is `"STOP"`)

4. **Assert structural invariants, not exact content.**
   - At least one progress chunk is emitted before the content chunk
     (for image/video generation)
   - Exactly one terminal chunk is emitted
   - The terminal chunk contains the media URL in `content` (OpenAI) or
     `parts[].text` (Gemini)
   - For OpenAI: `data: [DONE]` follows the terminal chunk
   - For Gemini: no `[DONE]` follows; stream ends after terminal event

5. **Use order-tolerant comparison for progress chunks.**
   - Progress messages may vary in number and exact text
   - Assert that at least N progress chunks exist (N may be 0 for text-only)
   - Do not assert exact progress text

6. **For Gemini streaming, verify the conversion layer.**
   - Each Gemini event has `candidates[0].content.role == "model"`
   - `modelVersion` is present in each event
   - `finishReason` mapping follows the documented rules
     (`stop` → `STOP`, `length` → `MAX_TOKENS`, etc.)

---

## Compatibility Assertions to Prioritize

The following assertions should be prioritized in early test harness sprints,
ordered by client-impact likelihood:

### Tier 1 — Must-pass for basic client compatibility

1. **OpenAI non-streaming response envelope** — `id`, `object`, `created`,
   `model`, `choices` fields present with correct types
2. **OpenAI streaming SSE framing** — each chunk is `data: {json}\n\n`,
   terminal is `data: [DONE]\n\n`
3. **OpenAI streaming chunk envelope** — `object: "chat.completion.chunk"`,
   `choices[0].delta` structure, `finish_reason` values
4. **Gemini non-streaming response envelope** — `candidates[0].content.parts[]`,
   `finishReason`, `modelVersion`
5. **Model listing shape** — `/v1/models` returns `object: "list"` with
   `data[]` array of model objects

### Tier 2 — Important for media-generation clients

6. **Image content format** — OpenAI `choices[0].message.content` contains
   `![Generated Image](url)` pattern
7. **Video content format** — OpenAI `choices[0].message.content` contains
   HTML `<video>` tag
8. **Gemini parts conversion** — markdown images → `inlineData`, HTML video
   tags → `fileData`
9. **Gemini stream termination** — no `[DONE]` sentinel after final event
10. **`reasoning_content` in streaming delta** — progress messages use
    `reasoning_content` field, not `content`

### Tier 3 — Important for edge cases and non-standard extensions

11. **`extend://` scheme acceptance** — request with `extend://MEDIA_ID` in
    `image_url` is accepted and normalized correctly
12. **Accepted-but-not-forwarded fields** — `temperature`, `max_tokens`,
    `responseModalities` are accepted without error
13. **Error response envelopes** — OpenAI `{error: {message, type, code}}`
    and Gemini `{error: {code, message, status}}` formats
14. **Gemini model resource** — single model lookup returns correct shape
    with `supportedGenerationMethods`
15. **Auth channel support** — `Authorization: Bearer`, `x-goog-api-key`,
    and `?key=` all accepted
