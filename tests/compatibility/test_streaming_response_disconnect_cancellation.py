"""Receive-side streaming disconnect and cancellation characterization test.

This test characterizes Starlette 0.48.0's pre-2.4 ``StreamingResponse``
disconnect path by directly invoking the response returned by the OpenAI
streaming route with a coordinated receive callable that returns
``http.disconnect`` after the first content body has been sent and the
gated fake handler is blocked awaiting its next value.

The test proves:

- Exactly one content body was sent before disconnect.
- No ``[DONE]`` sentinel or ``more_body=False`` message was emitted.
- The fake handler observed ``asyncio.CancelledError``.
- The handler's test-only ``finally`` block ran.
- The route body iterator terminated (post-call ``__anext__()`` raises
  ``StopAsyncIteration``).
- ``response.__call__`` returned normally.

This does NOT prove real TCP disconnection, deployed-server behavior, or
production resource cleanup. Starlette 0.48.0 does NOT explicitly call
``aclose()`` on ``body_iterator``; no separate explicit or implicit
``aclose()`` invocation is claimed.

No FastAPI app, TestClient, HTTPX, lifespan, network, database, browser,
captcha, proxy, token, session service, media retrieval, or real
credentials are used.

Direct route calls supply the already-resolved ``api_key`` dependency
parameter explicitly. Authentication behavior is not exercised.

Sprint 006O — Receive-Side Streaming Disconnect Characterization.
"""

import asyncio
import json
import unittest
from unittest.mock import patch

from starlette.requests import Request
from starlette.responses import StreamingResponse

import src.api.routes as routes_module
from src.api.routes import create_chat_completion
from src.core.models import ChatCompletionRequest, ChatMessage


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-3.0-pro-image-landscape"
SYNTHETIC_PROMPT = "Hello, tell me a short story."
FAKE_API_KEY = "test-key"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_text_delta_chunk(text: str = "Hello world") -> str:
    """Build a raw JSON string matching a typical OpenAI text-delta chunk."""
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


def _make_openai_request(
    model: str = KNOWN_MODEL,
    prompt: str = SYNTHETIC_PROMPT,
    stream: bool = True,
) -> ChatCompletionRequest:
    """Build a minimal ChatCompletionRequest for streaming."""
    return ChatCompletionRequest(
        model=model,
        messages=[ChatMessage(role="user", content=prompt)],
        stream=stream,
    )


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


def _make_asgi_scope_disconnect(
    path: str = "/v1/chat/completions",
    method: str = "POST",
) -> dict:
    """Build a minimal HTTP ASGI scope with spec_version ``"2.0"``.

    Sets ``asgi.spec_version`` to ``"2.0"`` so that Starlette 0.48.0
    ``StreamingResponse.__call__`` takes the anyio task-group path with
    ``listen_for_disconnect`` and ``stream_response`` racing.
    """
    return {
        "type": "http",
        "asgi": {"spec_version": "2.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(b"host", b"test.local")],
    }


# ---------------------------------------------------------------------------
# Gated Fake Handler
# ---------------------------------------------------------------------------
class GatedFakeStreamingHandler:
    """Fake handler with explicit synchronization gates for disconnect tests.

    Yields one deterministic chunk, then blocks on an unreleased event
    so that cancellation arrives at a known await checkpoint. Records
    all invocation arguments, the cancellation exception type, and
    whether the test-only ``finally`` block ran.
    """

    def __init__(
        self,
        first_chunk: str,
        handler_waiting_for_next: asyncio.Event,
        handler_continue: asyncio.Event,
    ):
        self._first_chunk = first_chunk
        self._handler_waiting_for_next = handler_waiting_for_next
        self._handler_continue = handler_continue
        self.calls: list[dict] = []
        self.cancellation_type: type | None = None
        self.finally_ran: bool = False

    async def handle_generation(
        self,
        model: str,
        prompt: str,
        images=None,
        stream: bool = False,
        base_url_override=None,
        video_media_id=None,
    ):
        """Async generator with synchronization gates."""
        self.calls.append({
            "model": model,
            "prompt": prompt,
            "images": images,
            "stream": stream,
            "base_url_override": base_url_override,
            "video_media_id": video_media_id,
        })
        try:
            yield self._first_chunk

            # Signal that we are waiting for the next value
            self._handler_waiting_for_next.set()

            # Block until released (never released — cancellation arrives here)
            await self._handler_continue.wait()

            # Should not reach here in a disconnect test
            yield "data: should-not-be-reached\n\n"
        except asyncio.CancelledError:
            self.cancellation_type = asyncio.CancelledError
            raise
        except BaseException as exc:
            self.cancellation_type = type(exc)
            raise
        finally:
            self.finally_ran = True


# ---------------------------------------------------------------------------
# Test: OpenAI Receive-Side Disconnect After First Body
# ---------------------------------------------------------------------------
class TestOpenAIReceiveSideDisconnectAfterFirstBody(
    unittest.IsolatedAsyncioTestCase,
):
    """OpenAI receive-side disconnect after first content body."""

    async def test_openai_receive_side_disconnect_after_first_body(self):
        """Characterize receive-side disconnect and cancellation behavior.

        Patches ``generation_handler`` with a gated fake handler, calls
        ``create_chat_completion`` directly, confirms the route returns a
        ``StreamingResponse``, then invokes the response directly with:

        - ASGI scope with ``spec_version`` ``"2.0"``
        - A coordinated ``receive`` callable
        - A recording ``send`` callable

        The fake handler yields one deterministic OpenAI JSON chunk
        containing non-ASCII content (``Xin chào — 世界``), then blocks
        on an unreleased event. The ``receive`` callable waits for both
        the first body to be recorded and the handler to be blocked
        before returning ``http.disconnect``.

        Asserts:

        - ``response.__call__`` returns normally.
        - Exactly two ASGI messages recorded.
        - First message: ``http.response.start`` with status 200.
        - Second message: ``http.response.body`` with exact SSE bytes
          and ``more_body=True``.
        - No additional body emitted.
        - No ``data: [DONE]\\n\\n`` exists.
        - No message with ``more_body=False`` exists.
        - Fake handler observed ``asyncio.CancelledError``.
        - Handler test-only ``finally`` block ran.
        - Post-call ``body_iterator.__anext__()`` raises
          ``StopAsyncIteration``.
        - Fake handler invoked exactly once with expected arguments.
        """
        # -- Synchronization events ----------------------------------------
        first_body_sent = asyncio.Event()
        handler_waiting_for_next = asyncio.Event()
        handler_continue = asyncio.Event()  # Never released

        # -- Build the first chunk with non-ASCII content ------------------
        non_ascii_text = "Xin chào — 世界"
        first_chunk_json = _make_text_delta_chunk(non_ascii_text)

        # -- Create gated fake handler -------------------------------------
        fake_handler = GatedFakeStreamingHandler(
            first_chunk=first_chunk_json,
            handler_waiting_for_next=handler_waiting_for_next,
            handler_continue=handler_continue,
        )

        # -- Patch and call the route --------------------------------------
        with patch.object(routes_module, "generation_handler", fake_handler):
            request = _make_openai_request()
            raw_request = _make_raw_request()
            response = await create_chat_completion(
                request, raw_request, api_key=FAKE_API_KEY,
            )

            # Confirm response type
            self.assertIsInstance(response, StreamingResponse)

            # -- Build ASGI scope, receive, and send ----------------------
            scope = _make_asgi_scope_disconnect()

            async def receive():
                """Wait for first body sent and handler blocked, then disconnect."""
                await first_body_sent.wait()
                await handler_waiting_for_next.wait()
                return {"type": "http.disconnect"}

            messages: list[dict] = []

            async def send(message: dict):
                """Record ASGI messages and signal after first content body."""
                messages.append(message)
                if (
                    message["type"] == "http.response.body"
                    and message.get("more_body") is True
                ):
                    first_body_sent.set()

            # -- Invoke the response directly ------------------------------
            await response(scope, receive, send)

        # -- Assertions: response.__call__ returned normally (reached here) -

        # -- ASGI message count: exactly 2 ---------------------------------
        # Message 0: http.response.start
        # Message 1: http.response.body (first content body, more_body=True)
        self.assertEqual(
            len(messages), 2,
            f"Expected exactly 2 ASGI messages, got {len(messages)}",
        )

        # -- First message: http.response.start with status 200 ------------
        self.assertEqual(messages[0]["type"], "http.response.start")
        self.assertEqual(messages[0]["status"], 200)

        # -- Second message: http.response.body with exact SSE bytes -------
        self.assertEqual(messages[1]["type"], "http.response.body")
        self.assertIs(messages[1]["more_body"], True)

        # Build expected SSE bytes independently
        expected_payload = json.loads(first_chunk_json)
        expected_sse_bytes = (
            f"data: {json.dumps(expected_payload, ensure_ascii=False)}\n\n"
        ).encode("utf-8")

        self.assertEqual(
            messages[1]["body"], expected_sse_bytes,
            "Content body byte mismatch",
        )

        # Verify non-ASCII UTF-8 bytes are present
        non_ascii_bytes = non_ascii_text.encode("utf-8")
        self.assertIn(
            non_ascii_bytes, messages[1]["body"],
            "Non-ASCII UTF-8 bytes must appear in the content body",
        )

        # -- No additional body emitted ------------------------------------
        body_messages = [
            m for m in messages if m["type"] == "http.response.body"
        ]
        self.assertEqual(
            len(body_messages), 1,
            "Expected exactly one body message",
        )

        # -- No [DONE] sentinel exists -------------------------------------
        all_body_bytes = b"".join(
            m.get("body", b"") for m in body_messages
        )
        self.assertNotIn(
            b"data: [DONE]\n\n", all_body_bytes,
            "No [DONE] sentinel should be present",
        )

        # -- No message with more_body=False exists ------------------------
        final_messages = [
            m for m in messages if m.get("more_body") is False
        ]
        self.assertEqual(
            len(final_messages), 0,
            "No more_body=False message should exist",
        )

        # -- Fake handler observed CancelledError --------------------------
        self.assertIs(
            fake_handler.cancellation_type, asyncio.CancelledError,
            "Handler should have observed asyncio.CancelledError",
        )

        # -- Handler test-only finally block ran ---------------------------
        self.assertTrue(
            fake_handler.finally_ran,
            "Handler finally block should have run",
        )

        # -- Post-call body_iterator is terminated -------------------------
        with self.assertRaises(StopAsyncIteration):
            await response.body_iterator.__anext__()

        # -- Handler invoked exactly once with expected arguments ----------
        self.assertEqual(len(fake_handler.calls), 1)
        call = fake_handler.calls[0]
        self.assertEqual(call["model"], KNOWN_MODEL)
        self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
        self.assertIs(call["stream"], True)
        self.assertIsNone(call["images"])
        # base_url_override is derived from _get_request_base_url;
        # the synthetic request with host header "test.local" yields
        # exactly "http://test.local"
        self.assertEqual(
            call["base_url_override"],
            "http://test.local",
        )
        self.assertIsNone(call["video_media_id"])


if __name__ == "__main__":
    unittest.main()
