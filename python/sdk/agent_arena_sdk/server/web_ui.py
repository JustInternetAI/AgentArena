"""Web UI loader for the debug trace viewer.

Reads and serves the static HTML file so that the trace viewer is cleanly
separated from Python code.
"""

from __future__ import annotations

from pathlib import Path

_STATIC_DIR = Path(__file__).parent / "static"
_VIEWER_PATH = _STATIC_DIR / "debug_viewer.html"

# Cache the file contents after first read
_cached_html: str | None = None


def get_debug_viewer_html() -> str:
    """Return the HTML content of the debug trace viewer."""
    global _cached_html  # noqa: PLW0603
    if _cached_html is None:
        _cached_html = _VIEWER_PATH.read_text(encoding="utf-8")
    return _cached_html
