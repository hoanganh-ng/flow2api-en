"""
Shallow shape assertion helpers for offline compatibility fixture tests.

All assertions are structural / compatibility-focused. They verify that
fixture data conforms to the expected OpenAI-compatible envelope shapes
without inspecting content semantics or calling upstream services.

Sprint 005B — Fixture Loader & Shape Assertions
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# FX-ML-001 — OpenAI model list response shape
# ---------------------------------------------------------------------------

def assert_openai_model_list_shape(data: Any) -> None:
    """Assert that *data* matches the GET /v1/models response shape.

    Expected shape:
        {
            "object": "list",
            "data": [
                {"id": str, "object": "model", "created": int, "owned_by": str},
                ...
            ]
        }
    """
    assert isinstance(data, dict), "Model list response must be a dict"
    assert data.get("object") == "list", 'Top-level "object" must be "list"'
    assert "data" in data, 'Response must contain "data" key'
    assert isinstance(data["data"], list), '"data" must be a list'

    for idx, item in enumerate(data["data"]):
        assert isinstance(item, dict), f"data[{idx}] must be a dict"
        for field in ("id", "object", "created", "owned_by"):
            assert field in item, f'data[{idx}] missing required field "{field}"'
        assert isinstance(item["id"], str), f"data[{idx}].id must be a str"
        assert item["object"] == "model", (
            f'data[{idx}].object must be "model", got {item["object"]!r}'
        )


# ---------------------------------------------------------------------------
# FX-ON-001 — OpenAI chat completion request shape
# ---------------------------------------------------------------------------

def assert_openai_chat_completion_request_shape(data: Any) -> None:
    """Assert that *data* matches the POST /v1/chat/completions request shape.

    Expected shape:
        {
            "model": str,
            "messages": [{"role": str, "content": str}, ...],
            "stream": false
        }
    """
    assert isinstance(data, dict), "Request must be a dict"
    assert "model" in data, 'Request must contain "model" key'
    assert "messages" in data, 'Request must contain "messages" key'
    assert isinstance(data["messages"], list), '"messages" must be a list'
    assert len(data["messages"]) > 0, '"messages" must be a non-empty list'

    for idx, msg in enumerate(data["messages"]):
        assert isinstance(msg, dict), f"messages[{idx}] must be a dict"
        assert "role" in msg, f'messages[{idx}] missing "role"'
        assert "content" in msg, f'messages[{idx}] missing "content"'

    assert "stream" in data, 'Request must contain "stream" key'
    assert data["stream"] is False, '"stream" must be false for non-streaming request'


# ---------------------------------------------------------------------------
# FX-ON-001 — OpenAI chat completion response shape
# ---------------------------------------------------------------------------

def assert_openai_chat_completion_response_shape(data: Any) -> None:
    """Assert that *data* matches the POST /v1/chat/completions response shape.

    Expected shape:
        {
            "id": str,
            "object": "chat.completion",
            "created": int,
            "model": str,
            "choices": [
                {
                    "index": int,
                    "message": {"role": str, "content": str},
                    "finish_reason": str
                }
            ],
            "usage": {...}
        }
    """
    assert isinstance(data, dict), "Response must be a dict"

    for field in ("id", "object", "created", "model", "choices", "usage"):
        assert field in data, f'Response missing required field "{field}"'

    assert isinstance(data["choices"], list), '"choices" must be a list'
    assert len(data["choices"]) > 0, '"choices" must be a non-empty list'

    first_choice = data["choices"][0]
    assert isinstance(first_choice, dict), "choices[0] must be a dict"
    for field in ("index", "message", "finish_reason"):
        assert field in first_choice, f'choices[0] missing required field "{field}"'

    message = first_choice["message"]
    assert isinstance(message, dict), "choices[0].message must be a dict"
    assert "role" in message, 'choices[0].message missing "role"'
    assert "content" in message, 'choices[0].message missing "content"'


# ---------------------------------------------------------------------------
# FX-OS-003 — SSE [DONE] termination shape
# ---------------------------------------------------------------------------

def assert_sse_done_termination_shape(text: str) -> None:
    """Assert that *text* represents a valid SSE stream ending with [DONE].

    Expected shape:
        - At least one "data:" line present
        - Blank-line-separated SSE event framing (events separated by \\n\\n)
        - Final non-empty line is exactly "data: [DONE]"
    """
    assert isinstance(text, str), "SSE fixture must be a string"
    assert len(text.strip()) > 0, "SSE fixture must not be empty"

    # Must contain at least one data: event
    lines = text.splitlines()
    data_lines = [ln for ln in lines if ln.startswith("data:")]
    assert len(data_lines) >= 1, "SSE fixture must have at least one data: event"

    # Blank-line-separated SSE framing: the raw text must contain at least
    # one blank line (event boundary), indicating proper SSE framing.
    assert "\n\n" in text, (
        "SSE fixture must use blank-line-separated event framing (\\n\\n)"
    )

    # Final non-empty line must be exactly "data: [DONE]"
    non_empty_lines = [ln for ln in lines if ln.strip()]
    assert len(non_empty_lines) > 0, "SSE fixture has no non-empty lines"
    last_line = non_empty_lines[-1]
    assert last_line == "data: [DONE]", (
        f'Final non-empty line must be exactly "data: [DONE]", got {last_line!r}'
    )
