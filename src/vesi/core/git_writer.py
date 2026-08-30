"""Git object writer - writes Git objects for export.

Creates proper .git directory structure with loose objects.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
import zlib
from pathlib import Path
from dataclasses import dataclass


class GitWriter:
    """Writes Git objects to a .git directory."""

    def __init__(self, git_dir: Path) -> None:
        self.git_dir = git_dir
        self.objects_dir = git_dir / "objects"
        self.refs_dir = git_dir / "refs"
        self.heads_dir = self.refs_dir / "heads"
        self.tags_dir = self.refs_dir / "tags"

    def init(self) -> None:
        """Initialize .git directory structure."""
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.refs_dir.mkdir(parents=True, exist_ok=True)
        self.heads_dir.mkdir(parents=True, exist_ok=True)
        self.tags_dir.mkdir(parents=True, exist_ok=True)
        (self.git_dir / "info").mkdir(exist_ok=True)
        (self.git_dir / "hooks").mkdir(exist_ok=True)

    def write_blob(self, content: bytes) -> str:
        """Write a blob object. Returns the hash."""
        header = f"blob {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_object(hash_id, store)
        return hash_id

    def write_tree(self, entries: list[tuple[str, int, str]]) -> str:
        """Write a tree object.

        Args:
            entries: List of (name, mode, hash) tuples.

        Returns the tree hash.
        """
        content = b""
        for name, mode, hash_id in sorted(entries, key=lambda x: x[0]):
            # Mode as decimal string
            mode_str = f"{mode:o}".encode()
            # Name as bytes
            name_bytes = name.encode("utf-8")
            # Hash as 20 bytes
            hash_bytes = bytes.fromhex(hash_id)

            content += mode_str + b" " + name_bytes + b"\x00" + hash_bytes

        header = f"tree {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_object(hash_id, store)
        return hash_id

    def write_commit(
        self,
        tree_hash: str,
        parent_hashes: list[str] | None = None,
        author: str = "",
        author_email: str = "",
        author_timestamp: int = 0,
        committer: str = "",
        committer_email: str = "",
        committer_timestamp: int = 0,
        message: str = "",
    ) -> str:
        """Write a commit object.

        Returns the commit hash.
        """
        if parent_hashes is None:
            parent_hashes = []

        if not author_timestamp:
            author_timestamp = int(time.time())
        if not committer_timestamp:
            committer_timestamp = int(time.time())

        # Format timezone offset
        tz_offset = "+0000"
        tz_seconds = 0
        tz_str = f"{'+' if tz_seconds >= 0 else '-'}{abs(tz_seconds) // 3600:02}{(abs(tz_seconds) % 3600) // 60:02}"

        # Build commit content
        lines = [f"tree {tree_hash}"]

        for parent in parent_hashes:
            lines.append(f"parent {parent}")

        lines.append(f"author {author} <{author_email}> {author_timestamp} {tz_str}")
        lines.append(f"committer {committer} <{committer_email}> {committer_timestamp} {tz_str}")
        lines.append("")
        lines.append(message)

        content = "\n".join(lines).encode("utf-8")

        header = f"commit {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_object(hash_id, store)
        return hash_id

    def write_tag(
        self,
        tag_name: str,
        target_hash: str,
        tagger: str = "",
        tagger_email: str = "",
        timestamp: int = 0,
        message: str = "",
    ) -> str:
        """Write an annotated tag object.

        Returns the tag hash.
        """
        if not timestamp:
            timestamp = int(time.time())

        tz_str = "+0000"

        lines = [
            f"object {target_hash}",
            f"type commit",
            f"tag {tag_name}",
            f"tagger {tagger} <{tagger_email}> {timestamp} {tz_str}",
            "",
            message,
        ]

        content = "\n".join(lines).encode("utf-8")

        header = f"tag {len(content)}\x00".encode()
        store = header + content
        hash_id = hashlib.sha1(store).hexdigest()

        self._write_object(hash_id, store)
        return hash_id

    def set_head(self, ref: str, symbolic: bool = True) -> None:
        """Set HEAD reference.

        Args:
            ref: Branch name or commit hash
            symbolic: If True, write as symbolic ref; if False, write as hash
        """
        head_file = self.git_dir / "HEAD"

        if symbolic:
            head_file.write_text(f"ref: refs/heads/{ref}\n", encoding="utf-8")
        else:
            head_file.write_text(f"{ref}\n", encoding="utf-8")

    def set_branch(self, branch_name: str, commit_hash: str) -> None:
        """Set a branch reference."""
        branch_file = self.heads_dir / branch_name
        branch_file.parent.mkdir(parents=True, exist_ok=True)
        branch_file.write_text(f"{commit_hash}\n", encoding="utf-8")

    def set_tag(self, tag_name: str, commit_hash: str) -> None:
        """Set a lightweight tag reference."""
        tag_file = self.tags_dir / tag_name
        tag_file.write_text(f"{commit_hash}\n", encoding="utf-8")

    def write_description(self, description: str) -> None:
        """Write repository description."""
        desc_file = self.git_dir / "description"
        desc_file.write_text(description, encoding="utf-8")

    def write_config(self, bare: bool = False) -> None:
        """Write default .git/config."""
        config_content = f"""[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = {str(bare).lower()}
\tlogallrefupdates = true
"""
        config_file = self.git_dir / "config"
        config_file.write_text(config_content, encoding="utf-8")

    def write_exclude(self, patterns: list[str] | None = None) -> None:
        """Write .git/info/exclude."""
        default_patterns = [
            "# Git ignore patterns",
            "*.pyc",
            "__pycache__/",
            ".env",
            "*.egg-info/",
            "dist/",
            "build/",
        ]

        if patterns:
            default_patterns.extend(patterns)

        exclude_file = self.git_dir / "info" / "exclude"
        exclude_file.write_text("\n".join(default_patterns) + "\n", encoding="utf-8")

    def write_pack(self, objects: list[tuple[str, bytes, str]]) -> str:
        """Write objects to a pack file.

        Args:
            objects: List of (type, data, hash) tuples.

        Returns pack hash.
        """
        # Create pack file
        pack_name = hashlib.sha1(b"pack").hexdigest()[:16]
        pack_path = self.objects_dir / "pack" / f"pack-{pack_name}.pack"
        pack_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pack_path, "wb") as f:
            # Pack header
            f.write(b"PACK")
            f.write(struct.pack(">I", 2))  # Version 2
            f.write(struct.pack(">I", len(objects)))

            # Write each object
            for obj_type, data, hash_id in objects:
                type_map = {"commit": 1, "tree": 2, "blob": 3, "tag": 4}
                obj_type_num = type_map.get(obj_type, 3)

                # Encode header
                size = len(data)
                byte = (obj_type_num << 4) | (size & 0x7F)
                size >>= 7

                header = bytearray()
                while size > 0:
                    header.append(byte | 0x80)
                    byte = size & 0x7F
                    size >>= 7
                header.append(byte)

                f.write(bytes(header))

                # Compress and write data
                compressed = zlib.compress(data, level=6)
                f.write(compressed)

        # Write index
        self._write_pack_index(pack_path, objects)

        return pack_name

    def _write_pack_index(
        self,
        pack_path: Path,
        objects: list[tuple[str, bytes, str]],
    ) -> None:
        """Write pack index file."""
        idx_path = pack_path.with_suffix(".idx")

        # Sort objects by hash
        sorted_objects = sorted(objects, key=lambda x: x[2])

        with open(idx_path, "wb") as f:
            # Fanout table
            fanout = [0] * 256
            for _, _, hash_id in sorted_objects:
                byte_val = int(hash_id[:2], 16)
                fanout[byte_val] += 1

            for i in range(1, 256):
                fanout[i] += fanout[i - 1]

            for entry in fanout:
                f.write(struct.pack(">I", entry))

            # Hash table
            for _, _, hash_id in sorted_objects:
                f.write(bytes.fromhex(hash_id))

            # Offset table (simplified)
            offset = 0
            for obj_type, data, hash_id in sorted_objects:
                # Estimate offset (simplified)
                f.write(struct.pack(">I", offset))
                offset += len(data) + 100  # Approximate

            # Pack checksum
            pack_data = pack_path.read_bytes()
            pack_checksum = hashlib.sha1(pack_data).digest()
            f.write(pack_checksum)

    def _write_object(self, hash_id: str, data: bytes) -> None:
        """Write an object to loose storage."""
        obj_dir = self.objects_dir / hash_id[:2]
        obj_dir.mkdir(parents=True, exist_ok=True)

        obj_path = obj_dir / hash_id[2:]

        # Write compressed
        compressed = zlib.compress(data)

        fd, tmp_path = tempfile.mkstemp(dir=str(self.objects_dir), prefix=".tmp_")
        try:
            os.write(fd, compressed)
            os.fsync(fd)
            os.close(fd)
            os.replace(tmp_path, str(obj_path))
        except BaseException:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
