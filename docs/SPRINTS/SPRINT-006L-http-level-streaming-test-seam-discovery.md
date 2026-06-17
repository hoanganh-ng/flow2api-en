# Sprint 006L — HTTP-Level Streaming Test Seam Discovery

| Field | Value |
|-------|-------|
| Sprint ID | 006L |
| Type | Documentation-only (discovery) |
| Predecessor | Sprint 006K.1 |
| Status | Completed |

---

## 1. Objective

Identify the safest, most deterministic seam for exercising the streaming
generation routes (`/v1/chat/completions` with `stream=true`, and
`/v1beta/models/{model}:streamGenerateContent`) through the full HTTP
request path:

- FastAPI route matching
- Pydantic request validation
- Dependency injection (`verify_api_key_flexible`)
- In-process HTTP client (TestClient or httpx.AsyncClient)

The seam must be offline, deterministic, and must not initialize production
services (database, token manager, proxy manager, load balancer, browser
captcha, generation handler).

---

## 2. Scope

### In scope

- Inspect installed versions of Python, FastAPI, Starlette, HTTPX, AnyIO.
- Read and analyze Starlette `TestClient._TestClientTransport` source.
- Read and analyze httpx `ASGITransport` source.
- Read and analyze `StreamingResponse.__call__` dispatch logic.
- Analyze FastAPI `dependency_overrides` behavior.
- Analyze `src.api.routes` module boundary (router, handler global, auth).
- Analyze `src.main.app` construction and lifespan behavior.
- Compare five candidate seams (A–E) across eleven dimensions.
- Recommend exactly one seam for the next implementation sprint.
- Propose a minimal next-sprint test matrix.

### Out of scope

- Implementing tests.
- Modifying `src/` or existing test files.
- Importing or executing `src.main.app`.
- Starting production lifespan.
- Using database, upstream network, browser, captcha, token, session,
  proxy, or media services.
- Running a real socket server.
- Upgrading dependencies.

---

## 3. Installed Dependency Versions

| Package | Version |
|---------|---------|
| Python | 3.12.3 |
| FastAPI | 0.119.0 |
| Starlette | 0.48.0 |
| HTTPX | 0.28.1 |
| AnyIO | 4.13.0 |

---

## 4. Key Findings

### 4.1 src.main.app is unsafe

Importing `src.main` triggers module-level construction of `Database`,
`ProxyManager`, `FlowClient`, `TokenManager`, `LoadBalancer`,
`ConcurrencyManager`, and `GenerationHandler`. The `lifespan` context
manager performs database initialization, token snapshots, browser captcha
startup, warmup-tab allocation, and background task creation. This violates
offline and determinism constraints.

### 4.2 routes.router is a safe module boundary

`src.api.routes.router` is a plain `APIRouter()` with no lifespan,
middleware, or state. Its only external dependency is the module-level
`generation_handler` global (set via `set_generation_handler()`), which can
be safely patched. `verify_api_key_flexible` is a standard FastAPI
`Depends` callable, overridable via `app.dependency_overrides`.

### 4.3 Both TestClient and ASGITransport fully buffer responses

**TestClient (`_TestClientTransport`):** Collects all `http.response.body`
chunks into `io.BytesIO()`, then wraps the complete buffer as
`httpx.ByteStream(raw_kwargs["stream"].read())`. The response body is
delivered as a single chunk.

**httpx ASGITransport:** Collects all body chunks into `body_parts:
list[bytes]`, then `ASGIResponseStream.__aiter__` yields
`b"".join(body_parts)`. The response body is delivered as a single chunk.

**Conclusion:** Neither transport provides genuinely incremental streaming
delivery. `client.stream()`, `iter_bytes()`, and `iter_lines()` operate on
the already-buffered body.

### 4.4 ASGI spec_version defaults to "2.0" in both transports

Neither `TestClient` nor `ASGITransport` sets `asgi.spec_version` in the
scope. Starlette 0.48.0 therefore applies its default value of `"2.0"`,
which enters `StreamingResponse`'s pre-2.4 implementation path: the
`anyio.create_task_group()` branch with the disconnect-listener task.

This observation does not prove equivalence with a deployed Uvicorn server's
streaming, disconnect, cancellation, scheduling, or socket behavior. The
installed Uvicorn source has not been inspected for this sprint.

### 4.5 Authentication override is clean

`app.dependency_overrides[verify_api_key_flexible] = lambda: "test-key"`
completely replaces the authentication dependency. No `AuthManager`,
`config.api_key`, or database state is consulted.

---

## 5. Candidate Seam Comparison

Five candidates were evaluated across eleven dimensions. Full details are
in [HTTP_STREAMING_TEST_SEAM_DISCOVERY.md](../HTTP_STREAMING_TEST_SEAM_DISCOVERY.md).

| Candidate | Verdict | Rationale |
|-----------|---------|-----------|
| **A** — Test-local FastAPI + routes.router + TestClient | **Recommended** | Simplest setup, synchronous, works with unittest, full HTTP contract exercised, no production risk |
| **B** — Test-local FastAPI + AsyncClient + ASGITransport | Valid alternative | Async-native but same buffering, slightly more complex exception behavior, no additional coverage |
| **C** — ASGI wrapper altering spec_version | Supplementary only | Tests a non-production code path; reduces fidelity |
| **D** — Import src.main.app | **Excluded** | Triggers production lifespan, database access, service construction |
| **E** — Live Uvicorn/socket server | **Excluded** | Non-deterministic, network-dependent, violates all constraints |

---

## 6. Recommended Seam

**Candidate A: Test-local FastAPI with routes.router, dependency override,
handler patch, and TestClient.**

Setup pattern (pseudocode):

```python
from fastapi import FastAPI
from starlette.testclient import TestClient
from unittest.mock import patch

import src.api.routes as routes_module
from src.core.auth import verify_api_key_flexible

def make_test_app():
    app = FastAPI()  # no lifespan
    app.include_router(routes_module.router)
    app.dependency_overrides[verify_api_key_flexible] = lambda: "test-key"
    return app

class TestHTTPStreaming(unittest.TestCase):
    def setUp(self):
        self.app = make_test_app()
        self.client = TestClient(self.app)
        self.handler_patcher = patch("src.api.routes.generation_handler", FakeHandler(...))
        self.handler_patcher.start()

    def tearDown(self):
        self.handler_patcher.stop()
```

---

## 7. Proposed Next-Sprint Test Matrix

### Test 1: OpenAI HTTP-level streaming response

- `POST /v1/chat/completions` with `{"stream": true, "model": "...", "messages": [...]}`
- Fake handler yields deterministic SSE strings
- Assert: status 200, `content-type: text/event-stream`, header presence,
  fully reassembled SSE body content and order, `data: [DONE]\n\n` termination

### Test 2: Gemini HTTP-level streaming response

- `POST /v1beta/models/{model}:streamGenerateContent` with Gemini request body
- Fake handler yields deterministic OpenAI-format JSON chunks
- Assert: status 200, `content-type: text/event-stream`, Gemini event format
  (`candidates[0].content.role == "model"`, `modelVersion`), no `[DONE]` sentinel

These two tests are sufficient for the first HTTP-level streaming
implementation slice. The successful-path tests already prove that the
test-local `dependency_overrides[verify_api_key_flexible]` is wired
correctly and that the patched `generation_handler` is invoked through the
full FastAPI routing and Pydantic validation chain. A 401 test belongs to
separate authentication characterization. A 422 test primarily characterizes
generic FastAPI/Pydantic request validation and is not needed for the first
HTTP-level streaming implementation slice.

---

## 8. Explicitly Deferred

- Original ASGI body-message boundaries (Sprint 006K/006K.1)
- True incremental client delivery (impossible with current transports)
- Client disconnect behavior
- Cancellation propagation
- Backpressure
- Proxy buffering
- TCP or transfer-encoding behavior
- Production lifespan behavior
- `spec_version` manipulation (Candidate C)
- Async client testing (Candidate B)
- Authentication characterization (401 path)
- Request-validation characterization (422 path)

---

## 9. Deliverables

| Deliverable | Status |
|-------------|--------|
| docs/HTTP_STREAMING_TEST_SEAM_DISCOVERY.md | Created |
| docs/SPRINTS/SPRINT-006L-http-level-streaming-test-seam-discovery.md | Created |
| docs/PROJECT_STATE.md updated | Updated |
| docs/SPRINTS/README.md updated | Updated |
| docs/TEST_HARNESS_PLAN.md updated | Updated |
| No src/ changes | Confirmed |
| No test file changes | Confirmed |

---

## 10. Verification

```
python3 - <<'PY'
import sys; from importlib.metadata import version
print("python", sys.version)
for p in ("fastapi", "starlette", "httpx", "anyio"): print(p, version(p))
PY
# → python 3.12.3, fastapi 0.119.0, starlette 0.48.0, httpx 0.28.1, anyio 4.13.0

python3 -m unittest discover -s tests/compatibility -p "test_*.py"
# → 299 tests, OK

git diff -- src   # no output
git diff -- tests # no output
git diff --check  # no output
```
