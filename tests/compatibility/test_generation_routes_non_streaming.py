"""Mocked non-streaming generation route tests.

These tests exercise the OpenAI and Gemini non-streaming generation routes
via direct Python function calls with a fake handler, covering text success,
handler-uninitialized behavior, and deterministic handler-error conversion.

No FastAPI app, TestClient, HTTP transport, lifespan, streaming, network,
database, browser, captcha, proxy, token, or session service is used.

Sprint 006E — Mocked Non-Streaming Generation Route Tests.
"""

import json
import unittest
from unittest.mock import patch

from starlette.requests import Request

import src.api.routes as routes_module
from src.api.routes import (
    create_chat_completion,
    generate_content,
)
from src.core.models import (
    ChatCompletionRequest,
    ChatMessage,
    GeminiContent,
    GeminiGenerateContentRequest,
    GeminiPart,
)
from fastapi import HTTPException
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-3.0-pro-image-landscape"
SYNTHETIC_PROMPT = "Describe a sunset over the ocean"
FAKE_API_KEY = "test-key"  # Supplies the already-resolved dependency parameter


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
class FakeGenerationHandler:
    """Minimal fake handler implementing only the async-generator contract.

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
def _make_openai_request(
    model: str = KNOWN_MODEL,
    content: str = SYNTHETIC_PROMPT,
    stream: bool = False,
) -> ChatCompletionRequest:
    """Build a minimal text-only OpenAI ChatCompletionRequest."""
    return ChatCompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content=content)],
        stream=stream,
    )


def _make_gemini_request(
    content: str = SYNTHETIC_PROMPT,
) -> GeminiGenerateContentRequest:
    """Build a minimal text-only Gemini generateContent request."""
    return GeminiGenerateContentRequest(
        contents=[
            GeminiContent(
                role="user",
                parts=[GeminiPart(text=content)],
            )
        ]
    )


def _make_success_json(text: str = "Hello from fake handler") -> str:
    """Build an OpenAI-format success JSON string the fake handler yields."""
    return json.dumps({
        "choices": [{
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }]
    })


def _make_error_json(message: str = "fake error", status_code: int = 500) -> str:
    """Build an error JSON string the fake handler yields."""
    return json.dumps({
        "error": {
            "message": message,
            "type": "server_error",
            "code": "generation_failed",
            "status_code": status_code,
        }
    })


async def _read_json_body(response: JSONResponse) -> dict:
    """Decode the JSON body from a JSONResponse."""
    return json.loads(response.body.decode("utf-8"))


# ===========================================================================
# 1. OpenAI Non-Streaming Text Success
# ===========================================================================
class OpenAINonStreamingTextSuccessTests(unittest.IsolatedAsyncioTestCase):
    """Test create_chat_completion with stream=False and a successful fake handler."""

    async def test_openai_non_streaming_text_success(self):
        success_text = "Hello from fake handler"
        fake = FakeGenerationHandler(yield_value=_make_success_json(success_text))

        with patch.object(routes_module, "generation_handler", fake):
            response = await create_chat_completion(
                request=_make_openai_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        # Response type
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
        self.assertEqual(choice["message"]["content"], success_text)

        # Finish reason
        self.assertEqual(choice.get("finish_reason"), "stop")

        # Model behavior — known model resolves to itself
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0]["model"], KNOWN_MODEL)

        # Non-streaming mode
        self.assertFalse(fake.calls[0]["stream"])

        # Normalized prompt contains the synthetic input
        self.assertIn(SYNTHETIC_PROMPT, fake.calls[0]["prompt"])

        # No media-related data introduced
        self.assertIsNone(fake.calls[0]["images"])
        self.assertIsNone(fake.calls[0]["video_media_id"])


# ===========================================================================
# 2. OpenAI Handler Uninitialized
# ===========================================================================
class OpenAIHandlerUninitializedTests(unittest.IsolatedAsyncioTestCase):
    """Test create_chat_completion when generation_handler is None."""

    async def test_openai_handler_uninitialized(self):
        with patch.object(routes_module, "generation_handler", None):
            with self.assertRaises(HTTPException) as ctx:
                await create_chat_completion(
                    request=_make_openai_request(),
                    raw_request=_make_raw_request(),
                    api_key=FAKE_API_KEY,
                )

        exc = ctx.exception
        self.assertEqual(exc.status_code, 500)
        self.assertIn("not initialized", exc.detail)


# ===========================================================================
# 3. OpenAI Deterministic Handler Error
# ===========================================================================
class OpenAIHandlerErrorTests(unittest.IsolatedAsyncioTestCase):
    """Test create_chat_completion when the handler yields an error JSON."""

    async def test_openai_handler_error_conversion(self):
        error_msg = "upstream timeout"
        error_status = 502
        fake = FakeGenerationHandler(
            yield_value=_make_error_json(message=error_msg, status_code=error_status)
        )

        with patch.object(routes_module, "generation_handler", fake):
            response = await create_chat_completion(
                request=_make_openai_request(),
                raw_request=_make_raw_request(),
                api_key=FAKE_API_KEY,
            )

        # Response type
        self.assertIsInstance(response, JSONResponse)

        # Status code extracted from error payload
        self.assertEqual(response.status_code, error_status)

        # Error body preserved
        body = await _read_json_body(response)
        self.assertIn("error", body)
        self.assertEqual(body["error"]["message"], error_msg)
        self.assertEqual(body["error"]["status_code"], error_status)

        # Exactly one handler call
        self.assertEqual(len(fake.calls), 1)


# ===========================================================================
# 4. Gemini Non-Streaming Text Success
# ===========================================================================
class GeminiNonStreamingTextSuccessTests(unittest.IsolatedAsyncioTestCase):
    """Test generate_content with a successful fake handler."""

    async def test_gemini_non_streaming_text_success(self):
        success_text = "Gemini fake response text"
        fake = FakeGenerationHandler(yield_value=_make_success_json(success_text))

        with patch.object(routes_module, "generation_handler", fake):
            response = await generate_content(
                model=KNOWN_MODEL,
                request=_make_gemini_request(),
                raw_request=_make_raw_request(path="/v1beta/models/test:generateContent"),
                api_key=FAKE_API_KEY,
            )

        # Response type
        self.assertIsInstance(response, JSONResponse)

        # Status code — success is 200
        self.assertEqual(response.status_code, 200)

        # Gemini candidate/text shape
        body = await _read_json_body(response)
        self.assertIn("candidates", body)
        self.assertEqual(len(body["candidates"]), 1)

        candidate = body["candidates"][0]
        self.assertEqual(candidate["finishReason"], "STOP")
        self.assertEqual(candidate["index"], 0)

        content = candidate["content"]
        self.assertEqual(content["role"], "model")
        self.assertEqual(len(content["parts"]), 1)
        self.assertEqual(content["parts"][0]["text"], success_text)

        # modelVersion set to the resolved model
        self.assertEqual(body["modelVersion"], KNOWN_MODEL)

        # No OpenAI [DONE] sentinel in response body
        body_text = response.body.decode("utf-8")
        self.assertNotIn("[DONE]", body_text)

        # Exactly one handler call
        self.assertEqual(len(fake.calls), 1)

        # Model passed correctly
        self.assertEqual(fake.calls[0]["model"], KNOWN_MODEL)

        # Non-streaming mode
        self.assertFalse(fake.calls[0]["stream"])

        # Normalized prompt contains the synthetic input
        self.assertIn(SYNTHETIC_PROMPT, fake.calls[0]["prompt"])

        # No media-related data introduced
        self.assertIsNone(fake.calls[0]["images"])
        self.assertIsNone(fake.calls[0]["video_media_id"])


# ===========================================================================
# 5. Gemini Handler Uninitialized
# ===========================================================================
class GeminiHandlerUninitializedTests(unittest.IsolatedAsyncioTestCase):
    """Test generate_content when generation_handler is None."""

    async def test_gemini_handler_uninitialized(self):
        with patch.object(routes_module, "generation_handler", None):
            response = await generate_content(
                model=KNOWN_MODEL,
                request=_make_gemini_request(),
                raw_request=_make_raw_request(path="/v1beta/models/test:generateContent"),
                api_key=FAKE_API_KEY,
            )

        # Gemini route catches HTTPException and returns JSONResponse
        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(response.status_code, 500)

        body = await _read_json_body(response)
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], 500)
        self.assertEqual(body["error"]["status"], "INTERNAL")
        self.assertIn("not initialized", body["error"]["message"])


# ===========================================================================
# 6. Gemini Deterministic Handler Error
# ===========================================================================
class GeminiHandlerErrorTests(unittest.IsolatedAsyncioTestCase):
    """Test generate_content when the handler yields an error JSON."""

    async def test_gemini_handler_error_conversion(self):
        error_msg = "gemini upstream failure"
        error_status = 503
        fake = FakeGenerationHandler(
            yield_value=_make_error_json(message=error_msg, status_code=error_status)
        )

        with patch.object(routes_module, "generation_handler", fake):
            response = await generate_content(
                model=KNOWN_MODEL,
                request=_make_gemini_request(),
                raw_request=_make_raw_request(path="/v1beta/models/test:generateContent"),
                api_key=FAKE_API_KEY,
            )

        # Response type
        self.assertIsInstance(response, JSONResponse)

        # Status code mapped from handler error
        self.assertEqual(response.status_code, error_status)

        # Gemini error payload shape
        body = await _read_json_body(response)
        self.assertIn("error", body)
        self.assertEqual(body["error"]["code"], error_status)
        self.assertEqual(body["error"]["message"], error_msg)
        self.assertEqual(body["error"]["status"], "UNAVAILABLE")

        # Exactly one handler call
        self.assertEqual(len(fake.calls), 1)


if __name__ == "__main__":
    unittest.main()
