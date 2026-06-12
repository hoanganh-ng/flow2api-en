"""
Offline static generation fixture shape tests.

Loads the Sprint 005A fixtures and verifies their structural shape using
the helpers in tests/compatibility/helpers/. These tests:

  - Do NOT import the runtime FastAPI application.
  - Do NOT call upstream services.
  - Are fully offline and deterministic.
  - Use only the Python standard library.

Sprint 005B — Fixture Loader & Shape Assertions

Run with:
    python -m unittest tests.compatibility.test_static_generation_fixtures
or:
    pytest tests/compatibility/test_static_generation_fixtures.py
"""

from __future__ import annotations

import unittest

from tests.compatibility.helpers.fixture_loader import load_json, load_text
from tests.compatibility.helpers.shape_assertions import (
    assert_openai_chat_completion_request_shape,
    assert_openai_chat_completion_response_shape,
    assert_openai_model_list_shape,
    assert_sse_done_termination_shape,
)


# ---------------------------------------------------------------------------
# Fixture paths (relative to tests/fixtures/)
# ---------------------------------------------------------------------------

MODEL_LIST_PATH = "generation/model-list/openai-model-list.json"
NON_STREAM_REQUEST_PATH = "generation/openai-non-streaming/text-basic-request.json"
NON_STREAM_RESPONSE_PATH = "generation/openai-non-streaming/text-basic-response.json"
SSE_DONE_PATH = "generation/openai-streaming/done-termination.sse.txt"


# ---------------------------------------------------------------------------
# Loading tests
# ---------------------------------------------------------------------------

class FixtureLoadingTests(unittest.TestCase):
    """Verify that all Sprint 005A fixture files load without errors."""

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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
