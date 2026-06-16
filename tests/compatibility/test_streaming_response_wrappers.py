"""StreamingResponse wrapper and body-iterator characterization tests.

These tests exercise the streaming route wrappers (``create_chat_completion``
and ``stream_generate_content``) via direct Python function calls, verifying
``StreamingResponse`` construction, header/media-type values, deferred
handler execution, and direct ``body_iterator`` consumption behavior.

No FastAPI app, TestClient, ASGI transport, ``StreamingResponse.__call__``,
HTTP transport, lifespan, network, database, browser, captcha, proxy, token,
session service, media retrieval, or real credentials are used.

Direct route calls supply the already-resolved ``api_key`` dependency
parameter explicitly. Authentication behavior is not exercised.

Sprint 006J — StreamingResponse Wrapper and Body-Iterator Characterization.
"""

import json
import unittest
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import StreamingResponse

import src.api.routes as routes_module
from src.api.routes import (
    create_chat_completion,
    stream_generate_content,
)
from src.core.models import (
    ChatCompletionRequest,
    ChatMessage,
    GeminiContent,
    GeminiGenerateContentRequest,
    GeminiPart,
)
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-3.0-pro-image-landscape"
SYNTHETIC_PROMPT = "Hello, tell me a short story."
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
# Fake Generation Handlers
# ---------------------------------------------------------------------------
class FakeStreamingHandler:
    """Minimal fake handler yielding deterministic strings for streaming.

    Records calls for assertions. Does not make network calls, read
    credentials, touch a database, create browser/captcha/session services,
    use proxy behavior, retrieve media, or imitate the full production handler.
    """

    def __init__(self, yield_values: list[str] | None = None):
        self._yield_values = yield_values or []
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
        for value in self._yield_values:
            yield value


class FakeFailingHandler:
    """Fake handler that raises a deterministic exception during iteration.

    Supports raising before the first yield or after yielding N values.
    Records calls identically to FakeStreamingHandler.
    """

    def __init__(
        self,
        yield_values: list[str] | None = None,
        error: Exception | None = None,
    ):
        self._yield_values = yield_values or []
        self._error = error or RuntimeError("synthetic handler failure")
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
        """Async generator that yields configured values then raises."""
        self.calls.append({
            "model": model,
            "prompt": prompt,
            "images": images,
            "stream": stream,
            "base_url_override": base_url_override,
            "video_media_id": video_media_id,
        })
        for value in self._yield_values:
            yield value
        raise self._error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_text_delta_chunk(text: str = "Hello world") -> str:
    """Build a raw JSON string matching a typical OpenAI text-delta chunk.

    The handler yields raw JSON (without the ``data: `` prefix); the
    generator is responsible for SSE framing.
    """
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {"content": text},
            "finish_reason": None,
        }],
    })


def _make_final_chunk(text: str = "") -> str:
    """Build a raw JSON string with finish_reason=stop."""
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {"content": text},
            "finish_reason": "stop",
        }],
    })


def _make_openai_request(
    model: str = KNOWN_MODEL,
    prompt: str = SYNTHETIC_PROMPT,
    stream: bool = True,
) -> ChatCompletionRequest:
    """Build a minimal ChatCompletionRequest for streaming tests."""
    return ChatCompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content=prompt)],
        stream=stream,
    )


def _make_gemini_request(
    prompt: str = SYNTHETIC_PROMPT,
) -> GeminiGenerateContentRequest:
    """Build a minimal GeminiGenerateContentRequest for streaming tests."""
    return GeminiGenerateContentRequest(
        contents=[
            GeminiContent(
                role="user",
                parts=[GeminiPart(text=prompt)],
            )
        ]
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------
class TestOpenAIStreamingResponseWrapper(unittest.IsolatedAsyncioTestCase):
    """OpenAI streaming response construction and deferred execution tests."""

    async def test_openai_response_construction_and_deferred_execution(self):
        """Verify StreamingResponse construction without immediate handler invocation."""
        fake_handler = FakeStreamingHandler(yield_values=[_make_text_delta_chunk()])

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(request, raw_request, api_key=FAKE_API_KEY)

            # Verify response type
            self.assertIsInstance(response, StreamingResponse)

            # Verify status code
            self.assertEqual(response.status_code, 200)

            # Verify media type
            self.assertEqual(response.media_type, "text/event-stream")

            # Verify explicit headers
            headers_dict = dict(response.headers)
            self.assertEqual(headers_dict.get("cache-control"), "no-cache")
            self.assertEqual(headers_dict.get("connection"), "keep-alive")
            self.assertEqual(headers_dict.get("x-accel-buffering"), "no")

            # Verify content-type includes charset
            content_type = headers_dict.get("content-type", "")
            self.assertIn("text/event-stream", content_type)
            self.assertIn("charset=utf-8", content_type)

            # Verify body_iterator exists
            self.assertIsNotNone(response.body_iterator)

            # Verify handler has NOT been called yet (deferred execution)
            self.assertEqual(len(fake_handler.calls), 0)

    async def test_openai_successful_body_iteration(self):
        """Verify OpenAI SSE sequence and [DONE] termination during iteration."""
        chunks = [
            _make_text_delta_chunk("Hello"),
            _make_text_delta_chunk(" world"),
            _make_final_chunk(),
        ]
        fake_handler = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(request, raw_request, api_key=FAKE_API_KEY)

            # Consume body_iterator
            collected = []
            async for chunk in response.body_iterator:
                collected.append(chunk)

            # Verify SSE framing: each chunk starts with "data: "
            for chunk in collected[:-1]:  # Exclude [DONE]
                self.assertTrue(chunk.startswith("data: "), f"Chunk missing SSE prefix: {chunk!r}")

            # Verify final chunk is exactly "data: [DONE]\n\n"
            self.assertEqual(collected[-1], "data: [DONE]\n\n")

            # Verify [DONE] appears exactly once and is last
            done_count = sum(1 for c in collected if c == "data: [DONE]\n\n")
            self.assertEqual(done_count, 1)

            # Verify handler was called exactly once
            self.assertEqual(len(fake_handler.calls), 1)

            # Verify stable argument forwarding
            call = fake_handler.calls[0]
            self.assertEqual(call["model"], KNOWN_MODEL)
            self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
            self.assertTrue(call["stream"])
            self.assertIsNone(call["images"])
            self.assertIsNone(call["video_media_id"])
            # base_url_override should be derived from raw_request
            self.assertIsNotNone(call["base_url_override"])


class TestOpenAIHandlerUnavailable(unittest.IsolatedAsyncioTestCase):
    """OpenAI handler-unavailable behavior tests."""

    async def test_openai_handler_unavailable(self):
        """Verify failure timing when generation_handler is None.

        The route call succeeds and returns a StreamingResponse because
        _ensure_generation_handler() is called inside the generator
        (_iterate_openai_stream), which is only executed during body
        iteration. The HTTPException is raised during first iteration,
        not during the route call.
        """
        with patch.object(routes_module, "generation_handler", None):
            request = _make_openai_request()
            raw_request = _make_raw_request()

            # Route call succeeds - returns StreamingResponse
            response = await create_chat_completion(request, raw_request, api_key=FAKE_API_KEY)
            self.assertIsInstance(response, StreamingResponse)

            # First body iteration raises HTTPException
            with self.assertRaises(HTTPException) as exc_info:
                async for _ in response.body_iterator:
                    pass

            # Verify exception details
            self.assertEqual(exc_info.exception.status_code, 500)
            self.assertEqual(exc_info.exception.detail, "Generation handler not initialized")


class TestOpenAIPartialOutputThenException(unittest.IsolatedAsyncioTestCase):
    """OpenAI partial-output-then-exception behavior tests."""

    async def test_openai_partial_output_then_exception(self):
        """Verify exception propagation after partial output."""
        first_chunk = _make_text_delta_chunk("First chunk")
        fake_handler = FakeFailingHandler(
            yield_values=[first_chunk],
            error=RuntimeError("synthetic mid-stream failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(request, raw_request, api_key=FAKE_API_KEY)

            # Response should be constructed
            self.assertIsInstance(response, StreamingResponse)

            # Consume first chunk
            iterator = response.body_iterator.__aiter__()
            first = await iterator.__anext__()
            self.assertTrue(first.startswith("data: "))
            self.assertIn("First chunk", first)

            # Next iteration should raise the original exception
            with self.assertRaises(RuntimeError) as exc_info:
                await iterator.__anext__()
            self.assertEqual(str(exc_info.exception), "synthetic mid-stream failure")

            # Verify no [DONE] was emitted
            # (we only got one chunk before the exception)


class TestGeminiStreamingResponseWrapper(unittest.IsolatedAsyncioTestCase):
    """Gemini streaming response construction and deferred execution tests."""

    async def test_gemini_response_construction_and_deferred_execution(self):
        """Verify StreamingResponse construction without immediate handler invocation."""
        fake_handler = FakeStreamingHandler(yield_values=[_make_text_delta_chunk()])

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(path="/v1beta/models/test-model:streamGenerateContent")
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            # Verify response type
            self.assertIsInstance(response, StreamingResponse)

            # Verify status code
            self.assertEqual(response.status_code, 200)

            # Verify media type
            self.assertEqual(response.media_type, "text/event-stream")

            # Verify explicit headers
            headers_dict = dict(response.headers)
            self.assertEqual(headers_dict.get("cache-control"), "no-cache")
            self.assertEqual(headers_dict.get("connection"), "keep-alive")
            self.assertEqual(headers_dict.get("x-accel-buffering"), "no")

            # Verify content-type includes charset
            content_type = headers_dict.get("content-type", "")
            self.assertIn("text/event-stream", content_type)
            self.assertIn("charset=utf-8", content_type)

            # Verify body_iterator exists
            self.assertIsNotNone(response.body_iterator)

            # Verify handler has NOT been called yet (deferred execution)
            self.assertEqual(len(fake_handler.calls), 0)

    async def test_gemini_successful_body_iteration(self):
        """Verify Gemini event sequence and no [DONE] termination during iteration."""
        chunks = [
            _make_text_delta_chunk("Hello"),
            _make_text_delta_chunk(" Gemini"),
            _make_final_chunk(),
        ]
        fake_handler = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(path="/v1beta/models/test-model:streamGenerateContent")
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            # Consume body_iterator
            collected = []
            async for chunk in response.body_iterator:
                collected.append(chunk)

            # Verify SSE framing: each chunk starts with "data: "
            for chunk in collected:
                self.assertTrue(chunk.startswith("data: "), f"Chunk missing SSE prefix: {chunk!r}")

            # Verify no OpenAI [DONE] sentinel is emitted
            for chunk in collected:
                self.assertNotEqual(chunk, "data: [DONE]\n\n")
                self.assertNotIn("[DONE]", chunk)

            # Verify handler was called exactly once
            self.assertEqual(len(fake_handler.calls), 1)

            # Verify stable argument forwarding
            call = fake_handler.calls[0]
            self.assertEqual(call["model"], KNOWN_MODEL)
            self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
            self.assertTrue(call["stream"])
            self.assertIsNone(call["images"])
            self.assertIsNone(call["video_media_id"])
            # base_url_override should be derived from raw_request
            self.assertIsNotNone(call["base_url_override"])


class TestGeminiHandlerUnavailable(unittest.IsolatedAsyncioTestCase):
    """Gemini handler-unavailable behavior tests."""

    async def test_gemini_handler_unavailable(self):
        """Verify behavior when generation_handler is None for Gemini route.

        The route call succeeds and returns a StreamingResponse because
        _ensure_generation_handler() is called inside the generator
        (_iterate_gemini_stream), which is only executed during body
        iteration. The HTTPException is raised during first iteration,
        not during the route call. The route's try/except does not catch
        exceptions from generator iteration.
        """
        with patch.object(routes_module, "generation_handler", None):
            request = _make_gemini_request()
            raw_request = _make_raw_request(path="/v1beta/models/test-model:streamGenerateContent")

            # Route call succeeds - returns StreamingResponse
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )
            self.assertIsInstance(response, StreamingResponse)

            # First body iteration raises HTTPException
            with self.assertRaises(HTTPException) as exc_info:
                async for _ in response.body_iterator:
                    pass

            # Verify exception details
            self.assertEqual(exc_info.exception.status_code, 500)
            self.assertEqual(exc_info.exception.detail, "Generation handler not initialized")


class TestGeminiPartialOutputThenException(unittest.IsolatedAsyncioTestCase):
    """Gemini partial-output-then-exception behavior tests."""

    async def test_gemini_partial_output_then_exception(self):
        """Verify exception propagation after partial output for Gemini."""
        first_chunk = _make_text_delta_chunk("First Gemini chunk")
        fake_handler = FakeFailingHandler(
            yield_values=[first_chunk],
            error=RuntimeError("synthetic gemini mid-stream failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(path="/v1beta/models/test-model:streamGenerateContent")
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            # Response should be constructed
            self.assertIsInstance(response, StreamingResponse)

            # Consume first chunk
            iterator = response.body_iterator.__aiter__()
            first = await iterator.__anext__()
            self.assertTrue(first.startswith("data: "))

            # Verify it's a Gemini-shaped event (contains candidates structure)
            payload_text = first[6:].strip()  # Remove "data: " prefix
            payload = json.loads(payload_text)
            self.assertIn("candidates", payload)
            self.assertEqual(payload["candidates"][0]["content"]["role"], "model")

            # Next iteration should raise the original exception
            with self.assertRaises(RuntimeError) as exc_info:
                await iterator.__anext__()
            self.assertEqual(str(exc_info.exception), "synthetic gemini mid-stream failure")

            # Verify no synthetic error event was emitted before the exception
            # (we only got one chunk before the exception)


if __name__ == "__main__":
    unittest.main()
