"""Content-addressed object storage.

Objects are stored as files named by their SHA-256 hash.
Directory structure: .vesi/objects/<hash[0:2]>/<hash[2:]>
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from vesi.hashing import hash_content, short_hash


class ObjectStore:
    """Content-addressed object storage."""

    def __init__(self, objects_dir: Path) -> None:
        self.objects_dir = objects_dir
        self.objects_dir.mkdir(parents=True, exist_ok=True)

    def _object_path(self, hash_id: str) -> Path:
        """Get the filesystem path for an object hash."""
        prefix = hash_id[:2]
        suffix = hash_id[2:]
        return self.objects_dir / prefix / suffix

    def exists(self, hash_id: str) -> bool:
        """Check if an object exists in storage."""
        return self._object_path(hash_id).is_file()

    def save_object(self, data: bytes) -> str:
        """Save raw bytes as an object. Returns the hash.

        Uses atomic write: write to temp file, then rename.
        """
        hash_id = hash_content(data)
        if self.exists(hash_id):
            return hash_id

        obj_path = self._object_path(hash_id)
        obj_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.objects_dir),
            prefix=".tmp_",
        )
        try:
            os.write(fd, data)
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp_path, str(obj_path))
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None  # type: ignore[arg-type]
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return hash_id

    def load_object(self, hash_id: str) -> bytes:
        """Load raw bytes of an object by hash."""
        obj_path = self._object_path(hash_id)
        if not obj_path.is_file():
            raise FileNotFoundError(f"Object {hash_id} tidak ditemukan")
        return obj_path.read_bytes()

    def save_json(self, data: dict[str, Any]) -> str:
        """Save a JSON object. Returns the hash."""
        json_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self.save_object(json_bytes)

    def load_json(self, hash_id: str) -> dict[str, Any]:
        """Load a JSON object by hash."""
        data = self.load_object(hash_id)
        return json.loads(data.decode("utf-8"))

    def save_blob(self, content: bytes) -> str:
        """Save a blob (file content). Returns the hash."""
        return self.save_object(content)

    def load_blob(self, hash_id: str) -> bytes:
        """Load blob content."""
        return self.load_object(hash_id)

    def count_objects(self) -> int:
        """Count total objects in storage."""
        count = 0
        for prefix_dir in self.objects_dir.iterdir():
            if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                count += sum(1 for _ in prefix_dir.iterdir())
        return count

    def total_size(self) -> int:
        """Get total size of all objects in bytes."""
        total = 0
        for obj_file in self.objects_dir.rglob("*"):
            if obj_file.is_file():
                total += obj_file.stat().st_size
        return total

    def verify_integrity(self) -> list[str]:
        """Verify all objects have correct hashes.

        Returns list of error messages, empty if all OK.
        """
        errors: list[str] = []
        for obj_file in self.objects_dir.rglob("*"):
            if not obj_file.is_file():
                continue
            data = obj_file.read_bytes()
            computed = hash_content(data)
            # Reconstruct expected path
            expected_path = self._object_path(computed)
            if obj_file != expected_path:
                errors.append(
                    f"Object rusak: {short_hash(computed)} "
                    f"(file: {obj_file.relative_to(self.objects_dir)})"
                )
        return errors
