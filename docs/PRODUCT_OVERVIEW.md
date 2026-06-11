# PRODUCT_OVERVIEW.md

## What Is flow2api?

flow2api is a self-hosted API gateway that wraps Google's Flow (VideoFX / AI Sandbox) media generation service behind OpenAI-compatible and Gemini-compatible HTTP endpoints. It allows downstream applications — chat UIs, agent frameworks, API gateways like New API — to generate images and videos using Google's models without directly integrating with Google's internal Flow API.

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Text-to-Image (T2I)** | Generate images from text prompts via Gemini 3.0 Pro, Gemini 3.1 Flash, Imagen 4.0 |
| **Image-to-Image (I2I)** | Transform existing images using text + image input |
| **Text-to-Video (T2V)** | Generate videos from text prompts via Veo 3.1 (standard, fast, lite, ultra variants) |
| **Image-to-Video (I2V)** | Generate videos from 1-2 reference images (first-frame or first+last-frame) |
| **Reference-to-Video (R2V)** | Generate videos from up to 3 reference images with structured prompts |
| **Video Upsample** | Upscale generated videos to 1080P or 4K |
| **Multi-token load balancing** | Distribute requests across multiple Google accounts |
| **Captcha automation** | Multiple captcha solving modes (extension, personal browser, headed browser, third-party APIs) |
| **Admin UI** | Web-based token management, config, monitoring |
| **Prometheus metrics** | `/metrics` endpoint for observability |

## API Compatibility Layers

### OpenAI-Compatible
- `POST /v1/chat/completions` — unified generation endpoint
- `GET /v1/models` — model listing
- `GET /v1/models/aliases` — simplified model aliases

### Gemini-Compatible
- `POST /v1beta/models/{model}:generateContent`
- `POST /v1beta/models/{model}:streamGenerateContent`
- `POST /models/{model}:generateContent`
- `POST /models/{model}:streamGenerateContent`
- `GET /v1beta/models` / `GET /models` — model listing
- Supports `systemInstruction`, `contents[].parts[].text/inlineData/fileData`, `generationConfig`

### Authentication
- `Authorization: Bearer <api_key>`
- `x-goog-api-key: <api_key>`
- `?key=<api_key>` (query parameter)

## Deployment Modes

1. **Standard Docker** — `docker-compose.yml`, uses third-party captcha (YesCaptcha, CapMonster, etc.)
2. **Headed Docker** — `docker-compose.headed.yml`, runs Xvfb + Fluxbox for in-container browser captcha
3. **Proxy Docker** — `docker-compose.proxy.yml`, adds Cloudflare WARP sidecar
4. **Local** — `python main.py` with virtualenv

## Upstream Relationship

This project acts as a reverse-proxy / adapter between:
- **Upstream**: Google AI Sandbox API (`aisandbox-pa.googleapis.com`) and Google Labs (`labs.google/fx/api`)
- **Downstream**: Any OpenAI-compatible client or Gemini-compatible client

The upstream service requires valid Google session tokens (ST) which are exchanged for access tokens (AT). The captcha solving infrastructure exists to refresh these tokens when they expire.
