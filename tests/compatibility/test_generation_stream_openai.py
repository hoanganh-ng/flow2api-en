"""Mocked OpenAI streaming generator contract tests.

These tests exercise the internal ``_iterate_openai_stream`` async generator
directly, using a fake handler that yields deterministic strings. The tests
cover SSE framing, reasoning-content progress, ``[DONE]`` termination,
multiple-chunk ordering, empty-stream behavior, and direct handler-exception
propagation.

No FastAPI app, TestClient, HTTP transport, StreamingResponse construction,
lifespan, network, database, browser, captcha, proxy, token, session service,
media retrieval, or real credentials are used.

Sprint 006G — Mocked OpenAI Streaming Generator Contract.
"""

import json
import unittest
from unittest.mock import patch

import src.api.routes as routes_module
from src.api.routes import (
    NormalizedGenerationRequest,
    _iterate_openai_stream,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KNOWN_MODEL = "gemini-2.0-flash-exp"
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


def _make_prefixed_sse_chunk(text: str = "Already framed") -> str:
    """Build a chunk that already has the ``data: `` prefix.

    The generator should pass such chunks through unchanged.
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


async def _collect_stream(generator) -> list[str]:
    """Consume an async generator into a list of yielded strings."""
    results = []
    async for chunk in generator:
        results.append(chunk)
    return results


# ===========================================================================
# 1. Text-Delta SSE Framing
# ===========================================================================
class TextDeltaSSEFramingTests(unittest.IsolatedAsyncioTestCase):
    """Test that _iterate_openai_stream correctly frames raw JSON text deltas."""

    async def test_raw_json_gets_sse_framing(self):
        """Raw JSON handler output is wrapped in ``data: ...\\n\\n``."""
        raw_chunk = _make_text_delta_chunk("Hello")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # Expect: framed chunk + [DONE]
        self.assertEqual(len(results), 2)

        framed = results[0]
        self.assertTrue(framed.startswith("data: "))
        self.assertTrue(framed.endswith("\n\n"))

        # Extract JSON payload
        payload_str = framed[len("data: "):-2]  # strip "data: " and "\n\n"
        payload = json.loads(payload_str)
        self.assertEqual(payload["choices"][0]["delta"]["content"], "Hello")

        # [DONE] must not appear before the chunk
        self.assertNotIn("[DONE]", results[0])

    async def test_already_prefixed_chunk_passed_through(self):
        """Chunks already starting with ``data: `` are yielded unchanged."""
        prefixed = _make_prefixed_sse_chunk("Passthrough")
        fake = FakeStreamingHandler(yield_values=[prefixed])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # Expect: passthrough chunk + [DONE]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], prefixed)


# ===========================================================================
# 2. Reasoning-Content Progress
# ===========================================================================
class ReasoningContentProgressTests(unittest.IsolatedAsyncioTestCase):
    """Test that reasoning_content deltas are preserved in SSE framing."""

    async def test_reasoning_content_preserved(self):
        """A chunk with ``delta.reasoning_content`` is framed and preserved."""
        raw_chunk = _make_reasoning_delta_chunk("Uploading image...")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertGreaterEqual(len(results), 2)

        # Extract the framed chunk
        framed = results[0]
        payload_str = framed[len("data: "):-2]
        payload = json.loads(payload_str)

        # reasoning_content must be present and preserved
        delta = payload["choices"][0]["delta"]
        self.assertEqual(delta.get("reasoning_content"), "Uploading image...")

    async def test_reasoning_content_matches_fx_os_002_semantics(self):
        """Verify generator output is consistent with FX-OS-002 fixture semantics.

        FX-OS-002 contains two SSE chunks with ``delta.reasoning_content``.
        This test does not exercise HTTP transport; it confirms that the
        generator preserves reasoning_content at the async-generator level.
        """
        from tests.compatibility.helpers.fixture_loader import load_text

        fixture_text = load_text("generation/openai-streaming/reasoning-progress.sse.txt")

        # Parse fixture into individual data: lines
        fixture_data_lines = [
            line for line in fixture_text.strip().split("\n")
            if line.startswith("data: ")
        ]
        self.assertGreaterEqual(len(fixture_data_lines), 2)

        # Extract JSON payloads from fixture
        fixture_payloads = [json.loads(line[len("data: "):]) for line in fixture_data_lines]

        # Build fake handler yielding the same raw JSON strings (without data: prefix)
        raw_chunks = [json.dumps(p) for p in fixture_payloads]
        fake = FakeStreamingHandler(yield_values=raw_chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # All fixture chunks should be framed, plus [DONE]
        self.assertEqual(len(results), len(fixture_data_lines) + 1)

        # Verify reasoning_content preserved in each chunk
        for i, fixture_payload in enumerate(fixture_payloads):
            framed = results[i]
            payload_str = framed[len("data: "):-2]
            actual_payload = json.loads(payload_str)
            expected_rc = fixture_payload["choices"][0]["delta"].get("reasoning_content")
            actual_rc = actual_payload["choices"][0]["delta"].get("reasoning_content")
            self.assertEqual(actual_rc, expected_rc)


# ===========================================================================
# 3. [DONE] Termination
# ===========================================================================
class DoneTerminationTests(unittest.IsolatedAsyncioTestCase):
    """Test that ``data: [DONE]\\n\\n`` is emitted exactly once at the end."""

    async def test_done_emitted_exactly_once(self):
        """After consuming a finite stream, ``data: [DONE]\\n\\n`` appears once."""
        raw_chunk = _make_text_delta_chunk("content")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        done_events = [r for r in results if r == "data: [DONE]\n\n"]
        self.assertEqual(len(done_events), 1)

    async def test_done_is_final_event(self):
        """``data: [DONE]\\n\\n`` is the last yielded value."""
        raw_chunk = _make_text_delta_chunk("content")
        fake = FakeStreamingHandler(yield_values=[raw_chunk])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertEqual(results[-1], "data: [DONE]\n\n")

    async def test_done_exact_framing(self):
        """The [DONE] event has exact framing: ``data: [DONE]\\n\\n``."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "data: [DONE]\n\n")

    async def test_done_matches_fx_os_003_semantics(self):
        """Verify [DONE] framing matches FX-OS-003 fixture semantics.

        FX-OS-003 contains a sample chunk followed by ``data: [DONE]``.
        This test confirms the generator emits the same ``data: [DONE]``
        termination string as found in the fixture.
        """
        from tests.compatibility.helpers.fixture_loader import load_text

        fixture_text = load_text("generation/openai-streaming/done-termination.sse.txt")

        # FX-OS-003 ends with "data: [DONE]" as the last non-empty line
        non_empty_lines = [line for line in fixture_text.split("\n") if line.strip()]
        self.assertTrue(non_empty_lines)
        last_line = non_empty_lines[-1]
        self.assertEqual(last_line, "data: [DONE]")

        # The generator emits "data: [DONE]\n\n"
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # Compare generator output (stripped) with fixture last line (stripped)
        self.assertEqual(results[0].strip(), last_line)


# ===========================================================================
# 4. Multiple-Chunk Ordering
# ===========================================================================
class MultipleChunkOrderingTests(unittest.IsolatedAsyncioTestCase):
    """Test that multiple chunks are yielded in order with [DONE] at end."""

    async def test_ordering_preserved(self):
        """Two chunks are yielded in the same order as the handler."""
        chunk_a = _make_text_delta_chunk("first")
        chunk_b = _make_text_delta_chunk("second")
        fake = FakeStreamingHandler(yield_values=[chunk_a, chunk_b])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # Expect: chunk_a framed, chunk_b framed, [DONE]
        self.assertEqual(len(results), 3)

        # First chunk
        payload_a = json.loads(results[0][len("data: "):-2])
        self.assertEqual(payload_a["choices"][0]["delta"]["content"], "first")

        # Second chunk
        payload_b = json.loads(results[1][len("data: "):-2])
        self.assertEqual(payload_b["choices"][0]["delta"]["content"], "second")

        # [DONE] at end
        self.assertEqual(results[2], "data: [DONE]\n\n")

    async def test_no_duplication(self):
        """Each handler yield produces exactly one output chunk (no duplication)."""
        chunks = [_make_text_delta_chunk(f"chunk-{i}") for i in range(3)]
        fake = FakeStreamingHandler(yield_values=chunks)

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        # 3 content chunks + 1 [DONE] = 4 total
        self.assertEqual(len(results), 4)

        # No duplicate content in the non-DONE results
        content_chunks = [r for r in results if r != "data: [DONE]\n\n"]
        self.assertEqual(len(content_chunks), 3)

        # Verify each unique
        payloads = [json.loads(c[len("data: "):-2]) for c in content_chunks]
        texts = [p["choices"][0]["delta"]["content"] for p in payloads]
        self.assertEqual(texts, ["chunk-0", "chunk-1", "chunk-2"])

    async def test_handler_called_once(self):
        """The handler's handle_generation is invoked exactly once."""
        chunk = _make_text_delta_chunk("once")
        fake = FakeStreamingHandler(yield_values=[chunk])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])


# ===========================================================================
# 5. Empty Handler Stream
# ===========================================================================
class EmptyHandlerStreamTests(unittest.IsolatedAsyncioTestCase):
    """Test behavior when the handler yields no chunks."""

    async def test_empty_stream_emits_only_done(self):
        """When the handler yields nothing, only ``data: [DONE]\\n\\n`` is emitted."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            results = await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "data: [DONE]\n\n")

    async def test_empty_stream_handler_called(self):
        """The handler is still invoked even when it yields nothing."""
        fake = FakeStreamingHandler(yield_values=[])

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_openai_stream(_make_normalized_request())
            )

        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])
        self.assertEqual(fake.calls[0]["model"], KNOWN_MODEL)
        self.assertEqual(fake.calls[0]["prompt"], SYNTHETIC_PROMPT)
        self.assertIsNone(fake.calls[0]["images"])
        self.assertIsNone(fake.calls[0]["video_media_id"])


# ===========================================================================
# 6. Mutable State and Cleanup
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

    async def test_handler_arguments_forwarded(self):
        """Verify all NormalizedGenerationRequest fields are forwarded correctly."""
        fake = FakeStreamingHandler(yield_values=[])
        normalized = NormalizedGenerationRequest(
            model="test-model",
            prompt="test-prompt",
            images=[b"fake-image-bytes"],
            messages=None,
            video_media_id="test-media-id",
        )

        with patch.object(routes_module, "generation_handler", fake):
            await _collect_stream(
                _iterate_openai_stream(normalized, base_url_override="https://base.example")
            )

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["model"], "test-model")
        self.assertEqual(call["prompt"], "test-prompt")
        self.assertEqual(call["images"], [b"fake-image-bytes"])
        self.assertTrue(call["stream"])
        self.assertEqual(call["base_url_override"], "https://base.example")
        self.assertEqual(call["video_media_id"], "test-media-id")

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
                _iterate_openai_stream(normalized)
            )

        # Source: images=normalized.images if normalized.images else None
        # Empty list is falsy, so None is passed.
        self.assertIsNone(fake.calls[0]["images"])


# ===========================================================================
# 7. Handler Exception Propagation
# ===========================================================================
class HandlerExceptionPropagationTests(unittest.IsolatedAsyncioTestCase):
    """Verify that handler exceptions propagate directly without SSE synthesis.

    ``_iterate_openai_stream`` contains no local exception conversion.
    Exceptions raised by the handler propagate to the caller and interrupt
    normal stream termination, so the generator does not emit its final
    ``[DONE]`` event. Client-visible HTTP/StreamingResponse handling of the
    propagated exception remains out of scope.
    """

    async def test_exception_before_first_chunk(self):
        """Exception before any yield propagates; no [DONE] or SSE error emitted."""
        error = RuntimeError("synthetic stream failure")
        fake = FakeFailingHandler(yield_values=[], error=error)
        original = routes_module.generation_handler

        with patch.object(routes_module, "generation_handler", fake):
            with self.assertRaises(RuntimeError) as ctx:
                await _collect_stream(
                    _iterate_openai_stream(_make_normalized_request())
                )

        # Original exception type and message preserved
        self.assertIsInstance(ctx.exception, RuntimeError)
        self.assertEqual(str(ctx.exception), "synthetic stream failure")

        # Handler invoked exactly once
        self.assertEqual(len(fake.calls), 1)
        self.assertTrue(fake.calls[0]["stream"])

        # generation_handler restored after patch
        self.assertIs(routes_module.generation_handler, original)

    async def test_exception_after_one_chunk(self):
        """First chunk is emitted, then exception propagates; no [DONE] emitted."""
        raw_chunk = _make_text_delta_chunk("partial content")
        error = RuntimeError("synthetic stream failure")
        fake = FakeFailingHandler(yield_values=[raw_chunk], error=error)
        normalized = _make_normalized_request()

        with patch.object(routes_module, "generation_handler", fake):
            stream = _iterate_openai_stream(normalized)

            # First event should be the framed chunk
            first_event = await anext(stream)
            self.assertTrue(first_event.startswith("data: "))
            self.assertTrue(first_event.endswith("\n\n"))
            payload = json.loads(first_event[len("data: "):-2])
            self.assertEqual(
                payload["choices"][0]["delta"]["content"], "partial content"
            )

            # Second iteration should raise the handler exception
            with self.assertRaises(RuntimeError) as ctx:
                await anext(stream)

        # Exception type and message preserved
        self.assertIsInstance(ctx.exception, RuntimeError)
        self.assertEqual(str(ctx.exception), "synthetic stream failure")

        # Handler invoked once
        self.assertEqual(len(fake.calls), 1)


# ===========================================================================
# Run Tests
# ===========================================================================
if __name__ == "__main__":
    unittest.main()
