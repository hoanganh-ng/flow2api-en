"""
Fixture loader for offline compatibility fixture tests.

Loads JSON and text fixtures from tests/fixtures/ using only the standard
library. Does not import runtime application modules.

Sprint 005B — Fixture Loader & Shape Assertions
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _fixtures_root() -> Path:
    """Return the absolute path to the tests/fixtures directory.

    Resolution strategy (robust regardless of cwd):
      1. Walk up from this file to find the repository root (contains src/).
      2. Append tests/fixtures.
    """
    current = Path(__file__).resolve()
    for ancestor in current.parents:
        if (ancestor / "src").is_dir() and (ancestor / "tests").is_dir():
            return ancestor / "tests" / "fixtures"
    # Fallback: relative to this file (tests/compatibility/helpers -> tests/fixtures)
    return Path(__file__).resolve().parent.parent.parent / "fixtures"


FIXTURES_ROOT = _fixtures_root()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_json(relative_path: str) -> Any:
    """Load and parse a JSON fixture file.

    Args:
        relative_path: path relative to tests/fixtures/, e.g.
            "generation/model-list/openai-model-list.json"

    Returns:
        Parsed JSON (dict, list, etc.).

    Raises:
        FileNotFoundError: if the fixture file does not exist.
        json.JSONDecodeError: if the file is not valid JSON.
    """
    path = FIXTURES_ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_text(relative_path: str) -> str:
    """Load a text fixture file as a string.

    Args:
        relative_path: path relative to tests/fixtures/, e.g.
            "generation/openai-streaming/done-termination.sse.txt"

    Returns:
        File contents as str.

    Raises:
        FileNotFoundError: if the fixture file does not exist.
    """
    path = FIXTURES_ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return fh.read()


def fixture_path(relative_path: str) -> Path:
    """Return the absolute Path for a fixture file (without loading it).

    Useful when tests need to inspect file metadata or pass a path to
    another utility.
    """
    path = FIXTURES_ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path
