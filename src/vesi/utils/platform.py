"""Cross-platform utilities."""

from __future__ import annotations

import os
import platform
import sys


def get_platform() -> str:
    """Return normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def is_windows() -> bool:
    return get_platform() == "windows"


def get_terminal_width() -> int:
    """Get terminal width with fallback."""
    try:
        return os.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        return 80


def supports_color() -> bool:
    """Check if terminal supports color output."""
    if os.environ.get("NO_COLOR") or os.environ.get("--no-color"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    if not sys.stdout.isatty():
        return False
    return True


def print_color(text: str, color: str, *, enabled: bool = True) -> None:
    """Print colored text if terminal supports it."""
    if not enabled or not supports_color():
        print(text)
        return

    colors = {
        "green": "\033[32m",
        "red": "\033[31m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    code = colors.get(color, "")
    reset = colors["reset"]
    print(f"{code}{text}{reset}")


def confirm(message: str, *, default: bool = False) -> bool:
    """Ask user for confirmation."""
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        response = input(f"{message}{suffix}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if not response:
        return default
    return response in ("y", "yes")
