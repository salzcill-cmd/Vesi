"""Git object parser - reads Git objects from .git repositories.

Supports:
- Loose objects (.git/objects/xx/xxxx)
- Packed objects (.git/objects/pack/pack-xxx.pack)
- Blobs, trees, commits
- Reference parsing (HEAD, branches, tags)
"""

from __future__ import annotations

import zlib
import struct
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class GitObject:
    """A parsed Git object."""

    obj_type: str  # "blob", "tree", "commit", "tag"
    data: bytes
    hash_id: str = ""

    def __post_init__(self):
        if not self.hash_id:
            self.hash_id = hashlib.sha1(self.data).hexdigest()


@dataclass
class GitBlob:
    """A Git blob (file content)."""

    content: bytes
    hash_id: str = ""


@dataclass
class GitTreeEntry:
    """A single entry in a Git tree."""

    mode: int
    name: str
    hash_id: str

    @property
    def is_blob(self) -> bool:
        # Git stores mode as decimal int: 100644 (regular), 100755 (executable)
        return self.mode in (33188, 33261, 100644, 100755)

    @property
    def is_tree(self) -> bool:
        # Git stores tree mode as 40000 (decimal)
        return self.mode == 40000 or self.mode == 0o040000


@dataclass
class GitTree:
    """A Git tree (directory structure)."""

    entries: list[GitTreeEntry] = field(default_factory=list)
    hash_id: str = ""

    def get_entry(self, name: str) -> GitTreeEntry | None:
        """Find entry by name."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def get_blob_entries(self) -> list[GitTreeEntry]:
        """Get only blob (file) entries."""
        return [e for e in self.entries if e.is_blob]

    def get_tree_entries(self) -> list[GitTreeEntry]:
        """Get only tree (directory) entries."""
        return [e for e in self.entries if e.is_tree]


@dataclass
class GitCommit:
    """A Git commit object."""

    tree_hash: str
    parent_hashes: list[str] = field(default_factory=list)
    author: str = ""
    author_email: str = ""
    author_timestamp: str = ""
    committer: str = ""
    committer_email: str = ""
    committer_timestamp: str = ""
    message: str = ""
    hash_id: str = ""

    @property
    def is_merge(self) -> bool:
        return len(self.parent_hashes) > 1


@dataclass
class GitRef:
    """A Git reference (branch, tag, etc.)."""

    name: str
    target: str  # commit hash or symbolic ref
    ref_type: str = "branch"  # branch, tag, symbolic


class GitParser:
    """Parses Git objects from a .git repository."""

    def __init__(self, git_dir: Path) -> None:
        self.git_dir = git_dir
        self.objects_dir = git_dir / "objects"
        self.refs_dir = git_dir / "refs"
        self.packs_dir = self.objects_dir / "pack"

    def has_git_repo(self) -> bool:
        """Check if path contains a .git repository."""
        return (self.git_dir / "HEAD").is_file()

    def read_object(self, hash_id: str) -> GitObject | None:
        """Read a Git object by hash.

        Tries loose objects first, then packed objects.
        """
        # Try loose object
        loose_path = self.objects_dir / hash_id[:2] / hash_id[2:]
        if loose_path.is_file():
            return self._read_loose_object(loose_path, hash_id)

        # Try packed objects
        for pack_path in self.packs_dir.glob("pack-*.pack"):
            obj = self._read_packed_object(pack_path, hash_id)
            if obj:
                return obj

        return None

    def _read_loose_object(self, path: Path, hash_id: str) -> GitObject | None:
        """Read a loose Git object."""
        try:
            compressed = path.read_bytes()
            data = zlib.decompress(compressed)

            # Parse header: "type size\0data"
            null_idx = data.index(b"\x00")
            header = data[:null_idx].decode("utf-8")
            obj_type, size = header.split(" ", 1)

            content = data[null_idx + 1:]

            return GitObject(
                obj_type=obj_type,
                data=content,
                hash_id=hash_id,
            )
        except (zlib.error, FileNotFoundError, ValueError):
            return None

    def _read_packed_object(self, pack_path: Path, hash_id: str) -> GitObject | None:
        """Read an object from a pack file."""
        idx_path = pack_path.with_suffix(".idx")
        if not idx_path.is_file():
            return None

        try:
            offset = self._lookup_in_pack_index(idx_path, hash_id)
            if offset is None:
                return None

            with open(pack_path, "rb") as f:
                f.seek(offset)
                return self._read_pack_object(f, hash_id)
        except Exception:
            return None

    def _lookup_in_pack_index(self, idx_path: Path, hash_id: str) -> int | None:
        """Look up object offset in pack index."""
        with open(idx_path, "rb") as f:
            # Read fanout table
            fanout = []
            for _ in range(256):
                fanout.append(struct.unpack(">I", f.read(4))[0])

            # Find the range for this hash's first byte
            first_byte = int(hash_id[:2], 16)
            start = fanout[first_byte - 1] if first_byte > 0 else 0
            end = fanout[first_byte]

            # Binary search in this range
            for _ in range(start, end):
                hash_bytes = f.read(20)
                found_hash = hash_bytes.hex()
                offset = struct.unpack(">I", f.read(4))[0]

                if found_hash == hash_id:
                    return offset

        return None

    def _read_pack_object(self, f, hash_id: str) -> GitObject | None:
        """Read a single object from pack file."""
        try:
            # Read type and size
            byte = f.read(1)[0]
            obj_type_num = (byte >> 4) & 0x07
            size = byte & 0x0F
            shift = 4

            while byte & 0x80:
                byte = f.read(1)[0]
                size |= (byte & 0x7F) << shift
                shift += 7

            type_map = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}
            obj_type = type_map.get(obj_type_num, "blob")

            # Decompress
            decompressor = zlib.decompressobj()
            data = b""
            while len(data) < size:
                chunk = f.read(min(4096, size - len(data)))
                if not chunk:
                    break
                try:
                    data += decompressor.decompress(chunk)
                except zlib.error:
                    break

            return GitObject(
                obj_type=obj_type,
                data=data[:size],
                hash_id=hash_id,
            )
        except Exception:
            return None

    def parse_blob(self, git_obj: GitObject) -> GitBlob:
        """Parse a blob object."""
        return GitBlob(
            content=git_obj.data,
            hash_id=git_obj.hash_id,
        )

    def parse_tree(self, git_obj: GitObject) -> GitTree:
        """Parse a tree object."""
        entries = []
        data = git_obj.data
        pos = 0

        while pos < len(data):
            # Parse mode (decimal number followed by space)
            space_idx = data.index(b" ", pos)
            mode = int(data[pos:space_idx].decode("utf-8"))

            # Parse name (until null byte)
            pos = space_idx + 1
            null_idx = data.index(b"\x00", pos)
            name = data[pos:null_idx].decode("utf-8")

            # Parse hash (20 bytes)
            pos = null_idx + 1
            hash_bytes = data[pos:pos + 20]
            hash_id = hash_bytes.hex()

            entries.append(GitTreeEntry(
                mode=mode,
                name=name,
                hash_id=hash_id,
            ))

            pos = null_idx + 21

        return GitTree(
            entries=entries,
            hash_id=git_obj.hash_id,
        )

    def parse_commit(self, git_obj: GitObject) -> GitCommit:
        """Parse a commit object."""
        content = git_obj.data.decode("utf-8", errors="replace")
        lines = content.split("\n")

        tree_hash = ""
        parent_hashes = []
        author = ""
        author_email = ""
        author_timestamp = ""
        committer = ""
        committer_email = ""
        committer_timestamp = ""
        message_lines = []
        in_message = False

        for line in lines:
            if in_message:
                message_lines.append(line)
                continue

            if line.startswith("tree "):
                tree_hash = line[5:]
            elif line.startswith("parent "):
                parent_hashes.append(line[7:])
            elif line.startswith("author "):
                # Format: "Author Name <email> timestamp tz"
                parts = line[7:].rsplit(" ", 2)
                if len(parts) >= 3:
                    name_email = parts[0]
                    author_timestamp = parts[1]
                    # Parse name and email
                    if "<" in name_email and ">" in name_email:
                        at_idx = name_email.index("<")
                        gt_idx = name_email.index(">")
                        author = name_email[:at_idx].strip()
                        author_email = name_email[at_idx + 1:gt_idx]
                    else:
                        author = name_email
            elif line.startswith("committer "):
                parts = line[10:].rsplit(" ", 2)
                if len(parts) >= 3:
                    name_email = parts[0]
                    committer_timestamp = parts[1]
                    if "<" in name_email and ">" in name_email:
                        at_idx = name_email.index("<")
                        gt_idx = name_email.index(">")
                        committer = name_email[:at_idx].strip()
                        committer_email = name_email[at_idx + 1:gt_idx]
                    else:
                        committer = name_email
            elif line == "":
                in_message = True

        return GitCommit(
            tree_hash=tree_hash,
            parent_hashes=parent_hashes,
            author=author or committer,
            author_email=author_email or committer_email,
            author_timestamp=author_timestamp,
            committer=committer,
            committer_email=committer_email,
            committer_timestamp=committer_timestamp,
            message="\n".join(message_lines).strip(),
            hash_id=git_obj.hash_id,
        )

    def read_refs(self) -> list[GitRef]:
        """Read all references from .git/refs."""
        refs = []

        # Read HEAD (symbolic ref)
        head_file = self.git_dir / "HEAD"
        if head_file.is_file():
            content = head_file.read_text(encoding="utf-8").strip()
            if content.startswith("ref: "):
                ref_path = content[5:]
                refs.append(GitRef(
                    name="HEAD",
                    target=ref_path,
                    ref_type="symbolic",
                ))
            else:
                # Detached HEAD
                refs.append(GitRef(
                    name="HEAD",
                    target=content,
                    ref_type="detached",
                ))

        # Read branch refs
        heads_dir = self.refs_dir / "heads"
        if heads_dir.is_dir():
            for ref_file in heads_dir.rglob("*"):
                if ref_file.is_file():
                    name = str(ref_file.relative_to(heads_dir))
                    target = ref_file.read_text(encoding="utf-8").strip()
                    refs.append(GitRef(
                        name=name,
                        target=target,
                        ref_type="branch",
                    ))

        # Read tag refs
        tags_dir = self.refs_dir / "tags"
        if tags_dir.is_dir():
            for ref_file in tags_dir.rglob("*"):
                if ref_file.is_file():
                    name = str(ref_file.relative_to(tags_dir))
                    target = ref_file.read_text(encoding="utf-8").strip()
                    refs.append(GitRef(
                        name=name,
                        target=target,
                        ref_type="tag",
                    ))

        return refs

    def resolve_head(self) -> str | None:
        """Resolve HEAD to a commit hash."""
        head_file = self.git_dir / "HEAD"
        if not head_file.is_file():
            return None

        content = head_file.read_text(encoding="utf-8").strip()
        if content.startswith("ref: "):
            ref_path = content[5:]
            ref_file = self.git_dir / ref_path
            if ref_file.is_file():
                return ref_file.read_text(encoding="utf-8").strip()
        else:
            return content

    def walk_commits(
        self,
        start_hash: str | None = None,
        max_count: int = 0,
    ) -> Iterator[GitCommit]:
        """Walk commit history from a starting point."""
        if start_hash is None:
            start_hash = self.resolve_head()

        if not start_hash:
            return

        visited = set()
        current = start_hash

        while current and current not in visited:
            if max_count > 0 and len(visited) >= max_count:
                break

            visited.add(current)

            git_obj = self.read_object(current)
            if git_obj is None or git_obj.obj_type != "commit":
                break

            commit = self.parse_commit(git_obj)
            yield commit

            # Follow first parent
            if commit.parent_hashes:
                current = commit.parent_hashes[0]
            else:
                break

    def get_tree_files(
        self,
        tree_hash: str,
        prefix: str = "",
    ) -> dict[str, str]:
        """Recursively get all files in a tree.

        Returns dict of {path: hash_id}.
        """
        git_obj = self.read_object(tree_hash)
        if git_obj is None or git_obj.obj_type != "tree":
            return {}

        tree = self.parse_tree(git_obj)
        files = {}

        for entry in tree.entries:
            full_path = f"{prefix}/{entry.name}" if prefix else entry.name

            if entry.is_blob:
                files[full_path] = entry.hash_id
            elif entry.is_tree:
                sub_files = self.get_tree_files(entry.hash_id, full_path)
                files.update(sub_files)

        return files

    def get_file_content(self, blob_hash: str) -> bytes | None:
        """Get file content from blob hash."""
        git_obj = self.read_object(blob_hash)
        if git_obj is None or git_obj.obj_type != "blob":
            return None
        return git_obj.data

    def count_objects(self) -> dict[str, int]:
        """Count objects by type."""
        counts = {"blob": 0, "tree": 0, "commit": 0, "tag": 0, "total": 0}

        # Count loose objects
        if self.objects_dir.is_dir():
            for prefix_dir in self.objects_dir.iterdir():
                if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                    for obj_file in prefix_dir.iterdir():
                        if obj_file.is_file():
                            counts["total"] += 1

        return counts
