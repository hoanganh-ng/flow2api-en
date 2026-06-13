"""Unit tests for pure conversion/helper functions in src.api.routes.

These tests exercise offline, deterministic helper behavior without
constructing the FastAPI application, invoking route handlers, starting
lifespan, or contacting upstream services.

Only standard-library unittest is used. No pytest or extra dependencies.
"""

import asyncio
import json
import unittest

from src.api.routes import (
    _build_gemini_error_payload,
    _coerce_gemini_contents,
    _convert_openai_stream_chunk_to_gemini_event,
    _detect_image_mime_type,
    _extract_url_from_openai_payload,
    _normalize_finish_reason,
    _sanitize_media_prompt,
)
from src.core.models import GeminiContent


# ---------------------------------------------------------------------------
# _sanitize_media_prompt
# ---------------------------------------------------------------------------
class SanitizeMediaPromptTests(unittest.TestCase):
    """Tests for _sanitize_media_prompt: strip agent/tool scaffolding."""

    def test_plain_text_preserved(self):
        self.assertEqual(_sanitize_media_prompt("a cute cat"), "a cute cat")

    def test_empty_string(self):
        self.assertEqual(_sanitize_media_prompt(""), "")

    def test_none_returns_empty(self):
        # The guard `if not prompt` catches None as well as empty string.
        self.assertEqual(_sanitize_media_prompt(None), "")

    def test_whitespace_only(self):
        self.assertEqual(_sanitize_media_prompt("   "), "")

    def test_tool_block_removed(self):
        prompt = "draw a dog <tools>some tool defs</tools> in a park"
        result = _sanitize_media_prompt(prompt)
        self.assertNotIn("<tools>", result)
        self.assertIn("draw a dog", result)
        self.assertIn("in a park", result)

    def test_preamble_lines_stripped(self):
        preamble = "You are a function calling AI model.\nDraw a sunset"
        result = _sanitize_media_prompt(preamble)
        self.assertNotIn("function calling", result.lower())
        self.assertIn("Draw a sunset", result)

    def test_multiple_preamble_patterns_stripped(self):
        prompt = (
            "You are a function calling AI model.\n"
            "You are provided with function signatures within <tools> XML tags.\n"
            "You may call one or more functions to assist with the user query.\n"
            "Don't make assumptions about what values to plug into functions.\n"
            "Draw a mountain"
        )
        result = _sanitize_media_prompt(prompt)
        self.assertIn("Draw a mountain", result)
        # All preamble lines should be removed
        self.assertNotIn("function calling", result.lower())

    def test_excessive_newlines_collapsed(self):
        prompt = "line one\n\n\n\n\nline two"
        result = _sanitize_media_prompt(prompt)
        # Should not have three or more consecutive newlines
        self.assertNotIn("\n\n\n", result)
        self.assertIn("line one", result)
        self.assertIn("line two", result)

    def test_leading_and_trailing_whitespace_stripped(self):
        self.assertEqual(_sanitize_media_prompt("  hello  "), "hello")


# ---------------------------------------------------------------------------
# _build_gemini_error_payload
# ---------------------------------------------------------------------------
class BuildGeminiErrorPayloadTests(unittest.TestCase):
    """Tests for _build_gemini_error_payload: Gemini error envelope."""

    def test_basic_structure(self):
        payload = _build_gemini_error_payload(400, "bad request")
        self.assertIn("error", payload)
        error = payload["error"]
        self.assertEqual(error["code"], 400)
        self.assertEqual(error["message"], "bad request")

    def test_known_status_mapping_400(self):
        payload = _build_gemini_error_payload(400, "invalid")
        self.assertEqual(payload["error"]["status"], "INVALID_ARGUMENT")

    def test_known_status_mapping_401(self):
        payload = _build_gemini_error_payload(401, "unauth")
        self.assertEqual(payload["error"]["status"], "UNAUTHENTICATED")

    def test_known_status_mapping_403(self):
        payload = _build_gemini_error_payload(403, "denied")
        self.assertEqual(payload["error"]["status"], "PERMISSION_DENIED")

    def test_known_status_mapping_404(self):
        payload = _build_gemini_error_payload(404, "not found")
        self.assertEqual(payload["error"]["status"], "NOT_FOUND")

    def test_known_status_mapping_409(self):
        payload = _build_gemini_error_payload(409, "conflict")
        self.assertEqual(payload["error"]["status"], "ABORTED")

    def test_known_status_mapping_429(self):
        payload = _build_gemini_error_payload(429, "rate limited")
        self.assertEqual(payload["error"]["status"], "RESOURCE_EXHAUSTED")

    def test_known_status_mapping_500(self):
        payload = _build_gemini_error_payload(500, "internal error")
        self.assertEqual(payload["error"]["status"], "INTERNAL")

    def test_known_status_mapping_502(self):
        payload = _build_gemini_error_payload(502, "bad gw")
        self.assertEqual(payload["error"]["status"], "UNAVAILABLE")

    def test_known_status_mapping_503(self):
        payload = _build_gemini_error_payload(503, "unavail")
        self.assertEqual(payload["error"]["status"], "UNAVAILABLE")

    def test_known_status_mapping_504(self):
        payload = _build_gemini_error_payload(504, "timeout")
        self.assertEqual(payload["error"]["status"], "DEADLINE_EXCEEDED")

    def test_unknown_status_maps_to_unknown(self):
        payload = _build_gemini_error_payload(418, "teapot")
        self.assertEqual(payload["error"]["status"], "UNKNOWN")

    def test_stable_three_key_shape(self):
        payload = _build_gemini_error_payload(500, "err")
        error = payload["error"]
        self.assertEqual(set(error.keys()), {"code", "message", "status"})


# ---------------------------------------------------------------------------
# _normalize_finish_reason
# ---------------------------------------------------------------------------
class NormalizeFinishReasonTests(unittest.TestCase):
    """Tests for _normalize_finish_reason: OpenAI -> Gemini mapping."""

    def test_stop_maps_to_stop(self):
        self.assertEqual(_normalize_finish_reason("stop"), "STOP")

    def test_length_maps_to_max_tokens(self):
        self.assertEqual(_normalize_finish_reason("length"), "MAX_TOKENS")

    def test_content_filter_maps_to_safety(self):
        self.assertEqual(_normalize_finish_reason("content_filter"), "SAFETY")

    def test_unknown_value_maps_to_stop(self):
        self.assertEqual(_normalize_finish_reason("function_call"), "STOP")

    def test_none_returns_none(self):
        self.assertIsNone(_normalize_finish_reason(None))

    def test_empty_string_maps_to_stop(self):
        # Empty string is not in the mapping, so falls through to default "STOP".
        self.assertEqual(_normalize_finish_reason(""), "STOP")


# ---------------------------------------------------------------------------
# _extract_url_from_openai_payload
# ---------------------------------------------------------------------------
class ExtractUrlFromOpenaiPayloadTests(unittest.TestCase):
    """Tests for _extract_url_from_openai_payload: URL extraction logic."""

    def test_direct_url_field(self):
        payload = {"url": "https://example.com/image.png"}
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/image.png",
        )

    def test_direct_url_with_whitespace(self):
        payload = {"url": "  https://example.com/image.png  "}
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/image.png",
        )

    def test_markdown_image_in_choices(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "![img](https://example.com/photo.jpg)",
                    }
                }
            ]
        }
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/photo.jpg",
        )

    def test_html_video_in_choices(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": '<video src="https://example.com/clip.mp4" controls></video>',
                    }
                }
            ]
        }
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/clip.mp4",
        )

    def test_no_url_returns_none(self):
        payload = {"choices": [{"message": {"content": "just text"}}]}
        self.assertIsNone(_extract_url_from_openai_payload(payload))

    def test_empty_payload_returns_none(self):
        self.assertIsNone(_extract_url_from_openai_payload({}))

    def test_empty_choices_returns_none(self):
        self.assertIsNone(_extract_url_from_openai_payload({"choices": []}))

    def test_direct_url_preferred_over_content(self):
        payload = {
            "url": "https://direct.example.com/img.png",
            "choices": [
                {
                    "message": {
                        "content": "![img](https://markdown.example.com/img.png)",
                    }
                }
            ],
        }
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://direct.example.com/img.png",
        )

    def test_blank_direct_url_falls_through(self):
        payload = {
            "url": "   ",
            "choices": [
                {
                    "message": {
                        "content": "![img](https://example.com/fallback.png)",
                    }
                }
            ],
        }
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/fallback.png",
        )

    def test_non_string_url_field_falls_through(self):
        payload = {"url": 12345}
        self.assertIsNone(_extract_url_from_openai_payload(payload))

    def test_markdown_image_preferred_over_video(self):
        payload = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '![img](https://example.com/img.png)\n'
                            '<video src="https://example.com/vid.mp4"></video>'
                        ),
                    }
                }
            ]
        }
        self.assertEqual(
            _extract_url_from_openai_payload(payload),
            "https://example.com/img.png",
        )

    def test_result_fallback_when_no_choices(self):
        # When choices is missing but payload has "result" with a URL-like string,
        # _extract_openai_message_content returns payload.get("result", "").
        # But if that result is just plain text with no markdown/video, returns None.
        payload = {"result": "plain text result"}
        self.assertIsNone(_extract_url_from_openai_payload(payload))


# ---------------------------------------------------------------------------
# _detect_image_mime_type
# ---------------------------------------------------------------------------
class DetectImageMimeTypeTests(unittest.TestCase):
    """Tests for _detect_image_mime_type: byte-signature MIME detection."""

    def test_jpeg_signature(self):
        self.assertEqual(
            _detect_image_mime_type(b"\xff\xd8\xff\xe0some data"),
            "image/jpeg",
        )

    def test_png_signature(self):
        self.assertEqual(
            _detect_image_mime_type(b"\x89PNG\r\n\x1a\nsome data"),
            "image/png",
        )

    def test_gif87a_signature(self):
        self.assertEqual(
            _detect_image_mime_type(b"GIF87adata"),
            "image/gif",
        )

    def test_gif89a_signature(self):
        self.assertEqual(
            _detect_image_mime_type(b"GIF89adata"),
            "image/gif",
        )

    def test_webp_signature(self):
        # RIFF....WEBP
        data = b"RIFF\x00\x00\x00\x00WEBPmore data"
        self.assertEqual(_detect_image_mime_type(data), "image/webp")

    def test_unknown_bytes_returns_fallback(self):
        self.assertEqual(
            _detect_image_mime_type(b"\x00\x01\x02\x03"),
            "image/png",
        )

    def test_custom_fallback(self):
        self.assertEqual(
            _detect_image_mime_type(b"\x00\x01", fallback="image/unknown"),
            "image/unknown",
        )

    def test_empty_bytes_returns_fallback(self):
        self.assertEqual(
            _detect_image_mime_type(b""),
            "image/png",
        )

    def test_insufficient_bytes_for_webp(self):
        # Starts with RIFF but too short for WEBP check at offset 8:12
        data = b"RIFF\x00\x00"
        self.assertEqual(_detect_image_mime_type(data), "image/png")


# ---------------------------------------------------------------------------
# _coerce_gemini_contents
# ---------------------------------------------------------------------------
class CoerceGeminiContentsTests(unittest.TestCase):
    """Tests for _coerce_gemini_contents: normalize raw contents to GeminiContent list."""

    def test_none_returns_empty(self):
        self.assertEqual(_coerce_gemini_contents(None), [])

    def test_empty_list_returns_empty(self):
        self.assertEqual(_coerce_gemini_contents([]), [])

    def test_gemini_content_passthrough(self):
        content = GeminiContent(
            role="user",
            parts=[{"text": "hello"}],
        )
        result = _coerce_gemini_contents([content])
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], content)

    def test_dict_validated_to_gemini_content(self):
        raw = {"role": "user", "parts": [{"text": "hello"}]}
        result = _coerce_gemini_contents([raw])
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], GeminiContent)
        self.assertEqual(result[0].role, "user")
        self.assertEqual(result[0].parts[0].text, "hello")

    def test_role_preserved_model(self):
        raw = {"role": "model", "parts": [{"text": "response"}]}
        result = _coerce_gemini_contents([raw])
        self.assertEqual(result[0].role, "model")

    def test_multiple_items(self):
        raw_list = [
            {"role": "user", "parts": [{"text": "q1"}]},
            {"role": "model", "parts": [{"text": "a1"}]},
        ]
        result = _coerce_gemini_contents(raw_list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].role, "user")
        self.assertEqual(result[1].role, "model")

    def test_parts_preserved(self):
        raw = {"role": "user", "parts": [{"text": "first"}, {"text": "second"}]}
        result = _coerce_gemini_contents([raw])
        self.assertEqual(len(result[0].parts), 2)
        self.assertEqual(result[0].parts[0].text, "first")
        self.assertEqual(result[0].parts[1].text, "second")

    def test_none_role_accepted(self):
        # GeminiContent allows role=None
        raw = {"parts": [{"text": "no role"}]}
        result = _coerce_gemini_contents([raw])
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].role)


# ---------------------------------------------------------------------------
# _convert_openai_stream_chunk_to_gemini_event (async)
# ---------------------------------------------------------------------------
class ConvertOpenaiStreamChunkTests(unittest.TestCase):
    """Tests for _convert_openai_stream_chunk_to_gemini_event."""

    def _run(self, coro):
        """Run an async coroutine synchronously."""
        return asyncio.run(coro)

    def test_text_delta(self):
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "Hello world"},
                    "finish_reason": None,
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "test-model")
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("data: "))
        self.assertTrue(result.endswith("\n\n"))
        chunk = json.loads(result[6:].strip())
        self.assertIn("candidates", chunk)
        self.assertEqual(chunk["modelVersion"], "test-model")
        candidate = chunk["candidates"][0]
        self.assertEqual(candidate["index"], 0)
        self.assertIn("content", candidate)
        self.assertEqual(candidate["content"]["role"], "model")
        # Text should be in parts
        parts = candidate["content"]["parts"]
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["text"], "Hello world")

    def test_reasoning_content_preferred(self):
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "reasoning_content": "thinking...",
                        "content": "visible",
                    },
                    "finish_reason": None,
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "test-model")
        )
        self.assertIsNotNone(result)
        chunk = json.loads(result[6:].strip())
        parts = chunk["candidates"][0]["content"]["parts"]
        # reasoning_content takes precedence via `or` chain
        self.assertEqual(parts[0]["text"], "thinking...")

    def test_finish_reason_included(self):
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "done text"},
                    "finish_reason": "stop",
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "test-model")
        )
        self.assertIsNotNone(result)
        chunk = json.loads(result[6:].strip())
        candidate = chunk["candidates"][0]
        self.assertEqual(candidate["finishReason"], "STOP")

    def test_empty_chunk_returns_none(self):
        # choices present but with only an index and empty delta, no finish_reason
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": None,
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "test-model")
        )
        self.assertIsNone(result)

    def test_no_choices_returns_none(self):
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event({}, "test-model")
        )
        self.assertIsNone(result)

    def test_empty_choices_returns_none(self):
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(
                {"choices": []}, "test-model"
            )
        )
        self.assertIsNone(result)

    def test_gemini_event_shape(self):
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "x"},
                    "finish_reason": "stop",
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "my-model")
        )
        chunk = json.loads(result[6:].strip())
        # Top-level keys
        self.assertIn("candidates", chunk)
        self.assertIn("modelVersion", chunk)
        self.assertEqual(chunk["modelVersion"], "my-model")
        # Candidate keys
        candidate = chunk["candidates"][0]
        self.assertIn("index", candidate)
        self.assertIn("content", candidate)
        self.assertIn("finishReason", candidate)

    def test_no_done_sentinel_in_output(self):
        # The function should never emit the OpenAI [DONE] sentinel.
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "final"},
                    "finish_reason": "stop",
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "m")
        )
        self.assertIsNotNone(result)
        self.assertNotIn("[DONE]", result)

    def test_finish_reason_only_emits_event(self):
        # A chunk with finish_reason but no text should still emit an event
        # because finishReason adds a second key to the candidate dict.
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "test-model")
        )
        self.assertIsNotNone(result)
        chunk = json.loads(result[6:].strip())
        candidate = chunk["candidates"][0]
        self.assertEqual(candidate["finishReason"], "STOP")
        # No content key since there was no text
        self.assertNotIn("content", candidate)

    def test_content_filter_finish_reason(self):
        payload = {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": "blocked"},
                    "finish_reason": "content_filter",
                }
            ]
        }
        result = self._run(
            _convert_openai_stream_chunk_to_gemini_event(payload, "m")
        )
        chunk = json.loads(result[6:].strip())
        self.assertEqual(chunk["candidates"][0]["finishReason"], "SAFETY")


if __name__ == "__main__":
    unittest.main()
