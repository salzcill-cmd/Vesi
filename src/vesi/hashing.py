"""SHA-256 hashing for content-addressed storage."""

from __future__ import annotations

import hashlib
from pathlib import Path


def hash_content(data: bytes) -> str:
    """Compute SHA-256 hash of bytes content."""
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def short_hash(full_hash: str, length: int = 7) -> str:
    """Return a shortened hash for display."""
    return full_hash[:length]
