# Flow2API

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.119.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)

**A fully-featured OpenAI-compatible API service providing a unified interface for Flow**

</div>

## ✨ Core Features

- 🎨 **Text-to-Image** / **Image-to-Image**
- 🎬 **Text-to-Video** / **Image-to-Video**
- 🎞️ **First-and-Last-Frame Video**
- 🔄 **Automatic AT/ST Refresh** - Auto-refresh when AT expires; auto-update via browser when ST expires (personal mode)
- 📊 **Balance Display** - Real-time query and display of VideoFX Credits
- 🚀 **Load Balancing** - Multi-token round-robin and concurrency control
- 🌐 **Proxy Support** - Supports HTTP/SOCKS5 proxies
- 📱 **Web Admin Interface** - Intuitive token and configuration management
- 🎨 **Continuous Image Generation Conversations**
- 🧩 **Gemini Official Request Body Compatible** - Supports `generateContent` / `streamGenerateContent`, `systemInstruction`, `contents.parts.text/inlineData/fileData`
- ✅ **Gemini Official Format Verified with Real Image Output** - Verified with real tokens that `/models/{model}:generateContent` returns official `candidates[].content.parts[].inlineData`

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose (recommended)
- Or Python 3.8+

- Since Flow added an extra captcha, you may choose to use browser captcha solving or a third-party captcha service:
Register at [YesCaptcha](https://yescaptcha.com/i/13Xd8K) and obtain an API key, then enter it in the ```YesCaptcha API Key``` field on the system config page.
- YesCaptcha supports switching `type` on the admin page: `RecaptchaV3TaskProxyless`, `RecaptchaV3TaskProxylessM1`, `RecaptchaV3TaskProxylessM1S7`, `RecaptchaV3TaskProxylessM1S9`; the current default recommendation is `M1S9`. S7/S9 will forcibly submit `minScore` 0.7/0.9.
- The default `docker-compose.yml` is recommended with a third-party captcha service (yescaptcha/capmonster/ezcaptcha/capsolver).
If you need headed captcha solving inside Docker (browser/personal), use `docker-compose.headed.yml` below.

- Auto-update ST browser extension: [Flow2API-Token-Updater](https://github.com/TheSmallHanCat/Flow2API-Token-Updater)

### Method 1: Docker Deployment (Recommended)

#### Standard Mode (without proxy)

```bash
# Clone the project
git clone https://github.com/TheSmallHanCat/flow2api.git
cd flow2api

# Start the service
docker-compose up -d

# View logs
docker-compose logs -f
```

> Note: Compose mounts `./tmp:/app/tmp` by default. Setting cache timeout to `0` means "no automatic expiration deletion"; if you want cache files to persist after container rebuilds, keep this `tmp` mount.

#### WARP Mode (with proxy)

```bash
# Start with WARP proxy
docker-compose -f docker-compose.warp.yml up -d

# View logs
docker-compose -f docker-compose.warp.yml logs -f
```

#### Docker Headed Captcha Mode (browser / personal)

> For scenarios where you need a virtualized desktop and want to enable headed browser captcha solving inside the container.  
> This mode starts `Xvfb + Fluxbox` by default for in-container visualization, with `ALLOW_DOCKER_HEADED_CAPTCHA=true`.  
> Only the application port is exposed; no remote desktop connection ports are provided.
> The built-in `personal` browser now starts in headed mode by default; to temporarily switch back to headless, also set the environment variable `PERSONAL_BROWSER_HEADLESS=true`.

```bash
# Start headed mode (recommend --build on first run)
docker compose -f docker-compose.headed.yml up -d --build

# View logs
docker compose -f docker-compose.headed.yml logs -f
```

- API port: `8000`
- After entering the admin backend, set the captcha method to `browser` or `personal`.

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

After the service starts, visit the admin backend at: **http://localhost:8000**. Please change your password immediately after the first login!

- **Username**: `admin`
- **Password**: `admin`

## 📈 Monitoring Endpoints

- `GET /health`: Public health check, returns a summary including service liveness, active token count, tokens about to expire, expired tokens, and 429-banned count.
- `GET /metrics`: Prometheus metrics endpoint
- `GET /api/tokens`: Admin endpoint, returns token statuses such as `at_expires`, `at_expired`, `at_expiring_within_1h`, `ban_reason`, `consecutive_error_count`.

Prometheus can scrape `/metrics` directly. If deploying to Kubernetes, it is recommended to scrape only within the cluster, and separately restrict external access to `/metrics` at the Ingress/Gateway layer.

### Model Test Page

Visit **http://localhost:8000/test** to open the built-in model test page, supporting:

- Browse all available models by category (image generation, text/image-to-video, multi-image video, video upsample, etc.)
- One-click testing by entering a prompt, streaming the generation progress
- Image-to-image / image-to-video scenarios support uploading images
- Direct preview of generated images or videos after completion

## 📋 Supported Models

### Image Generation

| Model Name | Description | Size |
|---------|--------|--------|
| `gemini-3.0-pro-image-landscape` | Image/Text-to-Image | Landscape |
| `gemini-3.0-pro-image-portrait` | Image/Text-to-Image | Portrait |
| `gemini-3.0-pro-image-square` | Image/Text-to-Image | Square |
| `gemini-3.0-pro-image-four-three` | Image/Text-to-Image | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four` | Image/Text-to-Image | Portrait 3:4 |
| `gemini-3.0-pro-image-landscape-2k` | Image/Text-to-Image (2K) | Landscape |
| `gemini-3.0-pro-image-portrait-2k` | Image/Text-to-Image (2K) | Portrait |
| `gemini-3.0-pro-image-square-2k` | Image/Text-to-Image (2K) | Square |
| `gemini-3.0-pro-image-four-three-2k` | Image/Text-to-Image (2K) | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four-2k` | Image/Text-to-Image (2K) | Portrait 3:4 |
| `gemini-3.0-pro-image-landscape-4k` | Image/Text-to-Image (4K) | Landscape |
| `gemini-3.0-pro-image-portrait-4k` | Image/Text-to-Image (4K) | Portrait |
| `gemini-3.0-pro-image-square-4k` | Image/Text-to-Image (4K) | Square |
| `gemini-3.0-pro-image-four-three-4k` | Image/Text-to-Image (4K) | Landscape 4:3 |
| `gemini-3.0-pro-image-three-four-4k` | Image/Text-to-Image (4K) | Portrait 3:4 |
| `imagen-4.0-generate-preview-landscape` | Image/Text-to-Image | Landscape |
| `imagen-4.0-generate-preview-portrait` | Image/Text-to-Image | Portrait |
| `gemini-3.1-flash-image-landscape` | Image/Text-to-Image | Landscape |
| `gemini-3.1-flash-image-portrait` | Image/Text-to-Image | Portrait |
| `gemini-3.1-flash-image-square` | Image/Text-to-Image | Square |
| `gemini-3.1-flash-image-four-three` | Image/Text-to-Image | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four` | Image/Text-to-Image | Portrait 3:4 |
| `gemini-3.1-flash-image-landscape-2k` | Image/Text-to-Image (2K) | Landscape |
| `gemini-3.1-flash-image-portrait-2k` | Image/Text-to-Image (2K) | Portrait |
| `gemini-3.1-flash-image-square-2k` | Image/Text-to-Image (2K) | Square |
| `gemini-3.1-flash-image-four-three-2k` | Image/Text-to-Image (2K) | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four-2k` | Image/Text-to-Image (2K) | Portrait 3:4 |
| `gemini-3.1-flash-image-landscape-4k` | Image/Text-to-Image (4K) | Landscape |
| `gemini-3.1-flash-image-portrait-4k` | Image/Text-to-Image (4K) | Portrait |
| `gemini-3.1-flash-image-square-4k` | Image/Text-to-Image (4K) | Square |
| `gemini-3.1-flash-image-four-three-4k` | Image/Text-to-Image (4K) | Landscape 4:3 |
| `gemini-3.1-flash-image-three-four-4k` | Image/Text-to-Image (4K) | Portrait 3:4 |

### Video Generation

#### Text-to-Video (T2V - Text to Video)
⚠️ **Image upload is not supported**

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_t2v_fast_portrait` | Text-to-Video | Portrait |
| `veo_3_1_t2v_fast_landscape` | Text-to-Video | Landscape |
| `veo_3_1_t2v_fast_portrait_ultra` | Text-to-Video | Portrait |
| `veo_3_1_t2v_fast_ultra` | Text-to-Video | Landscape |
| `veo_3_1_t2v_fast_portrait_ultra_relaxed` | Text-to-Video | Portrait |
| `veo_3_1_t2v_fast_ultra_relaxed` | Text-to-Video | Landscape |
| `veo_3_1_t2v_portrait` | Text-to-Video | Portrait |
| `veo_3_1_t2v_landscape` | Text-to-Video | Landscape |
| `veo_3_1_t2v_landscape_4s` | Text-to-Video 4s | Landscape |
| `veo_3_1_t2v_portrait_4s` | Text-to-Video 4s | Portrait |
| `veo_3_1_t2v_landscape_6s` | Text-to-Video 6s | Landscape |
| `veo_3_1_t2v_portrait_6s` | Text-to-Video 6s | Portrait |
| `veo_3_1_t2v_fast_landscape_4s` | Text-to-Video Fast 4s | Landscape |
| `veo_3_1_t2v_fast_portrait_4s` | Text-to-Video Fast 4s | Portrait |
| `veo_3_1_t2v_fast_landscape_6s` | Text-to-Video Fast 6s | Landscape |
| `veo_3_1_t2v_fast_portrait_6s` | Text-to-Video Fast 6s | Portrait |
| `veo_3_1_t2v_lite_portrait` | Text-to-Video Lite | Portrait |
| `veo_3_1_t2v_lite_landscape` | Text-to-Video Lite | Landscape |
| `veo_3_1_t2v_lite_4s_portrait` | Text-to-Video Lite 4s | Portrait |
| `veo_3_1_t2v_lite_4s_landscape` | Text-to-Video Lite 4s | Landscape |
| `veo_3_1_t2v_lite_6s_portrait` | Text-to-Video Lite 6s | Portrait |
| `veo_3_1_t2v_lite_6s_landscape` | Text-to-Video Lite 6s | Landscape |

#### First-and-Last-Frame Models (I2V - Image to Video)
📸 **Supports 1-2 images: 1 image as first frame, 2 images as first-and-last frames**

> 💡 **Auto-Adapt**: The system automatically selects the corresponding model_key based on the number of images.
> - **Single-frame mode** (1 image): generates video from the first frame
> - **Two-frame mode** (2 images): generates transition video from first frame + last frame
> - `veo_3_1_i2v_lite_*` supports only **1** first-frame image
> - `veo_3_1_interpolation_lite_*` supports only **2** first-and-last-frame images

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_i2v_s_fast_portrait_fl` | Image-to-Video | Portrait |
| `veo_3_1_i2v_s_fast_fl` | Image-to-Video | Landscape |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl` | Image-to-Video | Portrait |
| `veo_3_1_i2v_s_fast_ultra_fl` | Image-to-Video | Landscape |
| `veo_3_1_i2v_s_fast_portrait_ultra_relaxed` | Image-to-Video | Portrait |
| `veo_3_1_i2v_s_fast_ultra_relaxed` | Image-to-Video | Landscape |
| `veo_3_1_i2v_s_portrait` | Image-to-Video | Portrait |
| `veo_3_1_i2v_s_landscape` | Image-to-Video | Landscape |
| `veo_3_1_i2v_s_landscape_4s` | Image-to-Video 4s | Landscape |
| `veo_3_1_i2v_s_portrait_4s` | Image-to-Video 4s | Portrait |
| `veo_3_1_i2v_s_landscape_6s` | Image-to-Video 6s | Landscape |
| `veo_3_1_i2v_s_portrait_6s` | Image-to-Video 6s | Portrait |
| `veo_3_1_i2v_s_fast_landscape_4s_fl` | Image-to-Video Fast 4s | Landscape |
| `veo_3_1_i2v_s_fast_portrait_4s_fl` | Image-to-Video Fast 4s | Portrait |
| `veo_3_1_i2v_s_fast_landscape_6s_fl` | Image-to-Video Fast 6s | Landscape |
| `veo_3_1_i2v_s_fast_portrait_6s_fl` | Image-to-Video Fast 6s | Portrait |
| `veo_3_1_i2v_lite_portrait` | Image-to-Video Lite (first frame only) | Portrait |
| `veo_3_1_i2v_lite_landscape` | Image-to-Video Lite (first frame only) | Landscape |
| `veo_3_1_i2v_lite_4s_portrait` | Image-to-Video Lite 4s (first frame only) | Portrait |
| `veo_3_1_i2v_lite_4s_landscape` | Image-to-Video Lite 4s (first frame only) | Landscape |
| `veo_3_1_i2v_lite_6s_portrait` | Image-to-Video Lite 6s (first frame only) | Portrait |
| `veo_3_1_i2v_lite_6s_landscape` | Image-to-Video Lite 6s (first frame only) | Landscape |
| `veo_3_1_interpolation_lite_portrait` | Image-to-Video Lite (first-and-last-frame transition) | Portrait |
| `veo_3_1_interpolation_lite_landscape` | Image-to-Video Lite (first-and-last-frame transition) | Landscape |
| `veo_3_1_interpolation_lite_4s_portrait` | Image-to-Video Lite 4s (first-and-last-frame transition) | Portrait |
| `veo_3_1_interpolation_lite_4s_landscape` | Image-to-Video Lite 4s (first-and-last-frame transition) | Landscape |
| `veo_3_1_interpolation_lite_6s_portrait` | Image-to-Video Lite 6s (first-and-last-frame transition) | Portrait |
| `veo_3_1_interpolation_lite_6s_landscape` | Image-to-Video Lite 6s (first-and-last-frame transition) | Landscape |

#### Multi-Image Generation (R2V - Reference Images to Video)
🖼️ **Supports multiple images**

> **2026-03-06 Update**
>
> - Synced with upstream's new `R2V` video request body
> - `textInput` switched to `structuredPrompt.parts`
> - Added top-level `mediaGenerationContext.batchId`
> - Added top-level `useV2ModelConfig: true`
> - Landscape / portrait `R2V` models share the same new request body
> - Landscape `R2V` upstream `videoModelKey` switched to the `*_landscape` form
> - Per the current upstream protocol, `referenceImages` currently supports up to **3 images**

| Model Name | Description | Size |
|---------|---------|--------|
| `veo_3_1_r2v_fast_portrait` | Image-to-Video | Portrait |
| `veo_3_1_r2v_fast_landscape` | Image-to-Video | Landscape |
| `veo_3_1_r2v_fast_portrait_ultra` | Image-to-Video | Portrait |
| `veo_3_1_r2v_fast_landscape_ultra` | Image-to-Video | Landscape |
| `veo_3_1_r2v_fast_portrait_ultra_relaxed` | Image-to-Video | Portrait |
| `veo_3_1_r2v_fast_landscape_ultra_relaxed` | Image-to-Video | Landscape |

#### Video Upsample Models (Upsample)

These models do not directly call the upstream upsampler key; instead they first generate a video using the corresponding Veo 3.1 regular model, then submit a 1080P/4K upscale request.

| Model Name | Description | Output |
|---------|---------|--------|
| `veo_3_1_t2v_landscape_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_portrait_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_landscape_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_t2v_portrait_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_t2v_landscape_4s_4k` | Text-to-Video 4s upscale | 4K |
| `veo_3_1_t2v_portrait_4s_4k` | Text-to-Video 4s upscale | 4K |
| `veo_3_1_t2v_landscape_4s_1080p` | Text-to-Video 4s upscale | 1080P |
| `veo_3_1_t2v_portrait_4s_1080p` | Text-to-Video 4s upscale | 1080P |
| `veo_3_1_t2v_landscape_6s_4k` | Text-to-Video 6s upscale | 4K |
| `veo_3_1_t2v_portrait_6s_4k` | Text-to-Video 6s upscale | 4K |
| `veo_3_1_t2v_landscape_6s_1080p` | Text-to-Video 6s upscale | 1080P |
| `veo_3_1_t2v_portrait_6s_1080p` | Text-to-Video 6s upscale | 1080P |
| `veo_3_1_t2v_fast_portrait_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_fast_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_fast_portrait_ultra_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_fast_ultra_4k` | Text-to-Video upscale | 4K |
| `veo_3_1_t2v_fast_portrait_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_t2v_fast_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_t2v_fast_portrait_ultra_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_t2v_fast_ultra_1080p` | Text-to-Video upscale | 1080P |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl_4k` | Image-to-Video upscale | 4K |
| `veo_3_1_i2v_s_fast_ultra_fl_4k` | Image-to-Video upscale | 4K |
| `veo_3_1_i2v_s_fast_portrait_ultra_fl_1080p` | Image-to-Video upscale | 1080P |
| `veo_3_1_i2v_s_fast_ultra_fl_1080p` | Image-to-Video upscale | 1080P |
| `veo_3_1_i2v_s_landscape_4k` | Image-to-Video upscale | 4K |
| `veo_3_1_i2v_s_portrait_4k` | Image-to-Video upscale | 4K |
| `veo_3_1_i2v_s_landscape_1080p` | Image-to-Video upscale | 1080P |
| `veo_3_1_i2v_s_portrait_1080p` | Image-to-Video upscale | 1080P |
| `veo_3_1_i2v_s_landscape_4s_4k` | Image-to-Video 4s upscale | 4K |
| `veo_3_1_i2v_s_portrait_4s_4k` | Image-to-Video 4s upscale | 4K |
| `veo_3_1_i2v_s_landscape_4s_1080p` | Image-to-Video 4s upscale | 1080P |
| `veo_3_1_i2v_s_portrait_4s_1080p` | Image-to-Video 4s upscale | 1080P |
| `veo_3_1_i2v_s_landscape_6s_4k` | Image-to-Video 6s upscale | 4K |
| `veo_3_1_i2v_s_portrait_6s_4k` | Image-to-Video 6s upscale | 4K |
| `veo_3_1_i2v_s_landscape_6s_1080p` | Image-to-Video 6s upscale | 1080P |
| `veo_3_1_i2v_s_portrait_6s_1080p` | Image-to-Video 6s upscale | 1080P |
| `veo_3_1_r2v_fast_portrait_ultra_4k` | Multi-image video upscale | 4K |
| `veo_3_1_r2v_fast_landscape_ultra_4k` | Multi-image video upscale | 4K |
| `veo_3_1_r2v_fast_portrait_ultra_1080p` | Multi-image video upscale | 1080P |
| `veo_3_1_r2v_fast_landscape_ultra_1080p` | Multi-image video upscale | 1080P |

## 📡 API Usage Examples (streaming required)

> In addition to the `OpenAI-compatible` examples below, the service also supports Gemini official format:
> - `POST /v1beta/models/{model}:generateContent`
> - `POST /models/{model}:generateContent`
> - `POST /v1beta/models/{model}:streamGenerateContent`
> - `POST /models/{model}:streamGenerateContent`
>
> Gemini official format supports the following authentication methods:
> - `Authorization: Bearer <api_key>`
> - `x-goog-api-key: <api_key>`
> - `?key=<api_key>`
>
> Gemini official image request body is compatible with:
> - `systemInstruction`
> - `contents[].parts[].text`
> - `contents[].parts[].inlineData`
> - `contents[].parts[].fileData.fileUri`
> - `generationConfig.responseModalities`
> - `generationConfig.imageConfig.aspectRatio`
> - `generationConfig.imageConfig.imageSize`

### Gemini Official generateContent (Text-to-Image)

> Verified with real tokens.
> For streaming response, replace the path with `:streamGenerateContent?alt=sse`.

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
        "content": "A cute cat playing in a garden"
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
            "text": "Turn this image into a watercolor painting style"
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

### First-and-Last-Frame Video

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

### Multi-Image Video

> `R2V` will be automatically assembled by the server into the new video request body; the caller still uses OpenAI-compatible input.
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
            "text": "Using the characters and scenes from the three reference images, generate a portrait video with a smooth, forward-pushing camera"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<reference_image_1_base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<reference_image_2_base64>"
            }
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64/<reference_image_3_base64>"
            }
          }
        ]
      }
    ],
    "stream": true
  }'
```

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [PearNoDec](https://github.com/PearNoDec) for the YesCaptcha solving solution
- [raomaiping](https://github.com/raomaiping) for the headless captcha solving solution

Thanks to all contributors and users for their support!

---

## 📞 Contact

- Submit an issue: [GitHub Issues](https://github.com/TheSmallHanCat/flow2api/issues)

---

**⭐ If this project helps you, please give it a Star!**

## Recent Updates

- `9f1d712` Synced personal captcha-solving logic, including cleanup, browser parameters, and captcha method configuration.
- `da2ad06` Merged PR #133.
- `abd0c00` Fixed integration issues after merging PR #133.
- `55431c9` Synced origin/main to PR #133.
- `4b7a0ad` Added Prometheus service metrics and Token health monitoring.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=TheSmallHanCat/flow2api&type=date&legend=top-left)](https://www.star-history.com/#TheSmallHanCat/flow2api&type=date&legend=top-left)
