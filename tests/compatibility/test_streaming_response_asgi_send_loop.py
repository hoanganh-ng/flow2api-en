"""Direct ASGI StreamingResponse send-loop characterization tests.

These tests invoke the ``StreamingResponse`` objects returned by the
streaming routes directly with deterministic synthetic ASGI
scope/receive/send callables, characterizing ``http.response.start``,
``http.response.body``, header encoding, byte encoding, ``more_body``
flags, normal completion, and exception propagation.

No FastAPI app, TestClient, HTTPX, lifespan, network, database, browser,
captcha, proxy, token, session service, media retrieval, or real
credentials are used.

The synthetic ASGI harness uses ``asgi.spec_version`` ``"2.4"`` to
exercise the simple ``stream_response`` path in Starlette 0.48.0,
avoiding the anyio task-group and disconnect-listener path.

Direct route calls supply the already-resolved ``api_key`` dependency
parameter explicitly. Authentication behavior is not exercised.

Sprint 006K — Direct ASGI StreamingResponse Send-Loop Characterization.
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-3.0-pro-image-landscape"
SYNTHETIC_PROMPT = "Hello, tell me a short story."
FAKE_API_KEY = "test-key"  # Supplies the already-resolved dependency parameter


# ---------------------------------------------------------------------------
# Synthetic ASGI Harness
# ---------------------------------------------------------------------------
def _make_asgi_scope(
    path: str = "/v1/chat/completions",
    method: str = "POST",
) -> dict:
    """Build a minimal HTTP ASGI scope for direct response invocation.

    Sets ``asgi.spec_version`` to ``"2.4"`` so that Starlette 0.48.0
    ``StreamingResponse.__call__`` takes the simple ``stream_response``
    path without the anyio task-group and disconnect-listener.
    """
    return {
        "type": "http",
        "asgi": {"spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"host", b"test.local")],
    }


def _make_receive():
    """Build a deterministic receive callable.

    Returns ``http.disconnect`` immediately if called. With
    ``spec_version >= (2, 4)`` the receive callable is never invoked
    by ``StreamingResponse.__call__``, but it is provided for
    completeness and signature compatibility.
    """
    async def receive():
        return {"type": "http.disconnect"}
    return receive


def _make_send_recorder():
    """Build a send callable that records all ASGI messages.

    Returns ``(send, messages)`` where ``messages`` is a list populated
    with every message dict passed to ``send``.
    """
    messages: list[dict] = []

    async def send(message: dict):
        messages.append(message)

    return send, messages


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
    use proxy behavior, or retrieve media.
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

    Uses ``ensure_ascii=False`` so that non-ASCII characters are preserved
    as literal Unicode in the JSON string rather than being escaped.
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
    }, ensure_ascii=False)


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
    }, ensure_ascii=False)


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


def _get_start_message(messages: list[dict]) -> dict:
    """Extract the single http.response.start message."""
    starts = [m for m in messages if m["type"] == "http.response.start"]
    assert len(starts) == 1, f"Expected 1 response.start, got {len(starts)}"
    return starts[0]


def _get_body_messages(messages: list[dict]) -> list[dict]:
    """Extract all http.response.body messages in order."""
    return [m for m in messages if m["type"] == "http.response.body"]


def _headers_to_dict(raw_headers: list[tuple[bytes, bytes]]) -> dict[str, str]:
    """Decode raw ASGI header pairs to a lowercase-keyed dict."""
    return {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}


# ---------------------------------------------------------------------------
# Case 1: OpenAI Successful ASGI Send Loop
# ---------------------------------------------------------------------------
class TestOpenAISuccessfulASGISendLoop(unittest.IsolatedAsyncioTestCase):
    """OpenAI successful streaming via direct ASGI response invocation."""

    async def test_openai_successful_asgi_send_loop(self):
        """Verify exact ASGI message sequence for a successful OpenAI stream.

        Calls the route, then invokes the returned StreamingResponse directly
        with synthetic ASGI callables. Asserts the exact ASGI message order,
        exact content-body byte values with non-ASCII UTF-8 preservation,
        one body message per emitted stream event, ``data: [DONE]\\n\\n``
        as a separate body message, ``more_body`` flags, and the exact final
        empty body message.

        Non-ASCII value used: ``Xin chào — 世界``
        (Vietnamese greeting with CJK characters — proves UTF-8 byte encoding).
        """
        non_ascii_text = "Xin chào — 世界"
        chunks = [
            _make_text_delta_chunk(non_ascii_text),
            _make_text_delta_chunk(" world"),
            _make_final_chunk(),
        ]
        fake_handler = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(
                request, raw_request, api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope()
            receive = _make_receive()
            send, messages = _make_send_recorder()

            await response(scope, receive, send)

        # -- Message 0: exactly one http.response.start with status 200 ------
        self.assertEqual(messages[0]["type"], "http.response.start")
        start = messages[0]
        self.assertEqual(start["status"], 200)

        # -- Header assertions: bytes type, lowercase keys, exact values -----
        raw_headers = start["headers"]
        for key, value in raw_headers:
            self.assertIsInstance(key, bytes, f"Header key {key!r} is not bytes")
            self.assertIsInstance(value, bytes, f"Header value {value!r} is not bytes")

        header_keys = [k for k, _ in raw_headers]
        self.assertIn(b"content-type", header_keys)
        self.assertIn(b"cache-control", header_keys)
        self.assertIn(b"connection", header_keys)
        self.assertIn(b"x-accel-buffering", header_keys)

        header_dict = {k: v for k, v in raw_headers}
        self.assertEqual(
            header_dict[b"content-type"],
            b"text/event-stream; charset=utf-8",
        )
        self.assertEqual(header_dict[b"cache-control"], b"no-cache")
        self.assertEqual(header_dict[b"connection"], b"keep-alive")
        self.assertEqual(header_dict[b"x-accel-buffering"], b"no")

        # -- Build expected body byte sequences ------------------------------
        # _iterate_openai_stream parses each handler chunk and re-serializes
        # with json.dumps(..., ensure_ascii=False), then wraps in SSE framing.
        def _expected_openai_body(chunk_json: str) -> bytes:
            payload = json.loads(chunk_json)
            return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")

        expected_bodies = [
            _expected_openai_body(chunks[0]),
            _expected_openai_body(chunks[1]),
            _expected_openai_body(chunks[2]),
            b"data: [DONE]\n\n",
        ]

        # -- Verify non-ASCII bytes are present in first content body --------
        non_ascii_bytes = non_ascii_text.encode("utf-8")
        self.assertIn(
            non_ascii_bytes,
            expected_bodies[0],
            "Non-ASCII UTF-8 bytes must appear in the first content body",
        )

        # -- Body messages: exactly 3 chunk bodies + 1 [DONE] body + 1 final -
        bodies = _get_body_messages(messages)
        self.assertEqual(len(bodies), 5, "Expected 5 body messages total")

        # Content bodies are messages[1] through messages[4]
        content_bodies = bodies[:4]
        for i, body_msg in enumerate(content_bodies):
            self.assertEqual(
                body_msg["type"], "http.response.body",
                f"Message {i + 1} must be http.response.body",
            )
            self.assertIs(
                body_msg["more_body"], True,
                f"Content body {i} must have more_body=True",
            )
            self.assertIsInstance(body_msg["body"], bytes)
            self.assertEqual(
                body_msg["body"], expected_bodies[i],
                f"Content body {i} byte mismatch",
            )

        # Each content body is a separate ASGI message (proved by index check)
        self.assertEqual(messages[1], content_bodies[0])
        self.assertEqual(messages[2], content_bodies[1])
        self.assertEqual(messages[3], content_bodies[2])
        self.assertEqual(messages[4], content_bodies[3])

        # Final message: exactly {"type": "http.response.body",
        #                         "body": b"", "more_body": False}
        final = messages[-1]
        self.assertEqual(final["type"], "http.response.body")
        self.assertEqual(final["body"], b"")
        self.assertIs(final["more_body"], False)

        # -- Overall ASGI message count: 1 start + 4 content + 1 final = 6 ---
        self.assertEqual(len(messages), 6)

        # -- Handler called exactly once -------------------------------------
        self.assertEqual(len(fake_handler.calls), 1)


# ---------------------------------------------------------------------------
# Case 2: Gemini Successful ASGI Send Loop
# ---------------------------------------------------------------------------
class TestGeminiSuccessfulASGISendLoop(unittest.IsolatedAsyncioTestCase):
    """Gemini successful streaming via direct ASGI response invocation."""

    async def test_gemini_successful_asgi_send_loop(self):
        """Verify exact ASGI message sequence for a successful Gemini stream.

        Asserts one ``http.response.start``, exactly one body message per
        emitted Gemini event (3 handler chunks → 3 content bodies),
        no ``[DONE]`` body, exact content-body byte values with non-ASCII
        UTF-8 preservation, event-payload order verification, ``more_body``
        flags, and the exact final empty body message.

        Non-ASCII value used: ``Xin chào — 世界``
        (Vietnamese greeting with CJK characters — proves UTF-8 byte encoding).
        """
        non_ascii_text = "Xin chào — 世界"
        chunks = [
            _make_text_delta_chunk(non_ascii_text),
            _make_text_delta_chunk(" Gemini"),
            _make_final_chunk(),
        ]
        fake_handler = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            receive = _make_receive()
            send, messages = _make_send_recorder()

            await response(scope, receive, send)

        # -- Message 0: exactly one http.response.start with status 200 ------
        self.assertEqual(messages[0]["type"], "http.response.start")
        start = messages[0]
        self.assertEqual(start["status"], 200)

        # -- Header assertions: bytes type, lowercase keys, exact values -----
        raw_headers = start["headers"]
        for key, value in raw_headers:
            self.assertIsInstance(key, bytes, f"Header key {key!r} is not bytes")
            self.assertIsInstance(value, bytes, f"Header value {value!r} is not bytes")

        header_keys = [k for k, _ in raw_headers]
        self.assertIn(b"content-type", header_keys)
        self.assertIn(b"cache-control", header_keys)
        self.assertIn(b"connection", header_keys)
        self.assertIn(b"x-accel-buffering", header_keys)

        header_dict = {k: v for k, v in raw_headers}
        self.assertEqual(
            header_dict[b"content-type"],
            b"text/event-stream; charset=utf-8",
        )
        self.assertEqual(header_dict[b"cache-control"], b"no-cache")
        self.assertEqual(header_dict[b"connection"], b"keep-alive")
        self.assertEqual(header_dict[b"x-accel-buffering"], b"no")

        # -- Body messages: 3 Gemini events + 1 final empty body = 4 --------
        bodies = _get_body_messages(messages)
        self.assertEqual(len(bodies), 4, "Expected 4 body messages total")

        content_bodies = bodies[:3]

        # All content bodies have more_body=True and bytes body
        for i, body_msg in enumerate(content_bodies):
            self.assertEqual(
                body_msg["type"], "http.response.body",
                f"Message {i + 1} must be http.response.body",
            )
            self.assertIs(
                body_msg["more_body"], True,
                f"Content body {i} must have more_body=True",
            )
            self.assertIsInstance(body_msg["body"], bytes)

        # Each content body is a separate ASGI message (proved by index check)
        self.assertEqual(messages[1], content_bodies[0])
        self.assertEqual(messages[2], content_bodies[1])
        self.assertEqual(messages[3], content_bodies[2])

        # -- Verify non-ASCII UTF-8 bytes in first content body --------------
        non_ascii_bytes = non_ascii_text.encode("utf-8")
        self.assertIn(
            non_ascii_bytes,
            content_bodies[0]["body"],
            "Non-ASCII UTF-8 bytes must appear in the first Gemini content body",
        )

        # -- Parse and verify Gemini event payloads in order -----------------
        def _parse_gemini_body(body_bytes: bytes) -> dict:
            text = body_bytes.decode("utf-8")
            self.assertTrue(text.startswith("data: "), f"Missing SSE prefix: {text!r}")
            self.assertTrue(text.endswith("\n\n"), f"Missing SSE suffix: {text!r}")
            return json.loads(text[6:].strip())

        # Event 1: first text event (non-ASCII content, no finishReason)
        event_1 = _parse_gemini_body(content_bodies[0]["body"])
        self.assertIn("candidates", event_1)
        candidate_1 = event_1["candidates"][0]
        self.assertEqual(candidate_1["content"]["role"], "model")
        self.assertEqual(
            candidate_1["content"]["parts"][0]["text"], non_ascii_text,
        )
        self.assertNotIn("finishReason", candidate_1)
        self.assertEqual(event_1["modelVersion"], KNOWN_MODEL)

        # Event 2: second text event
        event_2 = _parse_gemini_body(content_bodies[1]["body"])
        candidate_2 = event_2["candidates"][0]
        self.assertEqual(candidate_2["content"]["role"], "model")
        self.assertEqual(candidate_2["content"]["parts"][0]["text"], " Gemini")
        self.assertNotIn("finishReason", candidate_2)
        self.assertEqual(event_2["modelVersion"], KNOWN_MODEL)

        # Event 3: finish-reason event (no content, finishReason=STOP)
        event_3 = _parse_gemini_body(content_bodies[2]["body"])
        candidate_3 = event_3["candidates"][0]
        self.assertNotIn("content", candidate_3)
        self.assertEqual(candidate_3["finishReason"], "STOP")
        self.assertEqual(event_3["modelVersion"], KNOWN_MODEL)

        # -- No OpenAI [DONE] sentinel in any body message -------------------
        for body_msg in bodies:
            self.assertNotIn(
                b"[DONE]", body_msg["body"],
                "Gemini stream must not contain [DONE] sentinel",
            )

        # -- Final message: exactly empty body with more_body=False ----------
        final = messages[-1]
        self.assertEqual(final["type"], "http.response.body")
        self.assertEqual(final["body"], b"")
        self.assertIs(final["more_body"], False)

        # -- Overall ASGI message count: 1 start + 3 content + 1 final = 5 --
        self.assertEqual(len(messages), 5)

        # -- Handler called exactly once -------------------------------------
        self.assertEqual(len(fake_handler.calls), 1)


# ---------------------------------------------------------------------------
# Case 3: OpenAI Exception Before First Chunk
# ---------------------------------------------------------------------------
class TestOpenAIExceptionBeforeFirstChunk(unittest.IsolatedAsyncioTestCase):
    """OpenAI exception during body iteration before any chunk is yielded."""

    async def test_openai_exception_before_first_chunk(self):
        """Verify ASGI behavior when the handler raises before yielding.

        The fake handler raises immediately. Response.start is sent (because
        Starlette sends it before iterating body_iterator). No content body
        is sent. The original exception propagates. No [DONE] is emitted.
        The final more_body=False message is absent.
        """
        fake_handler = FakeFailingHandler(
            yield_values=[],
            error=RuntimeError("synthetic immediate failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(
                request, raw_request, api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope()
            receive = _make_receive()
            send, messages = _make_send_recorder()

            with self.assertRaises(RuntimeError) as exc_info:
                await response(scope, receive, send)
            self.assertEqual(str(exc_info.exception), "synthetic immediate failure")

        # Response.start was sent (before body iteration)
        start = _get_start_message(messages)
        self.assertEqual(start["status"], 200)

        # No content body messages
        bodies = _get_body_messages(messages)
        content_bodies = [b for b in bodies if b.get("more_body") is True]
        self.assertEqual(len(content_bodies), 0, "No content body expected before exception")

        # No [DONE] in any message
        for body_msg in bodies:
            self.assertNotIn(b"[DONE]", body_msg["body"])

        # Final more_body=False is absent (exception interrupted the send loop)
        final_bodies = [b for b in bodies if b.get("more_body") is False]
        self.assertEqual(
            len(final_bodies), 0,
            "Final more_body=False message should be absent when exception interrupts",
        )


# ---------------------------------------------------------------------------
# Case 4: Gemini Exception Before First Event
# ---------------------------------------------------------------------------
class TestGeminiExceptionBeforeFirstEvent(unittest.IsolatedAsyncioTestCase):
    """Gemini exception during body iteration before any event is yielded."""

    async def test_gemini_exception_before_first_event(self):
        """Verify ASGI behavior when the Gemini handler raises before yielding.

        Corresponding to Case 3 for the Gemini route. Response.start is sent.
        No synthesized Gemini event is emitted. No [DONE] is present.
        The final more_body=False message is absent.
        """
        fake_handler = FakeFailingHandler(
            yield_values=[],
            error=RuntimeError("synthetic gemini immediate failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            receive = _make_receive()
            send, messages = _make_send_recorder()

            with self.assertRaises(RuntimeError) as exc_info:
                await response(scope, receive, send)
            self.assertEqual(str(exc_info.exception), "synthetic gemini immediate failure")

        # Response.start was sent
        start = _get_start_message(messages)
        self.assertEqual(start["status"], 200)

        # No content body messages
        bodies = _get_body_messages(messages)
        content_bodies = [b for b in bodies if b.get("more_body") is True]
        self.assertEqual(len(content_bodies), 0, "No content body expected before exception")

        # No [DONE] in any message
        for body_msg in bodies:
            self.assertNotIn(b"[DONE]", body_msg["body"])

        # Final more_body=False is absent
        final_bodies = [b for b in bodies if b.get("more_body") is False]
        self.assertEqual(
            len(final_bodies), 0,
            "Final more_body=False message should be absent when exception interrupts",
        )


# ---------------------------------------------------------------------------
# Case 5: OpenAI Partial Output Then Exception
# ---------------------------------------------------------------------------
class TestOpenAIPartialOutputThenExceptionASGI(unittest.IsolatedAsyncioTestCase):
    """OpenAI partial output then exception via direct ASGI invocation."""

    async def test_openai_partial_output_then_exception(self):
        """Verify ASGI messages when the handler yields one chunk then raises.

        Response.start is sent. One encoded content body with more_body=True
        is sent. The original exception propagates. No final [DONE] is
        emitted. No synthesized SSE error event is emitted. The final
        more_body=False message is absent.
        """
        first_chunk = _make_text_delta_chunk("First chunk")
        fake_handler = FakeFailingHandler(
            yield_values=[first_chunk],
            error=RuntimeError("synthetic mid-stream failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(
                request, raw_request, api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope()
            receive = _make_receive()
            send, messages = _make_send_recorder()

            with self.assertRaises(RuntimeError) as exc_info:
                await response(scope, receive, send)
            self.assertEqual(str(exc_info.exception), "synthetic mid-stream failure")

        # Response.start was sent
        start = _get_start_message(messages)
        self.assertEqual(start["status"], 200)

        # Body messages
        bodies = _get_body_messages(messages)

        # One content body with more_body=True
        content_bodies = [b for b in bodies if b.get("more_body") is True]
        self.assertEqual(len(content_bodies), 1, "Expected exactly one content body")

        # Content body is bytes containing the SSE frame
        body_bytes = content_bodies[0]["body"]
        self.assertIsInstance(body_bytes, bytes)
        body_text = body_bytes.decode("utf-8")
        self.assertTrue(body_text.startswith("data: "))
        self.assertIn("First chunk", body_text)

        # No [DONE] in any body message
        for body_msg in bodies:
            self.assertNotIn(b"[DONE]", body_msg["body"])

        # No synthesized SSE error event (only the one content body)
        self.assertEqual(len(content_bodies), 1)

        # Final more_body=False is absent
        final_bodies = [b for b in bodies if b.get("more_body") is False]
        self.assertEqual(
            len(final_bodies), 0,
            "Final more_body=False message should be absent when exception interrupts",
        )


# ---------------------------------------------------------------------------
# Case 6: Gemini Partial Output Then Exception
# ---------------------------------------------------------------------------
class TestGeminiPartialOutputThenExceptionASGI(unittest.IsolatedAsyncioTestCase):
    """Gemini partial output then exception via direct ASGI invocation."""

    async def test_gemini_partial_output_then_exception(self):
        """Verify ASGI messages when the Gemini handler yields one event then raises.

        One encoded Gemini body event with more_body=True is sent. The
        original exception propagates. No synthetic error event is emitted.
        No OpenAI [DONE] sentinel is present. The final more_body=False
        message is absent.
        """
        first_chunk = _make_text_delta_chunk("First Gemini chunk")
        fake_handler = FakeFailingHandler(
            yield_values=[first_chunk],
            error=RuntimeError("synthetic gemini mid-stream failure"),
        )

        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_gemini_request()
            raw_request = _make_raw_request(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            response = await stream_generate_content(
                model=KNOWN_MODEL,
                request=request,
                raw_request=raw_request,
                alt=None,
                api_key=FAKE_API_KEY,
            )

            scope = _make_asgi_scope(
                path="/v1beta/models/test-model:streamGenerateContent",
            )
            receive = _make_receive()
            send, messages = _make_send_recorder()

            with self.assertRaises(RuntimeError) as exc_info:
                await response(scope, receive, send)
            self.assertEqual(str(exc_info.exception), "synthetic gemini mid-stream failure")

        # Response.start was sent
        start = _get_start_message(messages)
        self.assertEqual(start["status"], 200)

        # Body messages
        bodies = _get_body_messages(messages)

        # One content body with more_body=True
        content_bodies = [b for b in bodies if b.get("more_body") is True]
        self.assertEqual(len(content_bodies), 1, "Expected exactly one content body")

        # Content body is a Gemini-shaped event
        body_bytes = content_bodies[0]["body"]
        self.assertIsInstance(body_bytes, bytes)
        body_text = body_bytes.decode("utf-8")
        self.assertTrue(body_text.startswith("data: "))
        payload_text = body_text[6:].strip()
        payload = json.loads(payload_text)
        self.assertIn("candidates", payload)
        self.assertEqual(payload["candidates"][0]["content"]["role"], "model")

        # No OpenAI [DONE] sentinel in any body message
        for body_msg in bodies:
            self.assertNotIn(b"[DONE]", body_msg["body"])

        # No synthetic error event (only the one content body)
        self.assertEqual(len(content_bodies), 1)

        # Final more_body=False is absent
        final_bodies = [b for b in bodies if b.get("more_body") is False]
        self.assertEqual(
            len(final_bodies), 0,
            "Final more_body=False message should be absent when exception interrupts",
        )


if __name__ == "__main__":
    unittest.main()
