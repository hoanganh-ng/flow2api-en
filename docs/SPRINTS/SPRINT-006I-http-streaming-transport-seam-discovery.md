# Sprint 006I — HTTP Streaming Transport Seam Discovery

## Status

✅ Completed

## Scope

Inspect and document the narrowest safe seam for testing streaming route
wrappers (`create_chat_completion` and `stream_generate_content`) and their
`StreamingResponse` construction behavior. This sprint is discovery and
documentation only. Do not invoke generation routes, construct
`StreamingResponse`, or add tests.

## Approach

### Source Inspection

All findings are from source inspection of:
- `src/api/routes.py` — streaming route wrappers and internal generators
- `src/core/auth.py` — authentication dependency chain
- Installed Starlette `StreamingResponse` implementation (`.venv/.../starlette/responses.py`)

No routes were invoked, no `StreamingResponse` was constructed or consumed,
no HTTP transport was exercised, and no runtime source was modified.

### Key Discoveries

1. **StreamingResponse construction does not start iteration.** The async
   generator is stored as `self.body_iterator` without calling `__anext__`.
   Iteration begins only when `stream_response(send)` is invoked via
   `__call__(scope, receive, send)`.

2. **Direct body_iterator iteration is feasible.** Tests can iterate
   `response.body_iterator` with `async for` without invoking `__call__`,
   `stream_response`, or any ASGI machinery. This avoids HTTP transport,
   lifespan, and disconnect handling.

3. **Both streaming routes use identical StreamingResponse construction.**
   Same media_type (`text/event-stream`), same explicit headers
   (`Cache-Control`, `Connection`, `X-Accel-Buffering`), same default
   status (200). The generators differ (OpenAI emits `[DONE]`, Gemini does
   not), but the transport seam is the same.

4. **Authentication dependency is not exercised.** Direct route calls supply the
   already-resolved `api_key` dependency parameter explicitly. Authentication
   behavior is not exercised. The route does not use `api_key` beyond the
   dependency check.

5. **Exception timing is well-defined.** Exceptions before `StreamingResponse`
   construction occur before HTTP response start. Exceptions during iteration
   occur after response start and may truncate the stream.

6. **Starlette appends charset to text media types.** The final `content-type`
   header is `text/event-stream; charset=utf-8`.

## Safety Gate

**PASSED.** This sprint is documentation-only. No runtime behavior was
exercised:

- No FastAPI app creation
- No lifespan startup/shutdown
- No `StreamingResponse` construction or consumption
- No HTTP/ASGI transport
- No TestClient
- No dependency override
- No authentication testing
- No `src.main` import
- No production service instantiation
- No network calls
- No media retrieval
- No runtime source modification
- No new dependencies
- No commits or pushes

## Findings

### 1. Streaming Route Functions

#### OpenAI Streaming: `create_chat_completion`

- **Location:** `src/api/routes.py`, lines 850–889
- **Route path:** `POST /v1/chat/completions`
- **Stream-selection condition:** `if request.stream:`
- **Internal generator:** `_iterate_openai_stream(normalized, request_base_url)`
- **Media type:** `"text/event-stream"`
- **Explicit headers:** `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- **Status:** Default 200
- **Construction starts iteration:** No

#### Gemini Streaming: `stream_generate_content`

- **Location:** `src/api/routes.py`, lines 938–973
- **Route path:** `POST /v1beta/models/{model}:streamGenerateContent`
- **Stream-selection condition:** Always streaming (dedicated route)
- **Internal generator:** `_iterate_gemini_stream(normalized, normalized.model, request_base_url)`
- **Media type:** `"text/event-stream"`
- **Explicit headers:** `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- **Status:** Default 200
- **Construction starts iteration:** No

### 2. Starlette StreamingResponse Behavior

- **Construction consumes iterator:** No
- **When body_iterator execution starts:** Only during `stream_response(send)` via `__call__`
- **Iterator wrapping:** Sync `Iterable` wrapped via `iterate_in_threadpool`; `AsyncIterable` stored directly
- **Direct body_iterator iteration feasibility:** Yes (public attribute, no ASGI machinery required)
- **String-to-bytes encoding:** Applied during `stream_response` (UTF-8); direct iteration yields `str`
- **Media-type/charset handling:** `text/event-stream` → `text/event-stream; charset=utf-8`
- **Background-task handling:** Not exercised (routes do not pass `background`)
- **Exception propagation during iteration:** Direct (no try/except wrapping in `stream_response`)
- **Cleanup on completion or failure:** Generator's `finally` (if any) executes; no `finally` in route generators

### 3. Authentication Dependency

- **Config/database/service reads:** Reads `config.api_key` (in-memory comparison)
- **Test-local dependency override safety:** Yes (FastAPI supports `app.dependency_overrides`)
- **Direct-call behavior:** Pass `api_key="test-key"` directly; supplies the already-resolved dependency parameter explicitly. Authentication behavior is not exercised.
- **Distinction:** Route characterization tests authentication as a precondition, not the subject

### 4. Exception Timing

| Phase | When | Before/After HTTP Response Start |
|-------|------|----------------------------------|
| Request validation | Before route wrapper | Before |
| Route wrapper execution | After validation | Before |
| Handler-initialization check | During `_ensure_generation_handler()` | Before |
| StreamingResponse construction | After normalization | Before |
| First body iteration | After route returns | After |
| Partial output | After first chunk sent | After |
| Exception after partial output | During iteration | After |
| Normal completion | Generator exhausted | After |

### 5. Headers and Media Types

- **OpenAI streaming media type:** `text/event-stream; charset=utf-8`
- **Gemini streaming media type:** `text/event-stream; charset=utf-8`
- **Explicit route headers:** `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- **Automatically generated headers:** `content-type` (with charset), no `content-length`
- **Server/proxy behavior:** Undefined (not tested)

### 6. Candidate Test Seams

#### Option A: Direct Route Function Call → Direct body_iterator Consumption

- **Isolation:** High (no app, no lifespan, no TestClient)
- **Application/lifespan risk:** None
- **Dependency behavior:** Direct route calls supply the already-resolved `api_key` dependency parameter explicitly. Authentication behavior is not exercised.
- **Production-global initialization:** None
- **Coverage gained:** StreamingResponse construction, generator iteration, exception propagation, headers/media-type
- **Cleanup and exception observability:** Direct
- **Appropriate for next sprint:** Yes

#### Option B: Minimal Test-Local FastAPI App → Dependency Override → TestClient

- **Isolation:** Medium (test-local app)
- **Application/lifespan risk:** Low (if no lifespan handlers)
- **Dependency behavior:** Overridden via `app.dependency_overrides`
- **Production-global initialization:** None (if `src.main` not imported)
- **Coverage gained:** Full HTTP transport, TestClient integration
- **Cleanup and exception observability:** TestClient handles
- **Appropriate for next sprint:** Possibly, but adds complexity

#### Option C: Import/Use src.main

- **Isolation:** Low (production app)
- **Application/lifespan risk:** High (lifespan handlers instantiate services)
- **Dependency behavior:** Production dependencies active
- **Production-global initialization:** Full (database, services, config)
- **Coverage gained:** Full production behavior
- **Cleanup and exception observability:** Complex
- **Appropriate for next sprint:** No (unsafe for offline, deterministic tests)

### 7. Recommended Seam

**Option A: Direct route function call plus direct `StreamingResponse.body_iterator` consumption.**

**Added coverage:**
- StreamingResponse construction verification
- Generator iteration at transport boundary
- Exception propagation before and after partial output
- Header and media type assertions
- OpenAI `[DONE]` termination vs. Gemini silent termination

**Remaining gaps:**
- Full HTTP transport (chunked encoding, connection handling)
- Proxy buffering and backpressure
- Client disconnect detection
- ASGI server behavior
- TestClient integration

**Safety:**
- No FastAPI app creation
- No lifespan startup/shutdown
- No TestClient or ASGI transport
- No production service instantiation
- No network calls
- Deterministic and offline

**OpenAI and Gemini together:** Yes (same transport seam, different generators)

**Partial-output exceptions in first transport sprint:** Yes (small number of tests, high value)

### 8. Proposed Next Test Matrix

See [STREAMING_TRANSPORT_TEST_PLAN.md](../STREAMING_TRANSPORT_TEST_PLAN.md) for
the detailed test matrix.

**Summary:**

| Group | Tests | Description |
|-------|-------|-------------|
| Group 1 | 6 | OpenAI streaming happy path |
| Group 2 | 5 | Gemini streaming happy path |
| Group 3 | 1 | OpenAI exception before first chunk |
| Group 4 | 1 | Gemini exception before first chunk |
| Group 5 | 1 | OpenAI partial output then exception |
| Group 6 | 1 | Gemini partial output then exception |
| **Total** | **15** | |

### 9. Deferred Behaviors

- Full HTTP transport (chunked encoding, connection handling, ASGI server)
- Proxy buffering (nginx, Cloudflare)
- Backpressure and flow control
- Client disconnect detection and propagation
- TestClient integration
- Lifespan behavior
- Production services
- Network calls
- Media retrieval

## Documents Created

| File | Purpose |
|------|---------|
| `docs/STREAMING_TRANSPORT_SEAM_DISCOVERY.md` | Full seam discovery and analysis |
| `docs/STREAMING_TRANSPORT_TEST_PLAN.md` | Proposed test matrix for Sprint 006J |
| `docs/SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md` | This sprint document |

## Documents Modified

| File | Change |
|------|--------|
| `docs/PROJECT_STATE.md` | Added Sprint 006I to sprint history, current sprint, what-is-not-yet-done, and next-steps |
| `docs/TEST_HARNESS_PLAN.md` | Added Sprint 006I streaming transport seam discovery note |
| `docs/SPRINTS/README.md` | Added Sprint 006I to sprint index |

## What This Sprint Does NOT Cover

- Streaming transport tests (no tests added)
- Generation route invocation
- `StreamingResponse` construction or consumption
- `TestClient` or ASGI transport usage
- FastAPI app creation
- Dependency override
- Authentication testing
- `src.main` import
- Lifespan execution
- Production service instantiation
- Network calls
- Media retrieval
- Runtime source modification
- New dependencies
- Commits or pushes

## Verification

```bash
# Baseline verification
git status --short
# Result: worktree contains only intended Sprint 006I sprint changes and no unrelated changes

git log -5 --oneline
# Result:
# 7913a5a test(gemini): add 41 mocked Gemini streaming generator contract tests
# 2dde91f test(generation): add mocked OpenAI streaming generator contract tests
# 4fd6189 test(compatibility): add mocked OpenAI image-result route contract tests
# 8085205 test: characterize non-streaming generation routes
# 7257afe docs: map mocked generation route seam

# Full compatibility suite
python3 -m unittest discover -s tests/compatibility -p "test_*.py" -v
# Result: 285 tests, OK

# Import safety
python3 -c "import src.api.routes; print('src.api.routes import: OK')"
# Result: OK

# No runtime source changes
git diff -- src
# Result: (no output)

# No whitespace errors
git diff --check
# Result: (no output)

# Final status
git status --short
# Result:
# ?? docs/STREAMING_TRANSPORT_SEAM_DISCOVERY.md
# ?? docs/STREAMING_TRANSPORT_TEST_PLAN.md
# ?? docs/SPRINTS/SPRINT-006I-http-streaming-transport-seam-discovery.md
# M docs/PROJECT_STATE.md
# M docs/TEST_HARNESS_PLAN.md
# M docs/SPRINTS/README.md

git diff --stat
# Result: 3 files changed, insertions/deletions for updated docs
```

## Confirmation

- No generation routes were invoked.
- No `StreamingResponse` was constructed or consumed.
- No HTTP transport was exercised.
- No `TestClient` or ASGI transport was used.
- No FastAPI app was created.
- No dependencies were overridden.
- No authentication was tested.
- No `src.main` was imported.
- No lifespan was run.
- No production services were instantiated.
- No network calls were made.
- No media was retrieved.
- No runtime source (`src/`) was modified.
- No fixtures were added.
- No dependencies were added.
- No commits or pushes were performed.

## Recommendation for Next Sprint

Sprint 006J should implement the 15 streaming transport tests defined in
[STREAMING_TRANSPORT_TEST_PLAN.md](../STREAMING_TRANSPORT_TEST_PLAN.md) using
the recommended seam (direct route function call plus direct
`StreamingResponse.body_iterator` consumption).

The tests cover:
- OpenAI and Gemini streaming transport happy paths (11 tests)
- Exception before first chunk for both routes (2 tests)
- Partial output then exception for both routes (2 tests)

All tests are offline, deterministic, and consistent with the existing test
patterns established in Sprint 006E–006H.
