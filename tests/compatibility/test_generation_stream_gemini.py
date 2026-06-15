"""Mocked Gemini streaming generator contract tests.

These tests exercise the internal ``_iterate_gemini_stream`` async generator
directly, using a fake handler that yields deterministic strings. The tests
cover Gemini event framing, text conversion, finish-reason mapping,
reasoning-content behavior, empty-stream behavior, non-emitting chunks,
handler error-payload conversion, and direct handler-exception propagation.

No FastAPI app, TestClient, HTTP transport, StreamingResponse construction,
lifespan, network, database, browser, captcha, proxy, token, session service,
media retrieval, or real credentials are used.

Sprint 006H — Mocked Gemini Streaming Generator Contract.
"""

import json
import unittest
from unittest.mock import patch

import src.api.routes as routes_module
from src.api.routes import (
    NormalizedGenerationRequest,
    _iterate_gemini_stream,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-2.0-flash-exp"
RESPONSE_MODEL = "gemini-2.0-flash-exp"
SYNTHETIC_PROMPT = "Hello, tell me a short story."
FAKE_BASE_URL = "https://test.local"


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
def _make_normalized_request(
    model: str = KNOWN_MODEL,
    prompt: str = SYNTHETIC_PROMPT,
) -> NormalizedGenerationRequest:
    """Build a minimal NormalizedGenerationRequest for streaming tests."""
    return NormalizedGenerationRequest(
        model=model,
        prompt=prompt,
        images=[],
    )


def _make_text_delta_chunk(text: str = "Hello world") -> str:
    """Build a raw JSON string matching a typical OpenAI text-delta chunk.

    The handler yields raw JSON (without the ``data: `` prefix); the
    Gemini generator converts it through the conversion helper.
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


def _make_prefixed_text_delta_chunk(text: str = "Hello world") -> str:
    """Build a chunk that already has the ``data: `` prefix.

    The Gemini generator strips the prefix, parses the JSON, and
    converts through the Gemini event helper.
    """
    payload = json.dumps({
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
    return f"data: {payload}"


def _make_finish_reason_chunk(reason: str = "stop") -> str:
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


def _make_reasoning_delta_chunk(reasoning_text: str = "Thinking...") -> str:
    """Build a raw JSON string with a reasoning_content delta."""
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {"reasoning_content": reasoning_text},
            "finish_reason": None,
        }],
    })


def _make_non_emitting_chunk() -> str:
    """Build a chunk that the conversion helper maps to None (no event).

    An empty delta with no finish_reason results in a candidate dict
    with only ``index``, so the helper returns None.
    """
    return json.dumps({
        "id": "chatcmpl-1700000000",
        "object": "chat.completion.chunk",
        "created": 1700000000,
        "model": "flow2api",
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": None,
        }],
    })


def _make_error_payload_chunk(
    status_code: int = 500,
    message: str = "upstream failure",
) -> str:
    """Build a raw JSON string containing an ``error`` key.

    The Gemini generator has an explicit local error conversion path
    that builds a Gemini error event and terminates the stream.
    """
    return json.dumps({
        "error": {
            "message": message,
            "status_code": status_code,
        }
    })


def _make_prefixed_done_chunk() -> str:
    """Build a ``data: [DONE]`` chunk that the generator must skip."""
    return "data: [DONE]"


async def _collect_stream(generator) -> list[str]:
    """Consume an async generator into a list of yielded strings."""
    results = []
    async for chunk in generator:
        results.append(chunk)
    return results


def _parse_gemini_event(event: str) -> dict:
    """Parse a ``data: {...}\\n\\n`` framed Gemini event into a dict."""
    assert event.startswith("data: "), f"Event missing data: prefix: {event!r}"
    assert event.endswith("\n\n"), f"Event missing trailing newlines: {event!r}"
    return json.loads(event[len("data: "):-2])


# ===========================================================================
# 1. Text Delta — Gemini Event Framing
# ===========================================================================
class TextDeltaGeminiEventFramingTests(unittest.IsolatedAsyncioTestCase):
    """Test that _iterate_gemini_stream converts text deltas to Gemini events."""

    async def test_raw_json_produces_gemini_event(self):
        """Raw JSON handler output is converted to a Gemini-shaped event."""
        raw_chunk = _make_text_delta_chunk("Hello")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)

        event = results[0]
        self.assertTrue(event.startswith("data: "))
        self.assertTrue(event.endswith("\n\n"))

        payload = _parse_gemini_event(event)
        self.assertIn("candidates", payload)
        self.assertIn("modelVersion", payload)
        self.assertEqual(payload["modelVersion"], RESPONSE_MODEL)

        candidate = payload["candidates"][0]
        self.assertEqual(candidate["index"], 0)
        self.assertIn("content", candidate)
        self.assertEqual(candidate["content"]["role"], "model")

        parts = candidate["content"]["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["text"], "Hello")

    async def test_no_done_termination(self):
        """Gemini stream does not emit ``data: [DONE]`` after text deltas."""
        raw_chunk = _make_text_delta_chunk("content")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        for event in results:
            self.assertNotIn("[DONE]", event)

    async def test_no_openai_wrapper_leak(self):
        """The Gemini event does not contain OpenAI-specific wrapper fields."""
        raw_chunk = _make_text_delta_chunk("Hello")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        # No OpenAI-specific fields
        self.assertNotIn("id", payload)
        self.assertNotIn("object", payload)
        self.assertNotIn("created", payload)
        self.assertNotIn("choices", payload)

    async def test_prefixed_chunk_converted_to_gemini_event(self):
        """A ``data: ``-prefixed chunk is stripped, parsed, and converted."""
        prefixed = _make_prefixed_text_delta_chunk("Passthrough")
        fake = FakeStreamingHandler(yield_values=[prefixed])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        parts = payload["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], "Passthrough")

    async def test_text_preserved_exactly(self):
        """Text content is preserved without transformation."""
        text = "Exact preservation test: special chars <>&'\""
        raw_chunk = _make_text_delta_chunk(text)
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        parts = payload["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], text)


# ===========================================================================
# 2. Multiple Chunks — Ordering
# ===========================================================================
class MultipleChunkOrderingTests(unittest.IsolatedAsyncioTestCase):
    """Test that multiple chunks are yielded in order without duplication."""

    async def test_ordering_preserved(self):
        """Two text chunks are yielded in the same order as the handler."""
        chunk_a = _make_text_delta_chunk("first")
        chunk_b = _make_text_delta_chunk("second")
        fake = FakeStreamingHandler(yield_values=[chunk_a, chunk_b])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 2)

        payload_a = _parse_gemini_event(results[0])
        self.assertEqual(
            payload_a["candidates"][0]["content"]["parts"][0]["text"],
            "first",
        )

        payload_b = _parse_gemini_event(results[1])
        self.assertEqual(
            payload_b["candidates"][0]["content"]["parts"][0]["text"],
            "second",
        )

    async def test_no_duplication(self):
        """Each handler yield produces at most one Gemini event."""
        chunks = [_make_text_delta_chunk(f"chunk-{i}") for i in range(3)]
        fake = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 3)

        texts = [
            _parse_gemini_event(e)["candidates"][0]["content"]["parts"][0]["text"]
            for e in results
        ]
        self.assertEqual(texts, ["chunk-0", "chunk-1", "chunk-2"])

    async def test_handler_called_once(self):
        """The handler's handle_generation is invoked exactly once."""
        chunk = _make_text_delta_chunk("once")
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])

    async def test_normal_iteration_ends_without_done(self):
        """Normal iteration ends without any ``[DONE]`` sentinel."""
        chunks = [_make_text_delta_chunk("a"), _make_text_delta_chunk("b")]
        fake = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        for event in results:
            self.assertNotIn("[DONE]", event)


# ===========================================================================
# 3. Finish Reason
# ===========================================================================
class FinishReasonTests(unittest.IsolatedAsyncioTestCase):
    """Test that OpenAI finish_reason values are mapped to Gemini finishReason."""

    async def test_stop_mapped_to_stop(self):
        """OpenAI ``stop`` is mapped to Gemini ``STOP``."""
        chunk = _make_finish_reason_chunk("stop")
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        candidate = payload["candidates"][0]
        self.assertEqual(candidate["finishReason"], "STOP")
        # Finish-only chunk has no content key
        self.assertNotIn("content", candidate)

    async def test_length_mapped_to_max_tokens(self):
        """OpenAI ``length`` is mapped to Gemini ``MAX_TOKENS``."""
        chunk = _make_finish_reason_chunk("length")
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        self.assertEqual(payload["candidates"][0]["finishReason"], "MAX_TOKENS")

    async def test_content_filter_mapped_to_safety(self):
        """OpenAI ``content_filter`` is mapped to Gemini ``SAFETY``."""
        chunk = _make_finish_reason_chunk("content_filter")
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        self.assertEqual(payload["candidates"][0]["finishReason"], "SAFETY")

    async def test_finish_with_text_produces_both(self):
        """A chunk with both text and finish_reason produces content + finishReason."""
        raw = json.dumps({
            "choices": [{
                "index": 0,
                "delta": {"content": "final"},
                "finish_reason": "stop",
            }],
        })
        fake = FakeStreamingHandler(yield_values=[raw])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        candidate = payload["candidates"][0]
        self.assertEqual(candidate["finishReason"], "STOP")
        self.assertIn("content", candidate)
        self.assertEqual(candidate["content"]["parts"][0]["text"], "final")


# ===========================================================================
# 4. Reasoning Content
# ===========================================================================
class ReasoningContentTests(unittest.IsolatedAsyncioTestCase):
    """Test reasoning_content delta behavior in the Gemini stream generator."""

    async def test_reasoning_content_appears_as_text(self):
        """reasoning_content is placed into Gemini parts as text.

        The conversion helper uses ``delta.get("reasoning_content") or
        delta.get("content") or ""``. When reasoning_content is present,
        it is used as the text value in the Gemini parts output.
        """
        raw_chunk = _make_reasoning_delta_chunk("Uploading image...")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        parts = payload["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], "Uploading image...")

    async def test_reasoning_content_preferred_over_content(self):
        """When both reasoning_content and content are present, reasoning wins.

        The ``or`` chain in the conversion helper means reasoning_content
        is evaluated first.
        """
        raw = json.dumps({
            "choices": [{
                "index": 0,
                "delta": {
                    "reasoning_content": "thinking",
                    "content": "visible",
                },
                "finish_reason": None,
            }],
        })
        fake = FakeStreamingHandler(yield_values=[raw])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        payload = _parse_gemini_event(results[0])
        parts = payload["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], "thinking")


# ===========================================================================
# 5. Empty Handler Stream
# ===========================================================================
class EmptyHandlerStreamTests(unittest.IsolatedAsyncioTestCase):
    """Test behavior when the handler yields no chunks."""

    async def test_empty_stream_yields_nothing(self):
        """When the handler yields nothing, the generator yields nothing.

        Unlike ``_iterate_openai_stream``, the Gemini generator does not
        emit a terminal ``[DONE]`` event.
        """
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 0)

    async def test_empty_stream_handler_called(self):
        """The handler is still invoked even when it yields nothing."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])
        self.assertEqual(fake.calls[0]["model"], KNOWN_MODEL)
        self.assertEqual(fake.calls[0]["prompt"], SYNTHETIC_PROMPT)
        self.assertIsNone(fake.calls[0]["images"])
        self.assertIsNone(fake.calls[0]["video_media_id"])

    async def test_empty_stream_no_terminal_event(self):
        """No terminal event of any kind is emitted on an empty stream."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(results, [])


# ===========================================================================
# 6. Non-Emitting Chunk
# ===========================================================================
class NonEmittingChunkTests(unittest.IsolatedAsyncioTestCase):
    """Test that chunks the conversion helper maps to None are skipped."""

    async def test_non_emitting_chunk_skipped(self):
        """A chunk with empty delta and no finish_reason produces no event."""
        chunk = _make_non_emitting_chunk()
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 0)

    async def test_valid_chunks_after_non_emitting_still_appear(self):
        """A valid chunk after a non-emitting one is still yielded."""
        non_emitting = _make_non_emitting_chunk()
        valid = _make_text_delta_chunk("after-skip")
        fake = FakeStreamingHandler(yield_values=[non_emitting, valid])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        parts = payload["candidates"][0]["content"]["parts"]
        self.assertEqual(parts[0]["text"], "after-skip")

    async def test_multiple_non_emitting_chunks_all_skipped(self):
        """Multiple non-emitting chunks are all skipped silently."""
        chunks = [_make_non_emitting_chunk() for _ in range(3)]
        fake = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 0)


# ===========================================================================
# 7. Handler Error Payload
# ===========================================================================
class HandlerErrorPayloadTests(unittest.IsolatedAsyncioTestCase):
    """Test the explicit local error conversion path.

    When the handler yields a JSON payload containing an ``error`` key,
    ``_iterate_gemini_stream`` converts it to a Gemini error event using
    ``_build_gemini_error_payload`` and then terminates the generator
    via ``return``.
    """

    async def test_error_payload_converted_to_gemini_error_event(self):
        """An error JSON chunk is converted to a Gemini-shaped error event."""
        error_chunk = _make_error_payload_chunk(500, "upstream failure")
        fake = FakeStreamingHandler(yield_values=[error_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], 500)
        self.assertEqual(payload["error"]["message"], "upstream failure")
        self.assertEqual(payload["error"]["status"], "INTERNAL")

    async def test_error_payload_terminates_stream(self):
        """After an error event, the generator returns; subsequent chunks ignored."""
        error_chunk = _make_error_payload_chunk(400, "bad request")
        valid_chunk = _make_text_delta_chunk("should not appear")
        fake = FakeStreamingHandler(yield_values=[error_chunk, valid_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        # Only the error event; the valid chunk is never reached
        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        self.assertIn("error", payload)

    async def test_prefixed_error_payload_converted(self):
        """A ``data: ``-prefixed error chunk follows the same conversion path."""
        error_payload = json.dumps({
            "error": {"message": "prefixed error", "status_code": 401}
        })
        prefixed = f"data: {error_payload}"
        fake = FakeStreamingHandler(yield_values=[prefixed])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        self.assertEqual(payload["error"]["code"], 401)
        self.assertEqual(payload["error"]["message"], "prefixed error")
        self.assertEqual(payload["error"]["status"], "UNAUTHENTICATED")

    async def test_error_payload_no_done(self):
        """No ``[DONE]`` is emitted after the error event."""
        error_chunk = _make_error_payload_chunk(500, "fail")
        fake = FakeStreamingHandler(yield_values=[error_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        for event in results:
            self.assertNotIn("[DONE]", event)


# ===========================================================================
# 8. Data-Prefix [DONE] Handling
# ===========================================================================
class DataPrefixDoneHandlingTests(unittest.IsolatedAsyncioTestCase):
    """Test that ``data: [DONE]`` from the handler is silently skipped."""

    async def test_done_chunk_skipped(self):
        """A ``data: [DONE]`` handler yield is skipped; no event emitted."""
        fake = FakeStreamingHandler(yield_values=[_make_prefixed_done_chunk()])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 0)

    async def test_done_between_valid_chunks(self):
        """A ``data: [DONE]`` between valid chunks is skipped; both appear."""
        chunk_a = _make_prefixed_text_delta_chunk("before")
        done = _make_prefixed_done_chunk()
        chunk_b = _make_prefixed_text_delta_chunk("after")
        fake = FakeStreamingHandler(yield_values=[chunk_a, done, chunk_b])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 2)
        payload_a = _parse_gemini_event(results[0])
        self.assertEqual(
            payload_a["candidates"][0]["content"]["parts"][0]["text"],
            "before",
        )
        payload_b = _parse_gemini_event(results[1])
        self.assertEqual(
            payload_b["candidates"][0]["content"]["parts"][0]["text"],
            "after",
        )


# ===========================================================================
# 9. Exception Before First Chunk
# ===========================================================================
class ExceptionBeforeFirstChunkTests(unittest.IsolatedAsyncioTestCase):
    """Verify that handler exceptions before any yield propagate directly.

    ``_iterate_gemini_stream`` contains no local exception wrapping.
    Exceptions propagate from the handler through the async generator.
    """

    async def test_exception_propagates(self):
        """Exception before any yield propagates with original type and message."""
        error = RuntimeError("synthetic stream failure")
        fake = FakeFailingHandler(yield_values=[], error=error)
        original = routes_module.generation_handler

        with patch.object(routes_module, "generation_handler", fake):
            with self.assertRaises(RuntimeError) as ctx:
                await _collect_stream(
                    _iterate_gemini_stream(
                        _make_normalized_request(), RESPONSE_MODEL,
                    )
                )

        self.assertIsInstance(ctx.exception, RuntimeError)
        self.assertEqual(str(ctx.exception), "synthetic stream failure")

        # Handler invoked exactly once
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])

        # generation_handler restored after patch
        self.assertIs(routes_module.generation_handler, original)

    async def test_no_gemini_event_on_exception(self):
        """No Gemini event or ``[DONE]`` is emitted when handler raises immediately."""
        error = ValueError("early failure")
        fake = FakeFailingHandler(yield_values=[], error=error)

        with patch.object(routes_module, "generation_handler", fake):
            with self.assertRaises(ValueError):
                await _collect_stream(
                    _iterate_gemini_stream(
                        _make_normalized_request(), RESPONSE_MODEL,
                    )
                )

        # If we got here, the exception was raised — no events collected


# ===========================================================================
# 10. Exception After One Event
# ===========================================================================
class ExceptionAfterOneEventTests(unittest.IsolatedAsyncioTestCase):
    """Verify exception propagation after partial output."""

    async def test_first_event_then_exception(self):
        """First event is emitted, then the handler exception propagates."""
        raw_chunk = _make_text_delta_chunk("partial content")
        error = RuntimeError("synthetic mid-stream failure")
        fake = FakeFailingHandler(yield_values=[raw_chunk], error=error)

        with patch.object(routes_module, "generation_handler", fake):
            stream = _iterate_gemini_stream(
                _make_normalized_request(), RESPONSE_MODEL,
            )

            # First event should be a valid Gemini event
            first_event = await anext(stream)
            self.assertTrue(first_event.startswith("data: "))
            self.assertTrue(first_event.endswith("\n\n"))
            payload = _parse_gemini_event(first_event)
            self.assertEqual(
                payload["candidates"][0]["content"]["parts"][0]["text"],
                "partial content",
            )

            # Second iteration should raise the handler exception
            with self.assertRaises(RuntimeError) as ctx:
                await anext(stream)

        self.assertIsInstance(ctx.exception, RuntimeError)
        self.assertEqual(str(ctx.exception), "synthetic mid-stream failure")

        # Handler invoked once
        self.assertEqual(len(fake.calls), 1)

    async def test_no_synthetic_error_event(self):
        """No synthetic error event or ``[DONE]`` is emitted after exception."""
        raw_chunk = _make_text_delta_chunk("partial")
        error = RuntimeError("mid-stream failure")
        fake = FakeFailingHandler(yield_values=[raw_chunk], error=error)

        with patch.object(routes_module, "generation_handler", fake):
            stream = _iterate_gemini_stream(
                _make_normalized_request(), RESPONSE_MODEL,
            )

            # Consume first event
            await anext(stream)

            # Exception on next
            with self.assertRaises(RuntimeError):
                await anext(stream)

        # If we got here, exception propagated — no synthetic events


# ===========================================================================
# 11. Argument Forwarding
# ===========================================================================
class ArgumentForwardingTests(unittest.IsolatedAsyncioTestCase):
    """Verify that NormalizedGenerationRequest fields are forwarded correctly."""

    async def test_basic_arguments_forwarded(self):
        """Model, prompt, stream=True, and base_url_override are forwarded."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(),
                    RESPONSE_MODEL,
                    base_url_override=FAKE_BASE_URL,
                )
            )

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["model"], KNOWN_MODEL)
        self.assertEqual(call["prompt"], SYNTHETIC_PROMPT)
        self.assertTrue(call["stream"])
        self.assertEqual(call["base_url_override"], FAKE_BASE_URL)

    async def test_empty_images_becomes_none(self):
        """When images is an empty list, the handler receives None."""
        fake = FakeStreamingHandler(yield_values=[])
        normalized = NormalizedGenerationRequest(
            model=KNOWN_MODEL,
            prompt=SYNTHETIC_PROMPT,
            images=[],
        )

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(normalized, RESPONSE_MODEL)
            )

        self.assertIsNone(fake.calls[0]["images"])

    async def test_images_forwarded(self):
        """Non-empty images list is forwarded as-is."""
        fake = FakeStreamingHandler(yield_values=[])
        normalized = NormalizedGenerationRequest(
            model=KNOWN_MODEL,
            prompt=SYNTHETIC_PROMPT,
            images=[b"fake-image-bytes"],
        )

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(normalized, RESPONSE_MODEL)
            )

        self.assertEqual(fake.calls[0]["images"], [b"fake-image-bytes"])

    async def test_video_media_id_forwarded(self):
        """video_media_id from the normalized request is forwarded."""
        fake = FakeStreamingHandler(yield_values=[])
        normalized = NormalizedGenerationRequest(
            model=KNOWN_MODEL,
            prompt=SYNTHETIC_PROMPT,
            images=[],
            video_media_id="test-media-id",
        )

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(normalized, RESPONSE_MODEL)
            )

        self.assertEqual(fake.calls[0]["video_media_id"], "test-media-id")

    async def test_base_url_override_none_by_default(self):
        """When base_url_override is not passed, handler receives None."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertIsNone(fake.calls[0]["base_url_override"])


# ===========================================================================
# 12. Mutable State and Cleanup
# ===========================================================================
class MutableStateAndCleanupTests(unittest.IsolatedAsyncioTestCase):
    """Verify generation_handler is patchable and restored per test."""

    async def test_handler_restored_after_patch(self):
        """After exiting the patch context, the original handler is restored."""
        original = routes_module.generation_handler

        fake = FakeStreamingHandler(yield_values=[])
        with patch.object(routes_module, "generation_handler", fake):
            self.assertIs(routes_module.generation_handler, fake)

        self.assertIs(routes_module.generation_handler, original)

    async def test_no_metrics_or_config_mutation(self):
        """The generator does not mutate Prometheus registries or shared config.

        This test verifies that running the generator does not alter
        module-level state beyond the handler patch lifecycle.
        """
        import src.api.routes as mod

        original_handler = mod.generation_handler

        fake = FakeStreamingHandler(yield_values=[_make_text_delta_chunk("x")])
        with patch.object(mod, "generation_handler", fake):
            await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        # Handler restored
        self.assertIs(mod.generation_handler, original_handler)


# ===========================================================================
# 13. Termination Contract
# ===========================================================================
class TerminationContractTests(unittest.IsolatedAsyncioTestCase):
    """Document and assert the Gemini stream termination contract.

    Unlike ``_iterate_openai_stream`` which always emits
    ``data: [DONE]\\n\\n`` as a terminal event, ``_iterate_gemini_stream``
    does NOT emit any terminal sentinel. The generator simply ends when
    the handler iteration completes.

    If the handler yields ``data: [DONE]``, the generator skips it
    (continues to next chunk) rather than terminating.
    """

    async def test_normal_termination_is_silent(self):
        """After all handler chunks, the generator ends without any terminal event."""
        chunks = [_make_text_delta_chunk("a"), _make_text_delta_chunk("b")]
        fake = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        # Exactly two events, no terminal event
        self.assertEqual(len(results), 2)
        for event in results:
            self.assertNotIn("[DONE]", event)

    async def test_error_terminates_early(self):
        """An error payload causes early termination via return."""
        error = _make_error_payload_chunk(500, "fatal")
        text = _make_text_delta_chunk("unreachable")
        fake = FakeStreamingHandler(yield_values=[error, text])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        self.assertEqual(len(results), 1)
        payload = _parse_gemini_event(results[0])
        self.assertIn("error", payload)

    async def test_gemini_vs_openai_done_comparison(self):
        """Gemini stream never emits ``[DONE]``; OpenAI stream always does.

        This test documents the observable difference between the two
        internal generators at the async-generator level.
        """
        from src.api.routes import _iterate_openai_stream

        fake_gemini = FakeStreamingHandler(yield_values=[])
        fake_openai = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake_gemini):
            gemini_results = await _collect_stream(
                _iterate_gemini_stream(
                    _make_normalized_request(), RESPONSE_MODEL,
                )
            )

        with patch.object(routes_module, "generation_handler", fake_openai):
            openai_results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # Gemini: empty, no terminal event
        self.assertEqual(len(gemini_results), 0)

        # OpenAI: emits [DONE] even on empty stream
        self.assertEqual(len(openai_results), 1)
        self.assertEqual(openai_results[0], "data: [DONE]\n\n")


# ===========================================================================
# Run Tests
# ===========================================================================
if __name__ == "__main__":
    unittest.main()
