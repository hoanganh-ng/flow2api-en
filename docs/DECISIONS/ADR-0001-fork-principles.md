# ADR-0001: Fork Principles

**Status**: Accepted
**Date**: 2026-06-11
**Sprint**: Sprint 000

## Context

The upstream [flow2api](https://github.com/TheSmallHanCat/flow2api) project is a Python/FastAPI service that wraps Google's Flow (VideoFX) media generation behind OpenAI/Gemini-compatible APIs. The project documentation is primarily in Chinese. We want to create an English-friendly fork with structured documentation for understanding and potentially rewriting the system.

## Decision

We establish the following principles for this fork:

### 1. Preserve Upstream Behavior

Runtime behavior must remain identical to upstream unless a future sprint explicitly documents and scopes a change. This includes:
- API request/response formats
- Authentication and authorization logic
- Token lifecycle and refresh behavior
- Captcha solving workflows
- Proxy and network configuration
- Generation request handling
- Docker deployment behavior
- Default configuration values
- Model lists and resolution logic
- Admin UI behavior

### 2. Preserve License and Attribution

The original MIT license (Copyright © 2025 TheSmallHanCat) must remain intact. The fork is clearly marked as unofficial and not endorsed by the upstream author.

### 3. Additive English Documentation

English documentation is added alongside (not replacing) existing Chinese content. Source code comments in Chinese are left in place. No bulk translation passes on source files.

### 4. No Abuse or Evasion

This project does not design or implement features for:
- Bypassing upstream access controls
- Evading rate limits beyond upstream allowances
- Circumventing security measures
- Unauthorized access to services

### 5. High-Risk Area Awareness

Token handling, captcha/browser behavior, proxy behavior, upstream client behavior, and generation request/response compatibility are treated as high-risk areas requiring explicit sprint scoping before modification.

### 6. Documentation Before Code Changes

Before any source code modification:
- The affected module must be documented at the source level
- API contracts must be specified
- Compatibility fixtures must exist
- Changes must be validated against fixtures

## Consequences

**Positive**:
- Clear governance for fork evolution
- Reduced risk of accidental behavior changes
- Structured path toward potential rewrite
- English documentation lowers barrier for non-Chinese contributors

**Negative**:
- Slower initial progress due to documentation-first approach
- Maintaining dual-language documentation overhead
- Fork may diverge from upstream bug fixes if not actively synced

## Alternatives Considered

1. **Immediate rewrite** — Rejected: insufficient understanding of upstream behavior
2. **Translation-only fork** — Rejected: no structural documentation for planning
3. **No fork, contribute upstream** — Rejected: language barrier and different long-term goals
