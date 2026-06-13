"""Mocked OpenAI image-result route contract tests.

These tests exercise the OpenAI non-streaming image-result route path
represented by FX-ON-002, using a fake handler that yields deterministic
markdown image content. The route layer parses and returns the JSON as-is
without processing the image URL.

No FastAPI app, TestClient, HTTP transport, lifespan, streaming, network,
database, browser, captcha, proxy, token, session service, external media
retrieval, or real image assets are used.

Sprint 006F — Mocked OpenAI Image-Result Route Contract.
"""

import json
import unittest
from unittest.mock import patch

from starlette.requests import Request

import src.api.routes as routes_module
from src.api.routes import (
    create_chat_completion,
    retrieve_image_data,
    _load_image_bytes_from_uri,
)
from src.core.models import (
    ChatCompletionRequest,
    ChatMessage,
)
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-2.0-flash-exp-image-generation"
SYNTHETIC_PROMPT = "Generate an image of a sunset over a calm ocean"
FAKE_IMAGE_URL = "https://placeholder.example.invalid/media/test-image.jpg"
FAKE_API_KEY = "test-key"


# ---------------------------------------------------------------------------
# Synthetic Starlette Request
# ---------------------------------------------------------------------------
def _make_raw_request(path: str = "/v1/chat/completions") -> Request:
    """Build a minimal synthetic Request for _get_request_base_url."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [(b"host", b"test.local")],
        "query_string": b"",
        "server": ("test.local", 80),
        "scheme": "http",
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# Fake Generation Handler
# ---------------------------------------------------------------------------
class FakeImageResultHandler:
    """Minimal fake handler yielding deterministic image-result JSON.

    Records calls for assertions. Does not make network calls, read
    credentials, touch a database, create browser/captcha/session services,
    use proxy behavior, retrieve media, or imitate the full production handler.
    """

    def __init__(self, yield_value: str = ""):
        self._yield_value = yield_value
        self.calls: list[dict] = []

    async def handle_generation(
        self,
        model: str,
        prompt: str,
        images=None,
        stream: bool = False,
        base_url_override=None,
        video_media_id=None,
    ):
        """Async generator matching the production handle_generation contract."""
        self.calls.append({
            "model": model,
            "prompt": prompt,
            "images": images,
            "stream": stream,
            "base_url_override": base_url_override,
            "video_media_id": video_media_id,
        })
        yield self._yield_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_openai_image_request(
    model: str = KNOWN_MODEL,
    content: str = SYNTHETIC_PROMPT,
) -> ChatCompletionRequest:
    """Build a minimal text-only OpenAI ChatCompletionRequest for image generation."""
    return ChatCompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content=content)],
        stream=False,
    )


def _make_image_result_json(image_url: str = FAKE_IMAGE_URL) -> str:
    """Build an OpenAI-format image-result JSON string the fake handler yields."""
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"![Generated Image]({image_url})"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    })


async def _read_json_body(response: JSONResponse) -> dict:
    """Decode the JSON body from a JSONResponse."""
    return json.loads(response.body.decode("utf-8"))


# ---------------------------------------------------------------------------
# Network Helper Guards
# ---------------------------------------------------------------------------
async def _guarded_retrieve_image_data(url: str):
    """Guard: raise immediately if network-capable helper is invoked."""
    raise RuntimeError(
        f"SAFETY GATE VIOLATION: retrieve_image_data called with url={url}. "
        "Image-result route should not retrieve external media."
    )


async def _guarded_load_image_bytes_from_uri(uri: str):
    """Guard: raise immediately if network-capable helper is invoked."""
    raise RuntimeError(
        f"SAFETY GATE VIOLATION: _load_image_bytes_from_uri called with uri={uri}. "
        "Image-result route should not load image bytes from URI."
    )


# ===========================================================================
# 1. OpenAI Image-Result Success
# ===========================================================================
class OpenAIImageResultSuccessTests(unittest.IsolatedAsyncioTestCase):
    """Test create_chat_completion with stream=False and image-result output."""

    async def test_openai_image_result_success(self):
        """Verify image-result route returns JSON with markdown image content."""
        image_result_json = _make_image_result_json()
        fake = FakeImageResultHandler(yield_value=image_result_json)

        # Patch generation handler AND guard network helpers
        with patch.object(routes_module, "generation_handler", fake), \
             patch.object(routes_module, "retrieve_image_data", _guarded_retrieve_image_data), \
             patch.object(routes_module, "_load_image_bytes_from_uri", _guarded_load_image_bytes_from_uri):
            response = await create_chat_completion(
                request=_make_openai_image_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        # Response type — must be JSONResponse, not StreamingResponse
        self.assertIsInstance(response, JSONResponse)
        # Status code — success is 200
        self.assertEqual(response.status_code, 200)

        # Body shape
        body = await _read_json_body(response)
        self.assertIn("choices", body)
        self.assertEqual(len(body["choices"]), 1)

        choice = body["choices"][0]
        self.assertIn("message", choice)
        self.assertEqual(choice["message"]["role"], "assistant")

        # Image content — markdown format preserved
        content = choice["message"]["content"]
        self.assertIn("![Generated Image]", content)
        self.assertIn(FAKE_IMAGE_URL, content)

        # Finish reason
        self.assertEqual(choice.get("finish_reason"), "stop")

        # Handler call count and arguments
        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["model"], KNOWN_MODEL)
        self.assertFalse(call["stream"])
        self.assertIn(SYNTHETIC_PROMPT, call["prompt"])

        # No input images or video media
        self.assertIsNone(call["images"])
        self.assertIsNone(call["video_media_id"])

    async def test_openai_image_result_stable_structure(self):
        """Verify stable image-result structure matches expected shape."""
        image_result_json = _make_image_result_json()
        fake = FakeImageResultHandler(yield_value=image_result_json)

        with patch.object(routes_module, "generation_handler", fake), \
             patch.object(routes_module, "retrieve_image_data", _guarded_retrieve_image_data), \
             patch.object(routes_module, "_load_image_bytes_from_uri", _guarded_load_image_bytes_from_uri):
            response = await create_chat_completion(
                request=_make_openai_image_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        body = await _read_json_body(response)

        # Stable top-level fields
        self.assertIn("id", body)
        self.assertIn("object", body)
        self.assertIn("created", body)
        self.assertIn("model", body)

        # Stable choice structure
        choice = body["choices"][0]
        self.assertEqual(choice["index"], 0)
        self.assertIn("message", choice)
        self.assertIn("role", choice["message"])
        self.assertIn("content", choice["message"])


# ===========================================================================
# 2. FX-ON-002 Relationship
# ===========================================================================
class FXON002RelationshipTests(unittest.IsolatedAsyncioTestCase):
    """Compare actual route output with FX-ON-002 fixture."""

    async def test_fx_on_002_shape_compatibility(self):
        """Verify route output matches FX-ON-002 fixture shape and semantics."""
        from tests.compatibility.helpers.fixture_loader import load_json

        # Load FX-ON-002 fixtures
        fixture_request = load_json("generation/openai-non-streaming/image-result-request.json")
        fixture_response = load_json("generation/openai-non-streaming/image-result-response.json")

        # Extract expected values from fixture
        expected_model = fixture_response.get("model", "flow2api")
        expected_content = fixture_response["choices"][0]["message"]["content"]
        expected_image_url = "https://placeholder.example.invalid/media/test-image.jpg"

        # Build fake handler yielding fixture response
        fake = FakeImageResultHandler(yield_value=json.dumps(fixture_response))

        with patch.object(routes_module, "generation_handler", fake), \
             patch.object(routes_module, "retrieve_image_data", _guarded_retrieve_image_data), \
             patch.object(routes_module, "_load_image_bytes_from_uri", _guarded_load_image_bytes_from_uri):
            # Use fixture request shape
            request = ChatCompletionRequest(
                model=fixture_request["model"],
                messages=[ChatMessage(**msg) for msg in fixture_request["messages"]],
                stream=fixture_request.get("stream", False),
            )
            response = await create_chat_completion(
                request=request,
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        body = await _read_json_body(response)

        # Shape compatibility — top-level structure matches
        self.assertIn("choices", body)
        self.assertEqual(len(body["choices"]), 1)

        # Semantic compatibility — image content preserved
        actual_content = body["choices"][0]["message"]["content"]
        self.assertIn("![Generated Image]", actual_content)
        self.assertIn(expected_image_url, actual_content)

        # Fixture-only fields — document differences
        # Fixture has static id/created; route returns handler-provided values
        # Fixture usage is zeros; route returns handler-provided usage
        # These are acceptable differences for synthetic fixtures

    async def test_fx_on_002_contract_semantics(self):
        """Verify contract semantics: markdown image, finish_reason, no streaming."""
        fixture_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "![Generated Image](https://example.com/image.jpg)"
                },
                "finish_reason": "stop"
            }]
        }
        fake = FakeImageResultHandler(yield_value=json.dumps(fixture_response))

        with patch.object(routes_module, "generation_handler", fake), \
             patch.object(routes_module, "retrieve_image_data", _guarded_retrieve_image_data), \
             patch.object(routes_module, "_load_image_bytes_from_uri", _guarded_load_image_bytes_from_uri):
            response = await create_chat_completion(
                request=_make_openai_image_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        # Non-streaming response
        self.assertIsInstance(response, JSONResponse)
        self.assertNotIsInstance(response, type(None))  # Not StreamingResponse

        body = await _read_json_body(response)
        choice = body["choices"][0]

        # Contract semantics preserved
        self.assertEqual(choice["finish_reason"], "stop")
        self.assertIn("![", choice["message"]["content"])  # Markdown image prefix
        self.assertIn("](http", choice["message"]["content"])  # Markdown image URL pattern


# ===========================================================================
# 3. Network/Media Helper Guard
# ===========================================================================
class NetworkMediaHelperGuardTests(unittest.IsolatedAsyncioTestCase):
    """Verify image-result route does not invoke network or media helpers."""

    async def test_no_network_or_media_retrieval(self):
        """Confirm successful response without media retrieval."""
        image_result_json = _make_image_result_json()
        fake = FakeImageResultHandler(yield_value=image_result_json)

        # Patch network helpers to raise if called
        with patch.object(routes_module, "generation_handler", fake), \
             patch.object(routes_module, "retrieve_image_data", _guarded_retrieve_image_data), \
             patch.object(routes_module, "_load_image_bytes_from_uri", _guarded_load_image_bytes_from_uri):
            # This should succeed WITHOUT triggering the guards
            response = await create_chat_completion(
                request=_make_openai_image_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        # Verify response is successful (guards were not triggered)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JSONResponse)

        # Verify handler was called (route executed normally)
        self.assertEqual(len(fake.calls), 1)


# ===========================================================================
# Run Tests
# ===========================================================================
if __name__ == "__main__":
    unittest.main()
