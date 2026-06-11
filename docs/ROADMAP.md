# ROADMAP.md

## Migration Stages

The long-term goal is to move this project toward a maintainable TypeScript/Node.js implementation while preserving behavioral compatibility at every step. Each stage builds on the previous one and can be validated independently.

### Stage 1 — English Fork and Documentation Cleanup ✅ (Current)

**Sprint 000**

- [x] Fork baseline established
- [x] English project brain (CLAUDE.md) created
- [x] Core documentation scaffolding in place
- [x] README notice added (additive only)
- [x] LICENSE preserved
- [x] No runtime changes

**Deliverables**: This documentation set.

### Stage 2 — Existing System Map

**Goal**: Produce a detailed source-level understanding of every module before touching code.

- Document each Python module's responsibilities, inputs, outputs, and side effects
- Map all internal function call chains for generation, token refresh, and captcha flows
- Identify implicit contracts between modules (shared state, global singletons, database coupling)
- Catalog all configuration knobs and their runtime effects
- Document database schema and migration logic

**Deliverables**: Updated ARCHITECTURE.md and MODULE_BOUNDARIES.md with source-verified detail.

### Stage 3 — API Contract Documentation

**Goal**: Specify every external and internal API contract so a rewrite can be validated against fixtures.

- OpenAI-compatible request/response schemas with all field variants
- Gemini-compatible request/response schemas with all field variants
- Admin API schemas
- WebSocket captcha protocol
- Health and metrics endpoints
- Error code mapping and status code behavior
- Streaming event format (SSE)

**Deliverables**: API contract specification document; Postman/OpenAPI collections if feasible.

### Stage 4 — Test Harness / Compatibility Fixtures

**Goal**: Build a regression test suite that captures current behavior so a rewrite can prove compatibility.

- Golden request/response fixtures for each generation type
- Token lifecycle test scenarios (mocked upstream)
- Captcha flow test scenarios (mocked browser)
- Load balancer distribution tests
- Model resolver edge cases
- Config loading and migration tests
- Docker smoke tests

**Deliverables**: `tests/fixtures/` directory; CI integration.

### Stage 5 — TypeScript Shell Implementation

**Goal**: Stand up a minimal TypeScript service that passes the compatibility fixtures.

- FastAPI-equivalent routing (Express / Fastify / Hono)
- OpenAI + Gemini endpoint implementations
- Config loader (TOML)
- SQLite persistence (better-sqlite3 or similar)
- Docker packaging
- Admin UI shell

**Deliverables**: TypeScript project in `ts/` directory; passing fixture tests.

### Stage 6 — Gradual Replacement of Python Modules

**Goal**: Replace Python modules one at a time, validating each against fixtures.

Priority order (lowest risk first):
1. Config/persistence
2. Model resolver
3. API compatibility layer
4. Load balancer / concurrency manager
5. Generation handler
6. Token/account lifecycle
7. Proxy/network configuration
8. Browser/captcha/session lifecycle

**Deliverables**: Incremental migration PRs; each validated against Stage 4 fixtures.

### Stage 7 — Optional Go Services (Where Justified)

**Goal**: Evaluate whether any isolated service benefits from Go.

Candidates (only if analysis shows clear benefit):
- High-throughput polling proxy for upstream status checks
- Standalone captcha token broker service

**Rule**: Go is only adopted if TypeScript cannot meet a specific performance or concurrency requirement, and the service is small and self-contained.

## Decision Criteria

At each stage, the following must hold:

- **No silent behavior changes**: Any deviation from upstream must be explicitly documented in a sprint.
- **Fixture coverage**: Before replacing a module, its behavior must be captured in tests.
- **Backward compatibility**: Downstream clients must not break.
- **Deployment parity**: Docker Compose workflows must continue to work.
