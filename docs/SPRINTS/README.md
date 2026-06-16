# Sprints

This directory contains sprint planning and retrospective documents for the flow2api-en fork.

## Sprint Index

| Sprint | Name | Status | Description |
|--------|------|--------|-------------|
| [000](SPRINT-000-fork-baseline-english-project-brain.md) | Fork Baseline & English Project Brain | ✅ Completed | Documentation-only fork baseline, no runtime changes |
| [001](SPRINT-001-existing-system-map.md) | Existing System Map | ✅ Completed | Source-based system map, entrypoints, config map, risk register |
| [001A](SPRINT-001A-english-surface-audit.md) | English Surface Audit | ✅ Completed | Audit of Chinese-language surfaces, translation plan (audit-only) |
| [001B](SPRINT-001B-safe-readme-translation.md) | Safe README Translation | ✅ Completed | English README created, original Chinese preserved as README.zh-CN.md |
| [001C](SPRINT-001C-safe-translation-allowlist.md) | Safe Translation Allowlist | ✅ Completed | Translation allowlist/denylist created; classified all remaining Chinese surfaces |
| [002](SPRINT-002-api-surface-inventory.md) | API Surface Inventory | ✅ Completed | Documentation-only inventory of HTTP/WS API surface from source inspection |
| [003](SPRINT-003-generation-contract-deep-dive.md) | Generation Contract Deep Dive | ✅ Completed | Documentation-only deep dive of generation contract from source inspection |
| [004](SPRINT-004-generation-fixture-plan.md) | Generation Fixture Plan | ✅ Completed | Documentation-only fixture plan for future generation compatibility tests |
| [005A](SPRINT-005A-static-generation-fixture-skeleton.md) | Static Generation Fixture Skeleton | ✅ Completed | First sanitized static fixture skeleton (FX-ML-001, FX-ON-001, FX-OS-003) |
| [005B](SPRINT-005B-fixture-loader-shape-assertions.md) | Fixture Loader & Shape Assertions | ✅ Completed | Offline static fixture shape assertions for Sprint 005A fixtures |
| [005C](SPRINT-005C-additional-static-generation-fixtures.md) | Additional Static Generation Fixtures | ✅ Completed | Additional sanitized static fixture files (FX-ON-002, FX-GN-001, FX-OS-002) |
| [005D](SPRINT-005D-additional-static-fixture-assertions.md) | Additional Static Fixture Assertions | ✅ Completed | Offline static shape assertions for Sprint 005C fixtures |
| [006A](SPRINT-006A-route-test-seam-discovery.md) | Route Test Seam Discovery | ✅ Completed | Discovery-only analysis of safest route-level test seams |
| [006B](SPRINT-006B-conversion-layer-unit-tests.md) | Conversion-Layer Unit Tests | ✅ Completed | 67 unit tests for 7 pure conversion helpers in `src.api.routes` |
| [006C](SPRINT-006C-model-catalog-read-only-route-characterization.md) | Model Catalog & Read-Only Route Characterization | ✅ Completed | 95 unit tests for model catalog helpers and read-only model route functions |
| [006D](SPRINT-006D-mocked-generation-route-seam-discovery.md) | Mocked Generation Route Seam Discovery | ✅ Completed | Discovery-only documentation of generation route dependencies and mocking plan |
| [006E](SPRINT-006E-mocked-non-streaming-generation-route-tests.md) | Mocked Non-Streaming Generation Route Tests | ✅ Completed | 6 mocked non-streaming generation route tests with fake handler |
| [006F](SPRINT-006F-mocked-openai-image-result-route-contract.md) | Mocked OpenAI Image-Result Route Contract | ✅ Completed | 5 mocked image-result route tests with network/media helper guards |
| [006G](SPRINT-006G-mocked-openai-streaming-generator-contract.md) | Mocked OpenAI Streaming Generator Contract | ✅ Completed | 18 mocked OpenAI streaming generator tests covering SSE framing, reasoning_content, [DONE], ordering, empty stream, and handler-exception propagation |
| [006H](SPRINT-006H-mocked-gemini-streaming-generator-contract.md) | Mocked Gemini Streaming Generator Contract | ✅ Completed | 41 mocked Gemini streaming generator tests covering Gemini event framing, text conversion, finish-reason mapping, reasoning content, empty/non-emitting chunks, handler error-payload conversion, exception propagation, and no-[DONE] termination |
| [006I](SPRINT-006I-http-streaming-transport-seam-discovery.md) | HTTP Streaming Transport Seam Discovery | ✅ Completed | Discovery-only analysis of streaming transport seams, StreamingResponse behavior, authentication dependencies, exception timing, and recommended test approach |
| [006J](SPRINT-006J-streaming-response-wrapper-body-iterator-characterization.md) | StreamingResponse Wrapper & Body-Iterator Characterization | ✅ Completed | 8 StreamingResponse wrapper and body-iterator characterization tests covering deferred execution, SSE framing, [DONE] termination, handler-unavailable timing, and partial-output exception behavior |
| [006K](SPRINT-006K-direct-asgi-streaming-response-send-loop-characterization.md) | Direct ASGI StreamingResponse Send-Loop Characterization | ✅ Completed | 6 direct ASGI StreamingResponse send-loop tests covering response-start timing, header/byte encoding, body-message framing, [DONE] termination bytes, more_body flags, normal completion, and exception propagation |

## Sprint Conventions

- Each sprint document describes scope, deliverables, constraints, and verification steps
- Sprints must not change runtime behavior unless explicitly scoped
- High-risk areas require explicit sprint scope before modification
- Sprint documents are immutable once accepted (create a new sprint for corrections)
