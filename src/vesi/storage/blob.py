"""Blob storage - stores and retrieves file content."""

from __future__ import annotations

from pathlib import Path

from vesi.hashing import hash_file
from vesi.storage.objects import ObjectStore


class BlobStore:
    """Stores file content as blobs in the object store."""

    def __init__(self, object_store: ObjectStore) -> None:
        self.objects = object_store

    def save_file(self, path: Path) -> str:
        """Save a file's content as a blob. Returns the hash."""
        content = path.read_bytes()
        return self.objects.save_blob(content)

    def load_content(self, hash_id: str) -> bytes:
        """Load blob content by hash."""
        return self.objects.load_blob(hash_id)

    def file_hash(self, path: Path) -> str:
        """Compute hash of a file without saving it."""
        return hash_file(path)
