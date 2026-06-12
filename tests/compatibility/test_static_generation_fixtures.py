"""
Offline static generation fixture shape tests.

Loads the Sprint 005A and Sprint 005C fixtures and verifies their
structural shape using the helpers in tests/compatibility/helpers/.
These tests:

  - Do NOT import the runtime FastAPI application.
  - Do NOT call upstream services.
  - Are fully offline and deterministic.
  - Use only the Python standard library.

Sprint 005B — Fixture Loader & Shape Assertions
Sprint 005D — Additional Static Fixture Assertions (FX-ON-002, FX-GN-001, FX-OS-002)

Run with:
    python -m unittest tests.compatibility.test_static_generation_fixtures
or:
    pytest tests/compatibility/test_static_generation_fixtures.py
"""

from __future__ import annotations

import unittest

from tests.compatibility.helpers.fixture_loader import load_json, load_text
from tests.compatibility.helpers.shape_assertions import (
    assert_gemini_generate_content_request_shape,
    assert_gemini_generate_content_response_shape,
    assert_openai_chat_completion_request_shape,
    assert_openai_chat_completion_response_shape,
    assert_openai_image_result_response_shape,
    assert_openai_model_list_shape,
    assert_sse_done_termination_shape,
    assert_sse_reasoning_progress_shape,
)


# ---------------------------------------------------------------------------
# Fixture paths (relative to tests/fixtures/)
# ---------------------------------------------------------------------------

MODEL_LIST_PATH = "generation/model-list/openai-model-list.json"
NON_STREAM_REQUEST_PATH = "generation/openai-non-streaming/text-basic-request.json"
NON_STREAM_RESPONSE_PATH = "generation/openai-non-streaming/text-basic-response.json"
SSE_DONE_PATH = "generation/openai-streaming/done-termination.sse.txt"

# Sprint 005C fixtures (assertions added in Sprint 005D)
IMAGE_RESULT_REQUEST_PATH = "generation/openai-non-streaming/image-result-request.json"
IMAGE_RESULT_RESPONSE_PATH = "generation/openai-non-streaming/image-result-response.json"
GEMINI_REQUEST_PATH = "generation/gemini-non-streaming/text-basic-request.json"
GEMINI_RESPONSE_PATH = "generation/gemini-non-streaming/text-basic-response.json"
SSE_REASONING_PATH = "generation/openai-streaming/reasoning-progress.sse.txt"


# ---------------------------------------------------------------------------
# Loading tests
# ---------------------------------------------------------------------------

class FixtureLoadingTests(unittest.TestCase):
    """Verify that all Sprint 005A and Sprint 005C fixture files load without errors."""

    def test_load_model_list_json(self):
        data = load_json(MODEL_LIST_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_non_streaming_request_json(self):
        data = load_json(NON_STREAM_REQUEST_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_non_streaming_response_json(self):
        data = load_json(NON_STREAM_RESPONSE_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_sse_done_termination_text(self):
        text = load_text(SSE_DONE_PATH)
        self.assertIsNotNone(text)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text.strip()), 0)

    # -- Sprint 005C fixtures (loading tests added in Sprint 005D) --

    def test_load_image_result_request_json(self):
        data = load_json(IMAGE_RESULT_REQUEST_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_image_result_response_json(self):
        data = load_json(IMAGE_RESULT_RESPONSE_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_gemini_request_json(self):
        data = load_json(GEMINI_REQUEST_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_gemini_response_json(self):
        data = load_json(GEMINI_RESPONSE_PATH)
        self.assertIsNotNone(data)
        self.assertIsInstance(data, dict)

    def test_load_sse_reasoning_progress_text(self):
        text = load_text(SSE_REASONING_PATH)
        self.assertIsNotNone(text)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text.strip()), 0)


# ---------------------------------------------------------------------------
# FX-ML-001 — GET /v1/models model list shape
# ---------------------------------------------------------------------------

class FXML001ModelListShapeTests(unittest.TestCase):
    """FX-ML-001: GET /v1/models response shape assertions."""

    def setUp(self):
        self.data = load_json(MODEL_LIST_PATH)

    def test_top_level_is_dict(self):
        self.assertIsInstance(self.data, dict)

    def test_object_is_list(self):
        self.assertEqual(self.data.get("object"), "list")

    def test_data_is_list(self):
        self.assertIn("data", self.data)
        self.assertIsInstance(self.data["data"], list)

    def test_each_model_item_has_required_fields(self):
        for idx, item in enumerate(self.data["data"]):
            with self.subTest(index=idx):
                self.assertIsInstance(item, dict)
                for field in ("id", "object", "created", "owned_by"):
                    self.assertIn(field, item, f"data[{idx}] missing field '{field}'")

    def test_full_shape_assertion(self):
        # Delegates to the reusable shape helper
        assert_openai_model_list_shape(self.data)


# ---------------------------------------------------------------------------
# FX-ON-001 — POST /v1/chat/completions non-streaming request shape
# ---------------------------------------------------------------------------

class FXON001RequestShapeTests(unittest.TestCase):
    """FX-ON-001: POST /v1/chat/completions request shape assertions."""

    def setUp(self):
        self.data = load_json(NON_STREAM_REQUEST_PATH)

    def test_model_exists(self):
        self.assertIn("model", self.data)

    def test_messages_is_non_empty_list(self):
        self.assertIn("messages", self.data)
        self.assertIsInstance(self.data["messages"], list)
        self.assertGreater(len(self.data["messages"]), 0)

    def test_each_message_has_role_and_content(self):
        for idx, msg in enumerate(self.data["messages"]):
            with self.subTest(index=idx):
                self.assertIn("role", msg)
                self.assertIn("content", msg)

    def test_stream_is_false(self):
        self.assertIn("stream", self.data)
        self.assertFalse(self.data["stream"])

    def test_full_shape_assertion(self):
        assert_openai_chat_completion_request_shape(self.data)


# ---------------------------------------------------------------------------
# FX-ON-001 — POST /v1/chat/completions non-streaming response shape
# ---------------------------------------------------------------------------

class FXON001ResponseShapeTests(unittest.TestCase):
    """FX-ON-001: POST /v1/chat/completions response shape assertions."""

    def setUp(self):
        self.data = load_json(NON_STREAM_RESPONSE_PATH)

    def test_top_level_required_fields(self):
        for field in ("id", "object", "created", "model", "choices", "usage"):
            with self.subTest(field=field):
                self.assertIn(field, self.data)

    def test_choices_is_non_empty_list(self):
        self.assertIsInstance(self.data["choices"], list)
        self.assertGreater(len(self.data["choices"]), 0)

    def test_first_choice_has_required_fields(self):
        first = self.data["choices"][0]
        for field in ("index", "message", "finish_reason"):
            with self.subTest(field=field):
                self.assertIn(field, first)

    def test_first_choice_message_has_role_and_content(self):
        message = self.data["choices"][0]["message"]
        self.assertIn("role", message)
        self.assertIn("content", message)

    def test_full_shape_assertion(self):
        assert_openai_chat_completion_response_shape(self.data)


# ---------------------------------------------------------------------------
# FX-OS-003 — SSE [DONE] termination shape
# ---------------------------------------------------------------------------

class FXOS003SSETerminationShapeTests(unittest.TestCase):
    """FX-OS-003: OpenAI streaming [DONE] termination shape assertions."""

    def setUp(self):
        self.text = load_text(SSE_DONE_PATH)

    def test_has_at_least_one_data_event(self):
        lines = self.text.splitlines()
        data_lines = [ln for ln in lines if ln.startswith("data:")]
        self.assertGreaterEqual(len(data_lines), 1)

    def test_blank_line_separated_sse_framing(self):
        self.assertIn("\n\n", self.text)

    def test_final_non_empty_line_is_done(self):
        lines = self.text.splitlines()
        non_empty = [ln for ln in lines if ln.strip()]
        self.assertGreater(len(non_empty), 0)
        self.assertEqual(non_empty[-1], "data: [DONE]")

    def test_full_shape_assertion(self):
        assert_sse_done_termination_shape(self.text)


# ---------------------------------------------------------------------------
# FX-ON-002 — POST /v1/chat/completions image result formatting
# ---------------------------------------------------------------------------

class FXON002ImageResultRequestShapeTests(unittest.TestCase):
    """FX-ON-002: Image result request shape assertions."""

    def setUp(self):
        self.data = load_json(IMAGE_RESULT_REQUEST_PATH)

    def test_model_exists(self):
        self.assertIn("model", self.data)

    def test_messages_is_non_empty_list(self):
        self.assertIn("messages", self.data)
        self.assertIsInstance(self.data["messages"], list)
        self.assertGreater(len(self.data["messages"]), 0)

    def test_stream_is_false(self):
        self.assertIn("stream", self.data)
        self.assertFalse(self.data["stream"])

    def test_full_shape_assertion(self):
        # Reuses the base chat completion request shape helper
        assert_openai_chat_completion_request_shape(self.data)


class FXON002ImageResultResponseShapeTests(unittest.TestCase):
    """FX-ON-002: Image result response shape assertions."""

    def setUp(self):
        self.data = load_json(IMAGE_RESULT_RESPONSE_PATH)

    def test_top_level_required_fields(self):
        for field in ("id", "object", "created", "model", "choices", "usage"):
            with self.subTest(field=field):
                self.assertIn(field, self.data)

    def test_choices_is_non_empty_list(self):
        self.assertIsInstance(self.data["choices"], list)
        self.assertGreater(len(self.data["choices"]), 0)

    def test_first_choice_has_required_fields(self):
        first = self.data["choices"][0]
        for field in ("index", "message", "finish_reason"):
            with self.subTest(field=field):
                self.assertIn(field, first)

    def test_assistant_message_content_contains_image_marker(self):
        message = self.data["choices"][0]["message"]
        self.assertIn("role", message)
        self.assertEqual(message["role"], "assistant")
        self.assertIn("content", message)
        content = message["content"]
        self.assertIsInstance(content, str)
        # Fixture uses markdown image reference: ![Generated Image](...)
        self.assertIn("![", content)
        self.assertIn("](", content)

    def test_does_not_verify_media_availability(self):
        """Image URL presence is structural only; no network check."""
        content = self.data["choices"][0]["message"]["content"]
        # Just verify it's a string with a URL-like pattern; no fetch
        self.assertIn("http", content)

    def test_full_image_result_shape_assertion(self):
        assert_openai_image_result_response_shape(self.data)


# ---------------------------------------------------------------------------
# FX-GN-001 — Gemini generateContent non-streaming request shape
# ---------------------------------------------------------------------------

class FXGN001GeminiRequestShapeTests(unittest.TestCase):
    """FX-GN-001: Gemini generateContent request shape assertions."""

    def setUp(self):
        self.data = load_json(GEMINI_REQUEST_PATH)

    def test_contents_is_non_empty_list(self):
        self.assertIn("contents", self.data)
        self.assertIsInstance(self.data["contents"], list)
        self.assertGreater(len(self.data["contents"]), 0)

    def test_content_items_have_parts(self):
        for idx, content in enumerate(self.data["contents"]):
            with self.subTest(index=idx):
                self.assertIsInstance(content, dict)
                self.assertIn("parts", content)
                self.assertIsInstance(content["parts"], list)

    def test_at_least_one_part_has_text(self):
        has_text = False
        for content in self.data["contents"]:
            for part in content.get("parts", []):
                if isinstance(part, dict) and "text" in part:
                    has_text = True
        self.assertTrue(has_text, "At least one part must have a 'text' key")

    def test_full_shape_assertion(self):
        assert_gemini_generate_content_request_shape(self.data)


# ---------------------------------------------------------------------------
# FX-GN-001 — Gemini generateContent non-streaming response shape
# ---------------------------------------------------------------------------

class FXGN001GeminiResponseShapeTests(unittest.TestCase):
    """FX-GN-001: Gemini generateContent response shape assertions."""

    def setUp(self):
        self.data = load_json(GEMINI_RESPONSE_PATH)

    def test_candidates_is_non_empty_list(self):
        self.assertIn("candidates", self.data)
        self.assertIsInstance(self.data["candidates"], list)
        self.assertGreater(len(self.data["candidates"]), 0)

    def test_candidate_content_has_parts(self):
        for idx, candidate in enumerate(self.data["candidates"]):
            with self.subTest(index=idx):
                self.assertIn("content", candidate)
                content = candidate["content"]
                self.assertIsInstance(content, dict)
                self.assertIn("parts", content)
                self.assertIsInstance(content["parts"], list)

    def test_at_least_one_response_part_has_text(self):
        has_text = False
        for candidate in self.data["candidates"]:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                if isinstance(part, dict) and "text" in part:
                    has_text = True
        self.assertTrue(
            has_text,
            "At least one candidate content part must have a 'text' key",
        )

    def test_full_shape_assertion(self):
        assert_gemini_generate_content_response_shape(self.data)


# ---------------------------------------------------------------------------
# FX-OS-002 — OpenAI streaming reasoning_content / progress SSE shape
# ---------------------------------------------------------------------------

class FXOS002SSEReasoningProgressShapeTests(unittest.TestCase):
    """FX-OS-002: OpenAI streaming reasoning_content progress shape assertions."""

    def setUp(self):
        self.text = load_text(SSE_REASONING_PATH)

    def test_has_at_least_one_data_event(self):
        lines = self.text.splitlines()
        data_lines = [ln for ln in lines if ln.startswith("data:")]
        self.assertGreaterEqual(len(data_lines), 1)

    def test_blank_line_separated_sse_framing(self):
        self.assertIn("\n\n", self.text)

    def test_parseable_json_payload(self):
        """At least one data: line must contain parseable JSON."""
        import json

        lines = self.text.splitlines()
        data_lines = [
            ln for ln in lines
            if ln.startswith("data:") and ln[len("data:"):].strip() != "[DONE]"
        ]
        parsed = []
        for ln in data_lines:
            payload = ln[len("data:"):].strip()
            try:
                parsed.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
        self.assertGreaterEqual(len(parsed), 1)

    def test_openai_streaming_chunk_shape(self):
        """Each JSON chunk has object=='chat.completion.chunk' and choices."""
        import json

        lines = self.text.splitlines()
        for ln in lines:
            if not ln.startswith("data:"):
                continue
            payload = ln[len("data:"):].strip()
            if payload == "[DONE]":
                continue
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            self.assertEqual(chunk.get("object"), "chat.completion.chunk")
            self.assertIn("choices", chunk)
            self.assertIsInstance(chunk["choices"], list)
            self.assertGreater(len(chunk["choices"]), 0)

    def test_choices_delta_has_reasoning_content(self):
        """At least one chunk must have delta.reasoning_content."""
        import json

        found = False
        lines = self.text.splitlines()
        for ln in lines:
            if not ln.startswith("data:"):
                continue
            payload = ln[len("data:"):].strip()
            if payload == "[DONE]":
                continue
            try:
                chunk = json.loads(payload)
            except json.JSONDecodeError:
                continue
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if "reasoning_content" in delta:
                found = True
                break
        self.assertTrue(
            found,
            "At least one chunk must have choices[0].delta.reasoning_content",
        )

    def test_does_not_require_done_sentinel(self):
        """FX-OS-003 covers [DONE] termination; this fixture need not include it."""
        # This test documents the intentional absence of [DONE] in the
        # reasoning progress fixture. No assertion failure if absent.
        lines = self.text.splitlines()
        non_empty = [ln for ln in lines if ln.strip()]
        # If [DONE] happens to be present that is acceptable, but not required
        self.assertIsInstance(non_empty, list)

    def test_full_shape_assertion(self):
        assert_sse_reasoning_progress_shape(self.text)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
