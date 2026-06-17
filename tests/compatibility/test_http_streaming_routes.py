"""HTTP-level streaming route characterization tests.

These tests exercise the streaming generation routes through the full HTTP
request path using a test-local FastAPI application with ``routes.router``,
a dependency override for ``verify_api_key_flexible``, a patched fake
generation handler, and Starlette ``TestClient``.

The ``TestClient`` fully buffers the response body before delivery. These
tests characterize the complete HTTP request/response contract — status
codes, headers, and the fully reassembled SSE body — not incremental
delivery or original ASGI body-message boundaries.

``src.main.app`` is never imported. No production lifespan, database,
token manager, proxy manager, load balancer, browser captcha, session
service, media retrieval, network calls, or real credentials are used.

Sprint 006M — HTTP-Level Streaming Route Characterization.
"""

import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from starlette.testclient import TestClient

import src.api.routes as routes_module
from src.api.routes import router
from src.core.auth import verify_api_key_flexible


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-2.0-flash-exp"
SYNTHETIC_PROMPT = "Xin chào — 世界"
FAKE_API_KEY = "test-api-key"


# ---------------------------------------------------------------------------
# Test-Local Application Builder
# ---------------------------------------------------------------------------
def _make_test_app() -> FastAPI:
    """Build a test-local FastAPI app with routes.router and auth override.

    No lifespan, production services, or src.main import is involved.
    """
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_api_key_flexible] = lambda: FAKE_API_KEY
    return app


# ---------------------------------------------------------------------------
# Fake Generation Handler
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


# ---------------------------------------------------------------------------
# Helper: Build OpenAI-format raw JSON chunk
# ---------------------------------------------------------------------------
def _make_openai_text_delta_chunk(text: str) -> str:
    """Build a raw JSON string matching a typical OpenAI text-delta chunk.

    The handler yields raw JSON (without the ``data: `` prefix); the
    OpenAI generator is responsible for SSE framing.
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


def _make_openai_finish_chunk(reason: str = "stop") -> str:
    """Build a raw JSON chunk with a finish_reason and no text delta."""
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": reason,
        }],
    })


# ===========================================================================
# Test 1: OpenAI HTTP-Level Streaming Response
# ===========================================================================
class TestOpenAIHTTPStreamingResponse(unittest.TestCase):
    """OpenAI successful HTTP-level streaming response characterization.

    Exercises POST /v1/chat/completions with stream=true through the full
    HTTP path: FastAPI routing, Pydantic validation, dependency override,
    patched handler, StreamingResponse construction, and TestClient
    buffering. The fully buffered SSE body is asserted for content, order,
    headers, and [DONE] termination.
    """

    def setUp(self):
        self.app = _make_test_app()
        self.client = TestClient(self.app)
        # Build deterministic chunks with non-ASCII content
        self.chunk1 = _make_openai_text_delta_chunk("Xin chào")
        self.chunk2 = _make_openai_text_delta_chunk(" — 世界")
        self.chunk_finish = _make_openai_finish_chunk("stop")
        self.fake_handler = FakeStreamingHandler(
            yield_values=[self.chunk1, self.chunk2, self.chunk_finish]
        )
        self.patcher = patch.object(
            routes_module, "generation_handler", self.fake_handler
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        # Clean up dependency overrides to prevent state leakage
        self.app.dependency_overrides.clear()

    def test_openai_streaming_http_contract(self):
        """Assert the complete OpenAI streaming HTTP response contract."""
        response = self.client.post(
            "/v1/chat/completions",
            json={
                "model": KNOWN_MODEL,
                "messages": [{"role": "user", "content": SYNTHETIC_PROMPT}],
                "stream": True,
            },
        )

        # --- Status and headers ---
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("charset=utf-8", response.headers["content-type"].lower())
        self.assertEqual(response.headers["cache-control"], "no-cache")
        self.assertEqual(response.headers["connection"], "keep-alive")
        self.assertEqual(response.headers["x-accel-buffering"], "no")

        # --- Fully buffered SSE body ---
        body = response.text

        # Build expected events independently
        expected_payload1 = json.loads(self.chunk1)
        expected_payload2 = json.loads(self.chunk2)
        expected_payload_finish = json.loads(self.chunk_finish)

        expected_event1 = f"data: {json.dumps(expected_payload1, ensure_ascii=False)}\n\n"
        expected_event2 = f"data: {json.dumps(expected_payload2, ensure_ascii=False)}\n\n"
        expected_event_finish = f"data: {json.dumps(expected_payload_finish, ensure_ascii=False)}\n\n"
        expected_done = "data: [DONE]\n\n"

        # Full expected body: all events concatenated
        expected_body = expected_event1 + expected_event2 + expected_event_finish + expected_done

        self.assertEqual(body, expected_body)

        # Verify each event is separated by blank line (double newline)
        events = body.split("\n\n")
        # Last element after split is empty string (trailing \n\n)
        self.assertEqual(events[-1], "")
        non_empty_events = events[:-1]
        self.assertEqual(len(non_empty_events), 4)

        # Verify content of each event
        self.assertTrue(non_empty_events[0].startswith("data: "))
        self.assertTrue(non_empty_events[1].startswith("data: "))
        self.assertTrue(non_empty_events[2].startswith("data: "))
        self.assertEqual(non_empty_events[3], "data: [DONE]")

        # Parse and verify JSON payloads
        payload1 = json.loads(non_empty_events[0][len("data: "):])
        self.assertEqual(payload1["choices"][0]["delta"]["content"], "Xin chào")

        payload2 = json.loads(non_empty_events[1][len("data: "):])
        self.assertEqual(payload2["choices"][0]["delta"]["content"], " — 世界")

        payload_finish = json.loads(non_empty_events[2][len("data: "):])
        self.assertEqual(payload_finish["choices"][0]["finish_reason"], "stop")

        # Final event is exactly data: [DONE]
        self.assertEqual(non_empty_events[-1], "data: [DONE]")

        # Nothing follows [DONE] — body ends with "data: [DONE]\n\n"
        self.assertTrue(body.endswith("data: [DONE]\n\n"))

        # --- Handler call assertions ---
        self.assertEqual(len(self.fake_handler.calls), 1)
        call = self.fake_handler.calls[0]
        self.assertEqual(call["model"], KNOWN_MODEL)
        self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
        self.assertTrue(call["stream"])
        self.assertIsNone(call["images"])
        self.assertIsNone(call["video_media_id"])


# ===========================================================================
# Test 2: Gemini HTTP-Level Streaming Response
# ===========================================================================
class TestGeminiHTTPStreamingResponse(unittest.TestCase):
    """Gemini successful HTTP-level streaming response characterization.

    Exercises POST /v1beta/models/{model}:streamGenerateContent through the
    full HTTP path: FastAPI routing, Pydantic validation, dependency override,
    patched handler, StreamingResponse construction, and TestClient buffering.
    The fully buffered SSE body is asserted for Gemini event format,
    modelVersion, finishReason, and no-[DONE] termination.
    """

    def setUp(self):
        self.app = _make_test_app()
        self.client = TestClient(self.app)
        # Build deterministic chunks — OpenAI format that gets converted to Gemini
        # Include non-ASCII content
        self.chunk1 = _make_openai_text_delta_chunk("Xin chào")
        self.chunk2 = _make_openai_text_delta_chunk(" — 世界")
        self.chunk_finish = _make_openai_finish_chunk("stop")
        self.fake_handler = FakeStreamingHandler(
            yield_values=[self.chunk1, self.chunk2, self.chunk_finish]
        )
        self.patcher = patch.object(
            routes_module, "generation_handler", self.fake_handler
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        # Clean up dependency overrides to prevent state leakage
        self.app.dependency_overrides.clear()

    def test_gemini_streaming_http_contract(self):
        """Assert the complete Gemini streaming HTTP response contract."""
        response = self.client.post(
            f"/v1beta/models/{KNOWN_MODEL}:streamGenerateContent",
            json={
                "contents": [{
                    "role": "user",
                    "parts": [{"text": SYNTHETIC_PROMPT}],
                }],
            },
        )

        # --- Status and headers ---
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("charset=utf-8", response.headers["content-type"].lower())
        self.assertEqual(response.headers["cache-control"], "no-cache")
        self.assertEqual(response.headers["connection"], "keep-alive")
        self.assertEqual(response.headers["x-accel-buffering"], "no")

        # --- Fully buffered SSE body ---
        body = response.text

        # Verify each event is separated by blank line
        events = body.split("\n\n")
        # Last element after split is empty string (trailing \n\n)
        self.assertEqual(events[-1], "")
        non_empty_events = events[:-1]

        # Expect 3 events: text1, text2, finish (no [DONE] for Gemini)
        self.assertEqual(len(non_empty_events), 3)

        # All events should be data: prefixed
        for event in non_empty_events:
            self.assertTrue(event.startswith("data: "), f"Event missing data: prefix: {event!r}")

        # Parse and verify Gemini event structure
        gemini_events = [json.loads(e[len("data: "):]) for e in non_empty_events]

        # Event 1: text content "Xin chào"
        event1 = gemini_events[0]
        self.assertIn("candidates", event1)
        self.assertIn("modelVersion", event1)
        self.assertEqual(event1["modelVersion"], KNOWN_MODEL)
        candidate1 = event1["candidates"][0]
        self.assertEqual(candidate1["index"], 0)
        self.assertIn("content", candidate1)
        self.assertEqual(candidate1["content"]["role"], "model")
        self.assertEqual(candidate1["content"]["parts"][0]["text"], "Xin chào")
        self.assertNotIn("finishReason", candidate1)

        # Event 2: text content " — 世界" (non-ASCII)
        event2 = gemini_events[1]
        self.assertEqual(event2["modelVersion"], KNOWN_MODEL)
        candidate2 = event2["candidates"][0]
        self.assertEqual(candidate2["content"]["parts"][0]["text"], " — 世界")
        self.assertNotIn("finishReason", candidate2)

        # Event 3: finish reason (STOP) — no content
        event3 = gemini_events[2]
        self.assertEqual(event3["modelVersion"], KNOWN_MODEL)
        candidate3 = event3["candidates"][0]
        self.assertEqual(candidate3["finishReason"], "STOP")
        # Finish-only event has no content key
        self.assertNotIn("content", candidate3)

        # No [DONE] sentinel anywhere in the body (Gemini contract)
        self.assertNotIn("[DONE]", body)

        # Body ends with the last event's trailing newlines, not [DONE]
        self.assertTrue(body.endswith("\n\n"))
        self.assertFalse(body.endswith("data: [DONE]\n\n"))

        # --- Handler call assertions ---
        self.assertEqual(len(self.fake_handler.calls), 1)
        call = self.fake_handler.calls[0]
        self.assertEqual(call["model"], KNOWN_MODEL)
        self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
        self.assertTrue(call["stream"])
        self.assertIsNone(call["images"])
        self.assertIsNone(call["video_media_id"])


# ===========================================================================
# Run Tests
# ===========================================================================
if __name__ == "__main__":
    unittest.main()
