# Model Compatibility Map

> **Sprint 003 — Generation Contract Deep Dive**
> Documentation-only. No runtime behavior changes.

## Purpose

This document maps the model naming, listing, and resolution surfaces observed in the flow2api source. It identifies where model configuration lives, how aliases work, which model families exist, and which names are compatibility-sensitive.

## Model Listing Endpoints

| Endpoint | Format | Auth | Source |
|----------|--------|------|--------|
| `GET /v1/models` | OpenAI-compatible list | API key | `routes.py` L788–L801 |
| `GET /v1/models/aliases` | Alias-only list | API key | `routes.py` L804–L819 |
| `GET /v1beta/models` | Gemini-compatible list | API key | `routes.py` L822–L832 |
| `GET /models` | Same as v1beta (duplicate mount) | API key | Same |
| `GET /v1beta/models/{model}` | Single Gemini model resource | API key | `routes.py` L835–L847 |
| `GET /models/{model}` | Same as v1beta (duplicate mount) | API key | Same |

### /v1/models response shape

```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-3.0-pro-image-landscape",
      "object": "model",
      "owned_by": "flow2api",
      "description": "Image generation - GEM_PIX_2"
    }
  ]
}
```

**Observed in:** `_get_openai_model_catalog` (routes.py L107–L115), which iterates all `MODEL_CONFIG` keys.

### /v1/models/aliases response shape

```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-3.0-pro-image",
      "object": "model",
      "owned_by": "flow2api",
      "description": "Image generation (alias) - aspects: landscape, portrait, square, four-three, three-four; sizes: 2k, 4k",
      "is_alias": true
    }
  ]
}
```

**Observed in:** routes.py L804–L819, using `get_base_model_aliases()` from `model_resolver.py`.

### Gemini model resource shape

```json
{
  "name": "models/gemini-3.0-pro-image",
  "displayName": "gemini-3.0-pro-image",
  "description": "...",
  "version": "flow2api",
  "inputTokenLimit": 0,
  "outputTokenLimit": 0,
  "supportedGenerationMethods": ["generateContent", "streamGenerateContent"]
}
```

**Observed in:** `_build_gemini_model_resource` (routes.py L131–L144)

## Model Aliases Endpoint Behavior

The `/v1/models/aliases` endpoint returns **simplified model names** that the resolver can expand into full `MODEL_CONFIG` keys using `generationConfig` parameters.

**Alias sources** (observed in `model_resolver.py`):

- **Image aliases** from `IMAGE_BASE_MODELS` (L21–L28):
  - `gemini-3.0-pro-image`
  - `gemini-3.1-flash-image`
  - `imagen-4.0-generate-preview`

- **Video aliases** from `VIDEO_BASE_MODELS` (L125–L294):
  - `veo_3_1_t2v_fast`, `veo_3_1_t2v_fast_4s`, `veo_3_1_t2v_fast_6s`, `veo_3_1_t2v_fast_ultra`, etc.
  - I2V, R2V, interpolation, and extend variants
  - Each maps to landscape/portrait specific keys

The Gemini model catalog (`_get_gemini_model_catalog`, routes.py L118–L128) merges aliases + full `MODEL_CONFIG` keys, with aliases taking precedence for description.

## Where Model Registry / Config Appears to Live

### Primary registry: MODEL_CONFIG dict

- **Location:** `src/services/generation_handler.py` L23–L675 (static entries) + L730–L900 (dynamic updates via `_apply_veo_3_1_model_updates`)
- **Imported by:** `src/api/routes.py` (L24: `from ..services.generation_handler import MODEL_CONFIG`)
- **Structure per entry:**
  ```python
  "model-key-name": {
      "type": "image" | "video",
      # Image models:
      "model_name": "GEM_PIX_2" | "NARWHAL" | "IMAGEN_3_5",
      "aspect_ratio": "IMAGE_ASPECT_RATIO_LANDSCAPE" | ...,
      "upsample": "UPSAMPLE_IMAGE_RESOLUTION_2K" | ...,  # optional
      # Video models:
      "video_type": "t2v" | "i2v" | "r2v" | "extend",
      "model_key": "upstream_model_key",
      "aspect_ratio": "VIDEO_ASPECT_RATIO_LANDSCAPE" | "VIDEO_ASPECT_RATIO_PORTRAIT",
      "supports_images": bool,
      "min_images": int,  # optional
      "max_images": int,  # optional
      "upsample": {"resolution": "...", "model_key": "..."},  # optional, video
      "use_v2_model_config": bool,  # optional
      "allow_tier_upgrade": bool,   # optional
      "requires_video_id": bool,    # extend models
  }
  ```

### Dynamic model updates

`_apply_veo_3_1_model_updates()` (generation_handler.py L730–L900) runs at module import time and:

- Remaps certain model keys (e.g., `veo_3_1_t2v_landscape` → `veo_3_1_t2v`)
- Creates duration variants (4s, 6s) for T2V and I2V models
- Creates resolution variants (4k, 1080p) using upsample configs
- Adds landscape-explicit aliases for `/v1/models` listing

## Where Model Resolution Appears to Happen

Model resolution is handled by `resolve_model_name` in `src/core/model_resolver.py` (L515–L613):

1. **Direct match:** If `model` is already a valid `MODEL_CONFIG` key → return as-is (L609)
2. **Image alias:** If `model` is in `IMAGE_BASE_MODELS` → extract `aspectRatio` + `imageSize` from `generationConfig` → construct `{base}-{aspect}[-{size}]` (L533–L577)
3. **Video alias:** If `model` is in `VIDEO_BASE_MODELS` → extract `aspectRatio` → look up orientation map (L580–L606)
4. **Unknown:** Return original name (will fail `MODEL_CONFIG` validation downstream, L612)

**Resolution is called from:** `_resolve_request_model` in routes.py (L403–L407), which is invoked during both OpenAI and Gemini request normalization.

## Model Families / Categories Observed

### Image models

| Family | Internal name | Alias | Aspects | Sizes |
|--------|---------------|-------|---------|-------|
| Gemini 3.0 Pro Image | `GEM_PIX_2` | `gemini-3.0-pro-image` | landscape, portrait, square, four-three, three-four | 2k, 4k |
| Gemini 3.1 Flash Image | `NARWHAL` | `gemini-3.1-flash-image` | landscape, portrait, square, four-three, three-four | 2k, 4k |
| Imagen 4.0 | `IMAGEN_3_5` | `imagen-4.0-generate-preview` | landscape, portrait | (none) |

### Video models

| Family | Video types | Orientation | Duration variants | Resolution variants |
|--------|-------------|-------------|-------------------|---------------------|
| veo_3_1_t2v_fast | T2V | landscape, portrait | default, 4s, 6s | 4k, 1080p |
| veo_3_1_t2v_fast_ultra | T2V | landscape, portrait | default | 4k, 1080p |
| veo_3_1_t2v_fast_ultra_relaxed | T2V | landscape, portrait | default | — |
| veo_3_1_t2v (quality) | T2V | landscape, portrait | default, 4s, 6s | 4k, 1080p |
| veo_3_1_t2v_lite | T2V | landscape, portrait | default, 4s, 6s | — |
| veo_3_1_i2v_s_fast (fl) | I2V | landscape, portrait | default, 4s, 6s | 4k, 1080p |
| veo_3_1_i2v_s_fast_ultra (fl) | I2V | landscape, portrait | default | 4k, 1080p |
| veo_3_1_i2v_s_fast_ultra_relaxed | I2V | landscape, portrait | default | — |
| veo_3_1_i2v_s (quality) | I2V | landscape, portrait | default, 4s, 6s | 4k, 1080p |
| veo_3_1_i2v_lite | I2V | landscape, portrait | default, 4s, 6s | — |
| veo_3_1_interpolation_lite | I2V | landscape, portrait | default, 4s, 6s | — |
| veo_3_1_r2v_fast | R2V | landscape, portrait | — | — |
| veo_3_1_r2v_fast_ultra | R2V | landscape, portrait | — | 4k, 1080p |
| veo_3_1_r2v_fast_ultra_relaxed | R2V | landscape, portrait | — | — |
| veo_3_1_extend | Extend | landscape, portrait | — | — |

## Which Model Names/Aliases Appear Compatibility-Sensitive

1. **Image alias names** (`gemini-3.0-pro-image`, `gemini-3.1-flash-image`, `imagen-4.0-generate-preview`) — upstream clients like NewAPI send these as the `model` field with `generationConfig` params; renaming would break compatibility
2. **Video base names** (`veo_3_1_t2v_fast`, `veo_3_1_i2v_s_fast_fl`, etc.) — same alias-based resolution pattern
3. **Internal upstream model names** (`GEM_PIX_2`, `NARWHAL`, `IMAGEN_3_5`) — these are sent to the upstream Flow API; changing them would break generation
4. **`model_key` values** in video configs (e.g., `veo_3_1_t2v_fast`, `veo_3_1_i2v_s_fast_portrait_fl`) — sent directly to upstream; must match what the upstream API expects
5. **Aspect ratio enums** (`IMAGE_ASPECT_RATIO_LANDSCAPE`, `VIDEO_ASPECT_RATIO_PORTRAIT`, etc.) — upstream protocol constants
6. **The `"flow2api"` value in model listing** — appears as `owned_by` in OpenAI format and `version` in Gemini format; clients may filter or validate against this

## Unknowns Requiring Fixture Verification

1. **Total MODEL_CONFIG key count** — after `_apply_veo_3_1_model_updates`, the actual number of keys is large; the exact count should be verified by runtime inspection
2. **Alias collision behavior** — when a video alias like `veo_3_1_t2v` is both a `VIDEO_BASE_MODELS` key and a `MODEL_CONFIG` key, which resolution path wins depends on call order
3. **Tier-based model key mutation** — `_resolve_video_model_key_for_tier` can change model keys at runtime based on user paygate tier; the exact set of valid mutations is not exhaustively verifiable from source alone
4. **`use_v2_model_config` flag** — appears to influence upstream request format but the exact upstream behavior is unknown
5. **`allow_tier_upgrade: false`** — prevents ultra model upgrade for lite/interpolation models; interaction with tier logic needs runtime testing
6. **Imagen 4.0 aspect ratio limitation** — only landscape and portrait supported; what happens when a client requests square/4:3/3:4 via alias needs fixture testing
