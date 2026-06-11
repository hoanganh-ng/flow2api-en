# Flow2API

> **Unofficial English-friendly fork.** This is an unofficial fork of [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api). The original MIT license and attribution are preserved in [LICENSE](LICENSE). Runtime behavior is intended to remain unchanged from upstream unless a future sprint explicitly documents a change. See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for details.

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.119.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)

**A full-featured OpenAI-compatible API service providing a unified interface for Flow**

[中文文档](README.zh-CN.md) | [Project State](docs/PROJECT_STATE.md)

</div>

---

## Unofficial Fork Notice

This repository is an **unofficial fork** of [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api). It is not endorsed by the upstream author. The fork adds English documentation and planning artifacts. No upstream source code has been modified. All original attribution and license terms are preserved.

## Upstream Attribution

- **Upstream project:** [TheSmallHanCat/flow2api](https://github.com/TheSmallHanCat/flow2api)
- **Upstream author:** TheSmallHanCat
- **Upstream license:** MIT (Copyright © 2025 TheSmallHanCat)
- **Fork name:** flow2api-en

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Project Overview

Based on the upstream README and current source-analysis documentation, flow2api is a self-hosted API gateway that wraps Google's Flow (VideoFX / AI Sandbox) media generation service behind OpenAI-compatible and Gemini-compatible HTTP endpoints. It allows downstream applications — chat UIs, agent frameworks, API gateways — to generate images and videos using Google's models without directly integrating with Google's internal Flow API.

See [docs/PRODUCT_OVERVIEW.md](docs/PRODUCT_OVERVIEW.md) for a detailed overview.

## Current Compatibility Intent

This fork currently intends to preserve upstream runtime behavior unless a future sprint explicitly changes it. All runtime strings, UI text, source comments, config keys, endpoint paths, model names, and provider names remain unchanged from upstream. See [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for the current sprint status.

---

## Feature Overview

Based on the upstream README and observed during source mapping:

- **Text-to-Image (T2I)** / **Image-to-Image (I2I)** — via Gemini 3.0 Pro, Gemini 3.1 Flash, Imagen 4.0
- **Text-to-Video (T2V)** / **Image-to-Video (I2V)** — via Veo 3.1 (standard, fast, lite, ultra variants)
- **First/Last Frame Video (I2V)** — supports 1-2 reference images for frame-based video generation
- **Reference-to-Video (R2V)** — up to 3 reference images with structured prompts
- **Video Upsample** — upscale generated videos to 1080P or 4K
- **AT/ST Auto-Refresh** — automatic Access Token refresh; automatic Session Token update via browser (personal mode)
- **Balance Display** — real-time VideoFX Credits query and display
- **Load Balancing** — multi-token polling and concurrency control
- **Proxy Support** — HTTP/SOCKS5 proxy support
- **Web Admin UI** — token and configuration management
- **Image Generation Continuous Conversation**
- **Gemini Official Request Body Compatibility** — supports `generateContent` / `streamGenerateContent`, `systemInstruction`, `contents.parts.text/inlineData/fileData`

---

## Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Or Python 3.8+

- Due to additional captcha requirements on Flow, you can choose between browser-based captcha or third-party captcha services:
  Register at [YesCaptcha](https://yescaptcha.com/i/13Xd8K) and obtain an API key, then enter it in the system config page under `YesCaptcha API密钥`.
- YesCaptcha supports switching `type` in the admin page: `RecaptchaV3TaskProxyless`, `RecaptchaV3TaskProxylessM1`, `RecaptchaV3TaskProxylessM1S7`, `RecaptchaV3TaskProxylessM1S9`; S7/S9 will force submit `minScore` 0.7/0.9.
- The default `docker-compose.yml` is intended for use with third-party captcha services (yescaptcha/capmonster/ezcaptcha/capsolver).
  For in-Docker headed browser captcha (browser/personal), use `docker-compose.headed.yml` below.

- Auto-update ST browser extension: [Flow2API-Token-Updater](https://github.com/TheSmallHanCat/Flow2API-Token-Updater)

### Method 1: Docker Deployment (Recommended)

#### Standard Mode (no proxy)

```bash
# Clone the project
git clone https://github.com/TheSmallHanCat/flow2api.git
cd flow2api

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

> Note: Compose already mounts `./tmp:/app/tmp` by default. If cache timeout is set to `0`, the semantic is "no automatic expiration"; if you want cache files to persist across container rebuilds, keep this `tmp` mount.

#### WARP Mode (with proxy)

```bash
# Start with WARP proxy
docker-compose -f docker-compose.warp.yml up -d

# View logs
docker-compose -f docker-compose.warp.yml logs -f
```

#### Docker Headed Browser Captcha Mode (browser / personal)

> For scenarios where you need a virtualized desktop and want to enable headed browser captcha inside the container.
> This mode starts `Xvfb + Fluxbox` by default for in-container visualization and sets `ALLOW_DOCKER_HEADED_CAPTCHA=true`.
> Only the application port is exposed; no remote desktop connection ports are provided.
> The `personal` built-in browser now defaults to headed mode; to temporarily switch back to headless, set the environment variable `PERSONAL_BROWSER_HEADLESS=true`.

```bash
# Start headed mode (--build recommended on first run)
docker compose -f docker-compose.headed.yml up -d --build

# View logs
docker compose -f docker-compose.headed.yml logs -f
```

- API port: `8000`
- After entering the admin console, set the captcha method to `browser` or `personal`

### Method 2: Local Deployment

```bash
# Clone the project
git clone https://github.com/TheSmallHanCat/flow2api.git
cd flow2api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the service
python main.py
```

### First Access

After the service starts, access the admin console at: **http://localhost:8000**. Please change the default password on first login!

- **Username**: `admin`
- **Password**: `admin`

---

## Monitoring Endpoints

- `GET /health` — public health check; returns service liveness, active token count, expiring token count, expired token count, 429-banned count, and other summary data
- `GET /metrics` — Prometheus metrics endpoint
- `GET /api/tokens` — admin endpoint; returns `at_expires`, `at_expired`, `at_expiring_within_1h`, `ban_reason`, `consecutive_error_count`, and other token status fields

Prometheus can scrape `/metrics` directly. If deploying to Kubernetes, it is recommended to scrape only within the cluster and restrict external access to `/metrics` at the Ingress/Gateway layer.

### Model Test Page

Visit **http://localhost:8000/test** to open the built-in model test page, which supports:

- Browse all available models by category (image generation, text/image-to-video, multi-image video, video upsample, etc.)
- Enter prompts for one-click testing with streaming generation progress
- Upload images for image-to-image / image-to-video scenarios
- Preview generated images or videos after completion

---

## Supported Models

### Image Generation

| Model Name | Description | Size |
|---------|--------|--------|
| `gemini-3.0-pro-image-landscape` | I2I/T2I | Landscape |
| `gemini-3.0-pro-image-portrait` | I2I/T2I | Portrait |
| `gemini-3.0-pro-image-square` | I2I/T2I | Square |
| `gemini-3.0-pro-image-four-three` | I2I/T2I | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four` | I2I/T2I | Portrait 3:4 |
| `gemini-3.0-pro-image-landscape-2k` | I2I/T2I (2K) | Landscape |
| `gemini-3.0-pro-image-portrait-2k` | I2I/T2I (2K) | Portrait |
| `gemini-3.0-pro-image-square-2k` | I2I/T2I (2K) | Square |
| `gemini-3.0-pro-image-four-three-2k` | I2I/T2I (2K) | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four-2k` | I2I/T2I (2K) | Portrait 3:4 |
| `gemini-3.0-pro-image-landscape-4k` | I2I/T2I (4K) | Landscape |
| `gemini-3.0-pro-image-portrait-4k` | I2I/T2I (4K) | Portrait |
| `gemini-3.0-pro-image-square-4k` | I2I/T2I (4K) | Square |
| `gemini-3.0-pro-image-four-three-4k` | I2I/T2I (4K) | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four-4k` | I2I/T2I (4K) | Portrait 3:4 |
| `imagen-4.0-generate-preview-landscape` | I2I/T2I | Landscape |
| `imagen-4.0-generate-preview-portrait` | I2I/T2I | Portrait |
| `gemini-3.1-flash-image-landscape` | I2I/T2I | Landscape |
| `gemini-3.1-flash-image-portrait` | I2I/T2I | Portrait |
| `gemini-3.1-flash-image-square` | I2I/T2I | Square |
| `gemini-3.1-flash-image-four-three` | I2I/T2I | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four` | I2I/T2I | Portrait 3:4 |
| `gemini-3.1-flash-image-landscape-2k` | I2I/T2I (2K) | Landscape |
| `gemini-3.1-flash-image-portrait-2k` | I2I/T2I (2K) | Portrait |
| `gemini-3.1-flash-image-square-2k` | I2I/T2I (2K) | Square |
| `gemini-3.1-flash-image-four-three-2k` | I2I/T2I (2K) | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four-2k` | I2I/T2I (2K) | Portrait 3:4 |
| `gemini-3.1-flash-image-landscape-4k` | I2I/T2I (4K) | Landscape |
| `gemini-3.1-flash-image-portrait-4k` | I2I/T2I (4K) | Portrait |
| `gemini-3.1-flash-image-square-4k` | I2I/T2I (4K) | Square |
| `gemini-3.1-flash-image-four-three-4k` | I2I/T2I (4K) | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four-4k` | I2I/T2I (4K) | Portrait 3:4 |

### Video Generation

#### Text-to-Video (T2V)

> Does not support image upload.

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_t2v_fast_portrait` | T2V | Portrait |
| `veo_3_1_t2v_fast_landscape` | T2V | Landscape |
| `veo_3_1_t2v_fast_portrait_ultra` | T2V | Portrait |
| `veo_3_1_t2v_fast_ultra` | T2V | Landscape |
| `veo_3_1_t2v_fast_portrait_ultra_relaxed` | T2V | Portrait |
| `veo_3_1_t2v_fast_ultra_relaxed` | T2V | Landscape |
| `veo_3_1_t2v_portrait` | T2V | Portrait |
| `veo_3_1_t2v_landscape` | T2V | Landscape |
| `veo_3_1_t2v_landscape_4s` | T2V 4s | Landscape |
| `veo_3_1_t2v_portrait_4s` | T2V 4s | Portrait |
| `veo_3_1_t2v_landscape_6s` | T2V 6s | Landscape |
| `veo_3_1_t2v_portrait_6s` | T2V 6s | Portrait |
| `veo_3_1_t2v_fast_landscape_4s` | T2V Fast 4s | Landscape |
| `veo_3_1_t2v_fast_portrait_4s` | T2V Fast 4s | Portrait |
| `veo_3_1_t2v_fast_landscape_6s` | T2V Fast 6s | Landscape |
| `veo_3_1_t2v_fast_portrait_6s` | T2V Fast 6s | Portrait |
| `veo_3_1_t2v_lite_portrait` | T2V Lite | Portrait |
| `veo_3_1_t2v_lite_landscape` | T2V Lite | Landscape |
| `veo_3_1_t2v_lite_4s_portrait` | T2V Lite 4s | Portrait |
| `veo_3_1_t2v_lite_4s_landscape` | T2V Lite 4s | Landscape |
| `veo_3_1_t2v_lite_6s_portrait` | T2V Lite 6s | Portrait |
| `veo_3_1_t2v_lite_6s_landscape` | T2V Lite 6s | Landscape |

#### First/Last Frame Models (I2V - Image to Video)

> Supports 1-2 images: 1 image as the first frame, 2 images as first + last frame.

> **Auto-adaptation**: The system automatically selects the corresponding model_key based on image count.
> - **Single-frame mode** (1 image): uses the first frame to generate video
> - **Dual-frame mode** (2 images): uses first + last frame to generate a transition video
> - `veo_3_1_i2v_lite_*` supports **1** first-frame image only
> - `veo_3_1_interpolation_lite_*` supports **2** first+last-frame images only

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_i2v_s_fast_portrait_fl` | I2V | Portrait |
| `veo_3_1_i2v_s_fast_fl` | I2V | Landscape |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl` | I2V | Portrait |
| `veo_3_1_i2v_s_fast_ultra_fl` | I2V | Landscape |
| `veo_3_1_i2v_s_fast_portrait_ultra_relaxed` | I2V | Portrait |
| `veo_3_1_i2v_s_fast_ultra_relaxed` | I2V | Landscape |
| `veo_3_1_i2v_s_portrait` | I2V | Portrait |
| `veo_3_1_i2v_s_landscape` | I2V | Landscape |
| `veo_3_1_i2v_s_landscape_4s` | I2V 4s | Landscape |
| `veo_3_1_i2v_s_portrait_4s` | I2V 4s | Portrait |
| `veo_3_1_i2v_s_landscape_6s` | I2V 6s | Landscape |
| `veo_3_1_i2v_s_portrait_6s` | I2V 6s | Portrait |
| `veo_3_1_i2v_s_fast_landscape_4s_fl` | I2V Fast 4s | Landscape |
| `veo_3_1_i2v_s_fast_portrait_4s_fl` | I2V Fast 4s | Portrait |
| `veo_3_1_i2v_s_fast_landscape_6s_fl` | I2V Fast 6s | Landscape |
| `veo_3_1_i2v_s_fast_portrait_6s_fl` | I2V Fast 6s | Portrait |
| `veo_3_1_i2v_lite_portrait` | I2V Lite (first frame only) | Portrait |
| `veo_3_1_i2v_lite_landscape` | I2V Lite (first frame only) | Landscape |
| `veo_3_1_i2v_lite_4s_portrait` | I2V Lite 4s (first frame only) | Portrait |
| `veo_3_1_i2v_lite_4s_landscape` | I2V Lite 4s (first frame only) | Landscape |
| `veo_3_1_i2v_lite_6s_portrait` | I2V Lite 6s (first frame only) | Portrait |
| `veo_3_1_i2v_lite_6s_landscape` | I2V Lite 6s (first frame only) | Landscape |
| `veo_3_1_interpolation_lite_portrait` | I2V Lite (first+last frame interpolation) | Portrait |
| `veo_3_1_interpolation_lite_landscape` | I2V Lite (first+last frame interpolation) | Landscape |
| `veo_3_1_interpolation_lite_4s_portrait` | I2V Lite 4s (first+last frame interpolation) | Portrait |
| `veo_3_1_interpolation_lite_4s_landscape` | I2V Lite 4s (first+last frame interpolation) | Landscape |
| `veo_3_1_interpolation_lite_6s_portrait` | I2V Lite 6s (first+last frame interpolation) | Portrait |
| `veo_3_1_interpolation_lite_6s_landscape` | I2V Lite 6s (first+last frame interpolation) | Landscape |

#### Reference-to-Video (R2V)

> Supports multiple reference images.

> Based on upstream README, last synced 2026-03-06:
>
> - Upstream new-version `R2V` video request body synced
> - `textInput` switched to `structuredPrompt.parts`
> - Top-level `mediaGenerationContext.batchId` added
> - Top-level `useV2ModelConfig: true` added
> - Landscape / portrait `R2V` models share the same new-version request body
> - Landscape `R2V` upstream `videoModelKey` switched to `*_landscape` form
> - Per current upstream protocol, `referenceImages` currently supports up to **3** images

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_r2v_fast_portrait` | R2V | Portrait |
| `veo_3_1_r2v_fast_landscape` | R2V | Landscape |
| `veo_3_1_r2v_fast_portrait_ultra` | R2V | Portrait |
| `veo_3_1_r2v_fast_landscape_ultra` | R2V | Landscape |
| `veo_3_1_r2v_fast_portrait_ultra_relaxed` | R2V | Portrait |
| `veo_3_1_r2v_fast_landscape_ultra_relaxed` | R2V | Landscape |

#### Video Upsample Models

These models do not directly call the upstream upsampler key. Instead, they first generate a video using the corresponding Veo 3.1 base model, then submit a 1080P/4K upsample request.

| Model Name | Description | Output |
|---------|---------|--------|
| `veo_3_1_t2v_landscape_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_portrait_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_landscape_1080p` | T2V Upsample | 1080P |
| `veo_3_1_t2v_portrait_1080p` | T2V Upsample | 1080P |
| `veo_3_1_t2v_landscape_4s_4k` | T2V 4s Upsample | 4K |
| `veo_3_1_t2v_portrait_4s_4k` | T2V 4s Upsample | 4K |
| `veo_3_1_t2v_landscape_4s_1080p` | T2V 4s Upsample | 1080P |
| `veo_3_1_t2v_portrait_4s_1080p` | T2V 4s Upsample | 1080P |
| `veo_3_1_t2v_landscape_6s_4k` | T2V 6s Upsample | 4K |
| `veo_3_1_t2v_portrait_6s_4k` | T2V 6s Upsample | 4K |
| `veo_3_1_t2v_landscape_6s_1080p` | T2V 6s Upsample | 1080P |
| `veo_3_1_t2v_portrait_6s_1080p` | T2V 6s Upsample | 1080P |
| `veo_3_1_t2v_fast_portrait_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_fast_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_fast_portrait_ultra_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_fast_ultra_4k` | T2V Upsample | 4K |
| `veo_3_1_t2v_fast_portrait_1080p` | T2V Upsample | 1080P |
| `veo_3_1_t2v_fast_1080p` | T2V Upsample | 1080P |
| `veo_3_1_t2v_fast_portrait_ultra_1080p` | T2V Upsample | 1080P |
| `veo_3_1_t2v_fast_ultra_1080p` | T2V Upsample | 1080P |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl_4k` | I2V Upsample | 4K |
| `veo_3_1_i2v_s_fast_ultra_fl_4k` | I2V Upsample | 4K |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl_1080p` | I2V Upsample | 1080P |
| `veo_3_1_i2v_s_fast_ultra_fl_1080p` | I2V Upsample | 1080P |
| `veo_3_1_i2v_s_landscape_4k` | I2V Upsample | 4K |
| `veo_3_1_i2v_s_portrait_4k` | I2V Upsample | 4K |
| `veo_3_1_i2v_s_landscape_1080p` | I2V Upsample | 1080P |
| `veo_3_1_i2v_s_portrait_1080p` | I2V Upsample | 1080P |
| `veo_3_1_i2v_s_landscape_4s_4k` | I2V 4s Upsample | 4K |
| `veo_3_1_i2v_s_portrait_4s_4k` | I2V 4s Upsample | 4K |
| `veo_3_1_i2v_s_landscape_4s_1080p` | I2V 4s Upsample | 1080P |
| `veo_3_1_i2v_s_portrait_4s_1080p` | I2V 4s Upsample | 1080P |
| `veo_3_1_i2v_s_landscape_6s_4k` | I2V 6s Upsample | 4K |
| `veo_3_1_i2v_s_portrait_6s_4k` | I2V 6s Upsample | 4K |
| `veo_3_1_i2v_s_landscape_6s_1080p` | I2V 6s Upsample | 1080P |
| `veo_3_1_i2v_s_portrait_6s_1080p` | I2V 6s Upsample | 1080P |
| `veo_3_1_r2v_fast_portrait_ultra_4k` | R2V Upsample | 4K |
| `veo_3_1_r2v_fast_landscape_ultra_4k` | R2V Upsample | 4K |
| `veo_3_1_r2v_fast_portrait_ultra_1080p` | R2V Upsample | 1080P |
| `veo_3_1_r2v_fast_landscape_ultra_1080p` | R2V Upsample | 1080P |

---

## API Usage Examples (Streaming Required)

> In addition to the OpenAI-compatible examples below, the service also supports the official Gemini format:
> - `POST /v1beta/models/{model}:generateContent`
> - `POST /models/{model}:generateContent`
> - `POST /v1beta/models/{model}:streamGenerateContent`
> - `POST /models/{model}:streamGenerateContent`
>
> The official Gemini format supports the following authentication methods:
> - `Authorization: Bearer <api_key>`
> - `x-goog-api-key: <api_key>`
> - `?key=<api_key>`
>
> The official Gemini image request body is compatible with:
> - `systemInstruction`
> - `contents[].parts[].text`
> - `contents[].parts[].inlineData`
> - `contents[].parts[].fileData.fileUri`
> - `generationConfig.responseModalities`
> - `generationConfig.imageConfig.aspectRatio`
> - `generationConfig.imageConfig.imageSize`

### Gemini Official generateContent (Text-to-Image)

> Verified with real tokens.
> For streaming responses, replace the path with `:streamGenerateContent?alt=sse`.

```bash
curl -X POST "http://localhost:8000/models/gemini-3.1-flash-image:generateContent" \
  -H "x-goog-api-key: han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "systemInstruction": {
      "parts": [
        {
          "text": "Return an image only."
        }
      ]
    },
    "contents": [
      {
        "role": "user",
        "parts": [
          {
            "text": "A red apple on a wooden table, studio lighting, minimalist background"
          }
        ]
      }
    ],
    "generationConfig": {
      "responseModalities": ["IMAGE"],
      "imageConfig": {
        "aspectRatio": "1:1",
        "imageSize": "1K"
      }
    }
  }'
```

### Text-to-Image

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-image-landscape",
    "messages": [
      {
        "role": "user",
        "content": "A cute cat playing in the garden"
      }
    ],
    "stream": true
  }'
```

### Image-to-Image

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-image-landscape",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Transform this image into a watercolor painting style"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<base64_encoded_image>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

### Text-to-Video

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo_3_1_t2v_fast_landscape",
    "messages": [
      {
        "role": "user",
        "content": "A kitten chasing a butterfly on the grass"
      }
    ],
    "stream": true
  }'
```

### First/Last Frame Video Generation

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo_3_1_i2v_s_fast_fl_landscape",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Transition from the first image to the second image"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<first_frame_base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,<last_frame_base64>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

### Reference-to-Video (Multi-Image)

> `R2V` is assembled server-side using the new-version video request body. Callers can continue to use OpenAI-compatible input.
> The server automatically maps landscape `R2V` to the latest `*_landscape` upstream model key.
> Currently supports up to **3 reference images**.

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer han1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "veo_3_1_r2v_fast_portrait",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Based on three reference images, generate a portrait video with smooth camera movement"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<ref_image_1_base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<ref_image_2_base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<ref_image_3_base64>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

---

## Configuration Overview

Configuration is TOML-based, loaded from `config/setting.toml` (falls back to `config/setting_example.toml`). At runtime, the database (`data/flow.db`) is the authoritative config store. All config keys below are preserved exactly as they appear in the source.

See [docs/CONFIGURATION_MAP.md](docs/CONFIGURATION_MAP.md) for the full configuration reference.

| Section | Key | Type | Default | Description |
|---------|-----|------|---------|-------------|
| `[global]` | `api_key` | string | `"han1234"` | API key for client authentication |
| `[global]` | `admin_username` | string | `"admin"` | Admin login username |
| `[global]` | `admin_password` | string | `"admin"` | Admin login password |
| `[flow]` | `labs_base_url` | string | `"https://labs.google/fx/api"` | Google Labs base URL |
| `[flow]` | `api_base_url` | string | `"https://aisandbox-pa.googleapis.com/v1"` | AI Sandbox API base URL |
| `[flow]` | `timeout` | int | `120` | General upstream request timeout (seconds) |
| `[flow]` | `max_retries` | int | `3` | Max retries per request |
| `[server]` | `host` | string | `"0.0.0.0"` | Bind address |
| `[server]` | `port` | int | `8000` | Bind port |
| `[debug]` | `enabled` | bool | `false` | Enable debug logging to `logs.txt` |
| `[debug]` | `mask_token` | bool | `true` | Mask tokens in logs |
| `[proxy]` | `proxy_enabled` | bool | `false` | Enable request proxy |
| `[proxy]` | `proxy_url` | string | `""` | Proxy URL for upstream requests |
| `[generation]` | `image_timeout` | int | `300` | Image generation overall timeout (seconds) |
| `[generation]` | `video_timeout` | int | `1500` | Video generation overall timeout (seconds) |
| `[call_logic]` | `call_mode` | string | `"default"` | Token selection: `"default"` (load-aware) or `"polling"` (round-robin) |
| `[admin]` | `error_ban_threshold` | int | `3` | Auto-disable token after N consecutive errors |
| `[cache]` | `enabled` | bool | `false` | Enable media caching |
| `[cache]` | `timeout` | int | `7200` | Cache TTL in seconds (0 = never expire) |
| `[cache]` | `base_url` | string | `""` | Base URL for cached file access |
| `[captcha]` | `captcha_method` | string | `"extension"` | Captcha method: `extension`/`yescaptcha`/`browser`/`personal`/`remote_browser` |
| `[captcha]` | `yescaptcha_api_key` | string | `""` | YesCaptcha API key |
| `[captcha]` | `yescaptcha_task_type` | string | `"RecaptchaV3TaskProxylessM1"` | YesCaptcha task type |

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) | Fork identity, principles, and sprint history |
| [docs/PRODUCT_OVERVIEW.md](docs/PRODUCT_OVERVIEW.md) | Core capabilities and API compatibility |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | High-level architecture overview |
| [docs/SYSTEM_MAP.md](docs/SYSTEM_MAP.md) | Source-based system map (Sprint 001) |
| [docs/ENTRYPOINTS.md](docs/ENTRYPOINTS.md) | Application entrypoints (Sprint 001) |
| [docs/CONFIGURATION_MAP.md](docs/CONFIGURATION_MAP.md) | Full configuration reference (Sprint 001) |
| [docs/MODULE_BOUNDARIES.md](docs/MODULE_BOUNDARIES.md) | Module dependency boundaries |
| [docs/GLOSSARY.md](docs/GLOSSARY.md) | Term definitions |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Migration roadmap |
| [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md) | Known risks and uncertainties |
| [docs/SECURITY_AND_COMPLIANCE.md](docs/SECURITY_AND_COMPLIANCE.md) | Security considerations and compliance |
| [docs/TRANSLATION_PLAN.md](docs/TRANSLATION_PLAN.md) | Phased translation plan |
| [docs/ENGLISH_SURFACE_AUDIT.md](docs/ENGLISH_SURFACE_AUDIT.md) | Chinese-language surface audit (Sprint 001A) |
| [docs/UPSTREAM_BASELINE.md](docs/UPSTREAM_BASELINE.md) | Upstream baseline reference |
| [README.zh-CN.md](README.zh-CN.md) | Original Chinese README |

---

## Security and Compliance

This section provides a high-level overview only. See [docs/SECURITY_AND_COMPLIANCE.md](docs/SECURITY_AND_COMPLIANCE.md) for full details.

### Upstream Service Terms

This project interfaces with Google's services. Users should be aware of Google's Terms of Service for Google Labs / VideoFX, Google's reCAPTCHA Terms of Service, and the rate limits and usage policies of the upstream service.

### Token Lifecycle

Session tokens (ST) and access tokens (AT) for Google accounts are stored in SQLite (`data/flow.db`). Tokens are sensitive credentials — the database file should be protected with filesystem permissions. The `debug.mask_token` config option controls whether tokens are masked in logs (default: `true`).

### Captcha Workflows

Multiple captcha modes are supported: third-party API services (YesCaptcha, CapMonster, EzCaptcha, CapSolver), browser-based captcha (Playwright headed browser), personal browser captcha (nodriver-based resident tab pool), and Chrome extension bridge. Third-party captcha services receive the site key and page URL. Browser-based captcha modes launch real browser instances. Captcha tokens are short-lived and not persisted.

### Proxy Behavior

HTTP/SOCKS5 proxy support is available for upstream requests, media downloads, and browser captcha. Proxy URLs are stored in the database. Separate request and media proxy paths are supported.

### Account/Session Handling

Per-token settings include concurrency limits, account tier, image/video capability flags, and ban state. The system manages project pools per token for upstream API project rotation. Automatic 429 rate-limit banning and unban-after-12-hours behavior is observed during source mapping.

---

## Project Status

| Sprint | Status | Description |
|--------|--------|-------------|
| Sprint 000 — Fork Baseline & English Project Brain | Completed | Documentation baseline created |
| Sprint 001 — Existing System Map | Completed | Source-based system map, entrypoints, config map, risk register |
| Sprint 001A — English Surface Audit | Completed | Audit of Chinese-language surfaces, translation plan |
| Sprint 001B — Safe README Translation | Active | English README, original Chinese preserved as README.zh-CN.md |

The project is now English-documented at the README and project-brain level. Runtime source code, UI surfaces, logs, error strings, and config comments have not yet been translated. See [docs/TRANSLATION_PLAN.md](docs/TRANSLATION_PLAN.md) for the phased translation approach and [docs/ROADMAP.md](docs/ROADMAP.md) for the full migration roadmap.

---

## Acknowledgments

- [PearNoDec](https://github.com/PearNoDec) for the YesCaptcha integration approach
- [raomaiping](https://github.com/raomaiping) for the headless captcha approach
- Thanks to all contributors and users of the upstream project!

---

## Contact

- Upstream issues: [GitHub Issues](https://github.com/TheSmallHanCat/flow2api/issues)

---

## Recent Upstream Updates

- `9f1d712` Synced personal captcha logic, including cleanup, browser parameters, and captcha method configuration.
- `da2ad06` Merged PR #133.
- `abd0c00` Fixed integration issues after PR #133 merge.
- `55431c9` Synced origin/main to PR #133.
- `4b7a0ad` Added Prometheus service metrics and token health monitoring.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=TheSmallHanCat/flow2api&type=date&legend=top-left)](https://www.star-history.com/#TheSmallHanCat/flow2api&type=date&legend=top-left)
