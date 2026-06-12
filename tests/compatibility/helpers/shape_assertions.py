"""
Shallow shape assertion helpers for offline compatibility fixture tests.

All assertions are structural / compatibility-focused. They verify that
fixture data conforms to the expected OpenAI-compatible and Gemini-compatible
envelope shapes without inspecting content semantics or calling upstream
services.

Sprint 005B — Fixture Loader & Shape Assertions
Sprint 005D — Additional Static Fixture Assertions (FX-ON-002, FX-GN-001, FX-OS-002)
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
# FX-ON-002 — OpenAI image result response shape
# ---------------------------------------------------------------------------

def assert_openai_image_result_response_shape(data: Any) -> None:
    """Assert that *data* matches the OpenAI image result response shape.

    This extends the base chat completion response shape by additionally
    checking that the assistant message content contains a representative
    image markdown marker (e.g. ``![Generated Image](…)``).
    """
    # Base chat completion response envelope
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

    # Image-specific: content should contain a markdown image reference
    content = message["content"]
    assert isinstance(content, str), "choices[0].message.content must be a str"
    assert "![" in content and "](" in content, (
        "choices[0].message.content must contain a markdown image reference "
        "(e.g. '![Generated Image](...)')"
    )


# ---------------------------------------------------------------------------
# FX-GN-001 — Gemini generateContent request shape
# ---------------------------------------------------------------------------

def assert_gemini_generate_content_request_shape(data: Any) -> None:
    """Assert that *data* matches the Gemini generateContent request shape.

    Expected shape:
        {
            "contents": [
                {
                    "role": str,
                    "parts": [{"text": str}, ...]
                },
                ...
            ],
            ...
        }
    """
    assert isinstance(data, dict), "Request must be a dict"
    assert "contents" in data, 'Request must contain "contents" key'
    assert isinstance(data["contents"], list), '"contents" must be a list'
    assert len(data["contents"]) > 0, '"contents" must be a non-empty list'

    has_text_part = False
    for cidx, content in enumerate(data["contents"]):
        assert isinstance(content, dict), f"contents[{cidx}] must be a dict"
        assert "parts" in content, f'contents[{cidx}] missing "parts" key'
        assert isinstance(content["parts"], list), (
            f"contents[{cidx}].parts must be a list"
        )
        for pidx, part in enumerate(content["parts"]):
            assert isinstance(part, dict), (
                f"contents[{cidx}].parts[{pidx}] must be a dict"
            )
            if "text" in part:
                has_text_part = True

    assert has_text_part, (
        "At least one content item must have a parts entry with a \"text\" key"
    )


# ---------------------------------------------------------------------------
# FX-GN-001 — Gemini generateContent response shape
# ---------------------------------------------------------------------------

def assert_gemini_generate_content_response_shape(data: Any) -> None:
    """Assert that *data* matches the Gemini generateContent response shape.

    Expected shape:
        {
            "candidates": [
                {
                    "content": {
                        "role": str,
                        "parts": [{"text": str}, ...]
                    },
                    "finishReason": str,
                    "index": int
                },
                ...
            ],
            "modelVersion": str
        }
    """
    assert isinstance(data, dict), "Response must be a dict"
    assert "candidates" in data, 'Response must contain "candidates" key'
    assert isinstance(data["candidates"], list), '"candidates" must be a list'
    assert len(data["candidates"]) > 0, '"candidates" must be a non-empty list'

    has_text_part = False
    for cidx, candidate in enumerate(data["candidates"]):
        assert isinstance(candidate, dict), f"candidates[{cidx}] must be a dict"
        assert "content" in candidate, f'candidates[{cidx}] missing "content" key'

        content = candidate["content"]
        assert isinstance(content, dict), f"candidates[{cidx}].content must be a dict"
        assert "parts" in content, (
            f'candidates[{cidx}].content missing "parts" key'
        )
        assert isinstance(content["parts"], list), (
            f"candidates[{cidx}].content.parts must be a list"
        )

        for pidx, part in enumerate(content["parts"]):
            assert isinstance(part, dict), (
                f"candidates[{cidx}].content.parts[{pidx}] must be a dict"
            )
            if "text" in part:
                has_text_part = True

    assert has_text_part, (
        "At least one candidate must have a content.parts entry with a "
        "\"text\" key"
    )


# ---------------------------------------------------------------------------
# FX-OS-002 — OpenAI streaming reasoning_content / progress SSE shape
# ---------------------------------------------------------------------------

def assert_sse_reasoning_progress_shape(text: str) -> None:
    """Assert that *text* represents SSE chunks with reasoning_content progress.

    Expected shape:
        - At least one ``data:`` event exists (excluding ``data: [DONE]``)
        - Blank-line-separated SSE event framing
        - Each JSON payload has OpenAI streaming chunk shape:
          ``object == "chat.completion.chunk"``, ``choices[0].delta`` present
        - At least one chunk has ``choices[0].delta.reasoning_content``
        - ``data: [DONE]`` is NOT required (covered by FX-OS-003)
    """
    assert isinstance(text, str), "SSE fixture must be a string"
    assert len(text.strip()) > 0, "SSE fixture must not be empty"

    # Must contain at least one data: event
    lines = text.splitlines()
    data_lines = [ln for ln in lines if ln.startswith("data:")]
    assert len(data_lines) >= 1, "SSE fixture must have at least one data: event"

    # Blank-line-separated SSE framing
    assert "\n\n" in text, (
        "SSE fixture must use blank-line-separated event framing (\\n\\n)"
    )

    # Parse JSON payloads from data: lines (skip [DONE] sentinel if present)
    import json as _json

    parsed_chunks: list[Any] = []
    for ln in data_lines:
        payload_str = ln[len("data:"):].strip()
        if payload_str == "[DONE]":
            continue
        try:
            parsed_chunks.append(_json.loads(payload_str))
        except _json.JSONDecodeError:
            # Non-JSON data lines are ignored for shape purposes
            pass

    assert len(parsed_chunks) >= 1, (
        "SSE fixture must contain at least one parseable JSON chunk"
    )

    # Validate OpenAI streaming chunk shape on each parsed chunk
    has_reasoning_content = False
    for idx, chunk in enumerate(parsed_chunks):
        assert isinstance(chunk, dict), f"chunk[{idx}] must be a dict"
        assert chunk.get("object") == "chat.completion.chunk", (
            f'chunk[{idx}].object must be "chat.completion.chunk"'
        )
        assert "choices" in chunk, f'chunk[{idx}] missing "choices" key'
        assert isinstance(chunk["choices"], list), (
            f"chunk[{idx}].choices must be a list"
        )
        assert len(chunk["choices"]) > 0, (
            f"chunk[{idx}].choices must be a non-empty list"
        )

        first_choice = chunk["choices"][0]
        assert isinstance(first_choice, dict), (
            f"chunk[{idx}].choices[0] must be a dict"
        )
        assert "delta" in first_choice, (
            f'chunk[{idx}].choices[0] missing "delta" key'
        )

        delta = first_choice["delta"]
        assert isinstance(delta, dict), (
            f"chunk[{idx}].choices[0].delta must be a dict"
        )
        if "reasoning_content" in delta:
            has_reasoning_content = True

    assert has_reasoning_content, (
        "At least one chunk must have choices[0].delta.reasoning_content"
    )


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
