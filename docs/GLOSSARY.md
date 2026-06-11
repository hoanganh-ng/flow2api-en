# GLOSSARY.md

## Terms and Concepts

| Term | Definition |
|------|-----------|
| **AT** | Access Token — a short-lived token derived from ST, used to authenticate generation requests to upstream |
| **ST** | Session Token — `__Secure-next-auth.session-token` cookie from Google Labs, used to obtain AT |
| **Flow** | Google's internal media generation service (also called VideoFX or AI Sandbox) |
| **VideoFX** | Google's VideoFX product, the upstream service this project wraps |
| **AI Sandbox** | Google's `aisandbox-pa.googleapis.com` API endpoint used for generation |
| **Labs** | `labs.google/fx/api` — Google Labs endpoint used for project management |
| **T2V** | Text-to-Video generation |
| **T2I** | Text-to-Image generation |
| **I2V** | Image-to-Video generation (first-frame or first+last-frame) |
| **R2V** | Reference-to-Video generation (up to 3 reference images) |
| **Upsample** | Video upscaling to 1080P or 4K after initial generation |
| **MODEL_CONFIG** | Master dictionary in `generation_handler.py` mapping internal model IDs to upstream keys and types |
| **model_key** | The upstream model identifier sent to Google's API (e.g., `GEM_PIX_2_LANDSCAPE`) |
| **NormalizedGenerationRequest** | Internal data class unifying OpenAI and Gemini request formats |
| **generationConfig** | Gemini API parameter block containing `responseModalities`, `imageConfig` (aspectRatio, imageSize) |
| **Captcha / 打码** | Solving reCAPTCHA challenges to refresh Google session tokens |
| **Extension mode** | Captcha solving via Chrome Manifest V3 extension connected over WebSocket |
| **Personal mode** | Captcha solving via nodriver (undetected Chrome) with project pool rotation |
| **Browser mode** | Captcha solving via headed Playwright browser instances |
| **Remote browser** | Captcha solving via external headed browser HTTP service |
| **YesCaptcha** | Third-party reCAPTCHA solving API service |
| **CapMonster** | Third-party reCAPTCHA solving API service |
| **EzCaptcha** | Third-party reCAPTCHA solving API service |
| **CapSolver** | Third-party reCAPTCHA solving API service |
| **curl_cffi** | Python HTTP library with TLS fingerprint impersonation (used to mimic Chrome) |
| **nodriver** | Python library for undetected Chrome automation (successor to undetected-chromedriver) |
| **Playwright** | Browser automation library used for headed captcha mode |
| **429 ban** | Automatic token disabling after receiving HTTP 429 (rate limit) from upstream |
| **Error ban** | Automatic token disabling after N consecutive errors (configurable threshold) |
| **Call logic** | Token selection strategy: `default` (random weighted) or `polling` (sequential) |
| **Concurrency slot** | In-memory semaphore limiting simultaneous requests per token |
| **File cache** | Local storage of generated media with configurable TTL |
| **New API / One API** | Third-party API gateway projects that can front this service |
| **SSE** | Server-Sent Events — streaming format used for real-time generation progress |
| **Warmup** | Pre-starting browser tabs/projects at service startup to reduce first-request latency |
| **Project pool** | Set of Google Labs projects maintained per token for captcha rotation |
| **Paygate tier** | Account classification (e.g., `PAYGATE_TIER_ONE`) affecting available features |
| **Upstream** | Google's Flow/VideoFX service (the thing being proxied) |
| **Downstream** | Clients consuming the OpenAI/Gemini compatible API |

## File Abbreviations

| Abbreviation | File |
|-------------|------|
| `routes.py` | `src/api/routes.py` |
| `admin.py` | `src/api/admin.py` |
| `config.py` | `src/core/config.py` |
| `database.py` | `src/core/database.py` |
| `flow_client.py` | `src/services/flow_client.py` |
| `generation_handler.py` | `src/services/generation_handler.py` |
| `token_manager.py` | `src/services/token_manager.py` |
| `setting.toml` | `config/setting.toml` |
