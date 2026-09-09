"""Centralized logging setup for vesi.

Usage:
    setup_logging(debug=True)   # DEBUG output for development
    setup_logging(debug=False)  # Only warnings/errors (default)
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger("vesi")


def setup_logging(*, debug: bool = False) -> None:
    """Configure root logging for the vesi application.

    When debug is False (the default), only warnings and errors are shown.
    When debug is True, all messages including debug-level are visible.
    """
    level = logging.DEBUG if debug else logging.WARNING

    # (Re)configure a dedicated stderr handler so repeated calls
    # (e.g. debug toggled across runs) always reflect the latest level.
    root = logging.getLogger()
    try:
        root.handlers.clear()
    except Exception:
        root.handlers = []

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    fmt = logging.Formatter("%(name)s %(levelname)s: %(message)s")
    handler.setFormatter(fmt)
    root.addHandler(handler)

    root.setLevel(level)