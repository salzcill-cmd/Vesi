"""Git Bridge - Convert vesi objects to Git objects and push natively.

This module bridges the gap between vesi's internal storage format (SHA-256,
JSON-based trees/commits) and Git's wire format (SHA-1, binary trees,
zlib-compressed objects, packfiles).

Supports:
- Vesi blob → Git blob conversion
- Vesi tree → Git tree conversion (binary format)
- Vesi commit → Git commit conversion
- Pack file generation
- Smart HTTP push protocol with full negotiation
"""

from __future__ import annotations

import hashlib
import io
import struct
import time
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from vesi.hashing import short_hash
from vesi.storage.objects import ObjectStore
from vesi.storage.tree import Tree, TreeEntry


# ═══════════════════════════════════════════════════════════════════
# Git Object Types
# ═══════════════════════════════════════════════════════════════════

GIT_OBJ_COMMIT = 1
GIT_OBJ_TREE = 2
GIT_OBJ_BLOB = 3
GIT_OBJ_TAG = 4

# Git file modes
GIT_MODE_FILE = b"100644"
GIT_MODE_EXEC = b"100755"
GIT_MODE_DIR = b"40000"


# ═══════════════════════════════════════════════════════════════════
# Git Object Hashing (SHA-1 based, matching git's format)
# ═══════════════════════════════════════════════════════════════════

def git_hash_object(data: bytes, obj_type: str = "blob") -> str:
    """Compute Git SHA-1 hash for an object.

    Git objects are stored as: "<type> <size>\0<content>"
    """
    header = f"{obj_type} {len(data)}\0".encode()
    store = header + data
    return hashlib.sha1(store).hexdigest()


def git_hash_raw(raw: bytes) -> str:
    """Hash raw (already-formatted) git object bytes."""
    return hashlib.sha1(raw).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# Git Object Serialization
# ═══════════════════════════════════════════════════════════════════

def make_git_blob(data: bytes) -> tuple[str, bytes]:
    """Create a Git blob object. Returns (hash, raw_object_bytes)."""
    header = f"blob {len(data)}\0".encode()
    raw = header + data
    return git_hash_raw(raw), raw


def make_git_tree(entries: list[tuple[str, str, bytes]]) -> tuple[str, bytes]:
    """Create a Git tree object.

    Args:
        entries: List of (mode_str, name, sha1_bytes) where mode_str is like
                 "100644" or "40000" and sha1_bytes is the 20-byte SHA-1.

    Returns:
        (hash, raw_object_bytes)
    """
    tree_content = b""
    for mode_str, name, sha1_bytes in entries:
        # Git tree entry format: "<mode> <name>\0<20-byte-sha1>"
        tree_content += mode_str + b" " + name.encode() + b"\0" + sha1_bytes

    header = f"tree {len(tree_content)}\0".encode()
    raw = header + tree_content
    return git_hash_raw(raw), raw


def make_git_commit(
    tree_hash: str,
    parent_hashes: list[str],
    author_name: str,
    author_email: str,
    author_time: int,
    committer_name: str,
    committer_email: str,
    committer_time: int,
    message: str,
    timezone: str = "+0700",
) -> tuple[str, bytes]:
    """Create a Git commit object.

    Returns (hash, raw_object_bytes)
    """
    lines = []

    # Tree reference (40-char hex)
    lines.append(f"tree {tree_hash}")

    # Parent references
    for parent in parent_hashes:
        lines.append(f"parent {parent}")

    # Author
    author_date = f"{author_name} <{author_email}> {author_time} {timezone}"
    lines.append(f"author {author_date}")

    # Committer
    committer_date = f"{committer_name} <{committer_email}> {committer_time} {timezone}"
    lines.append(f"committer {committer_date}")

    # Empty line before message
    lines.append("")

    # Message
    lines.append(message)

    content = "\n".join(lines).encode("utf-8")
    header = f"commit {len(content)}\0".encode()
    raw = header + content
    return git_hash_raw(raw), raw


# ═══════════════════════════════════════════════════════════════════
# Vesi → Git Object Converter
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ConvertedObject:
    """A converted Git object ready for packing."""
    sha1: str
    raw: bytes
    obj_type: int  # GIT_OBJ_*
    size: int


class VesiToGitConverter:
    """Converts vesi storage objects to Git wire format objects."""

    def __init__(self, objects: ObjectStore) -> None:
        self.objects = objects
        # Cache: vesi_hash → ConvertedObject
        self._cache: dict[str, ConvertedObject] = {}
        # Mapping: vesi_hash → git_sha1
        self._hash_map: dict[str, str] = {}

    def convert_blob(self, vesi_hash: str) -> ConvertedObject:
        """Convert a vesi blob to a Git blob."""
        if vesi_hash in self._cache:
            return self._cache[vesi_hash]

        content = self.objects.load_blob(vesi_hash)
        sha1, raw = make_git_blob(content)
        obj = ConvertedObject(
            sha1=sha1, raw=raw,
            obj_type=GIT_OBJ_BLOB, size=len(content),
        )
        self._cache[vesi_hash] = obj
        self._hash_map[vesi_hash] = sha1
        return obj

    def convert_tree(self, vesi_hash: str) -> ConvertedObject:
        """Convert a vesi tree to a Git tree."""
        if vesi_hash in self._cache:
            return self._cache[vesi_hash]

        tree_data = self.objects.load_json(vesi_hash)
        tree = Tree.from_dict(tree_data)

        git_entries: list[tuple[str, str, bytes]] = []
        for entry in tree.entries:
            # First convert the child object
            if entry.type == "blob":
                child = self.convert_blob(entry.hash_id)
            elif entry.type == "tree":
                child = self.convert_tree(entry.hash_id)
            else:
                continue

            # Determine mode
            mode = GIT_MODE_FILE
            # Check if file is executable by name (simple heuristic)
            if entry.name.endswith((".sh", ".py", ".pl", ".rb", ".exe")):
                mode = GIT_MODE_EXEC
            elif entry.type == "tree":
                mode = GIT_MODE_DIR

            sha1_bytes = bytes.fromhex(child.sha1)
            git_entries.append((mode, entry.name, sha1_bytes))

        # Sort entries: directories first, then by name
        git_entries.sort(key=lambda e: (e[0] != GIT_MODE_DIR, e[1]))

        sha1, raw = make_git_tree(git_entries)
        obj = ConvertedObject(
            sha1=sha1, raw=raw,
            obj_type=GIT_OBJ_TREE, size=len(raw) - len(raw.split(b"\0", 1)[-1]),
        )
        self._cache[vesi_hash] = obj
        self._hash_map[vesi_hash] = sha1
        return obj

    def convert_commit(
        self,
        vesi_commit_data: dict[str, Any],
        parent_git_hashes: list[str] | None = None,
    ) -> ConvertedObject:
        """Convert a vesi commit to a Git commit.

        Args:
            vesi_commit_data: The vesi commit JSON data.
            parent_git_hashes: Pre-resolved parent Git SHA-1 hashes.
        """
        # Convert the tree
        tree_hash = vesi_commit_data.get("tree", "")
        if tree_hash and tree_hash not in self._hash_map:
            self.convert_tree(tree_hash)
        git_tree = self._hash_map.get(tree_hash, "0" * 40)

        # Extract author/committer info
        author = vesi_commit_data.get("author", "Unknown")
        message = vesi_commit_data.get("message", "")
        timestamp_raw = vesi_commit_data.get("timestamp", time.time())

        # Parse timestamp - handle both int and ISO format
        if isinstance(timestamp_raw, str):
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
                timestamp = int(dt.timestamp())
            except (ValueError, TypeError):
                timestamp = int(time.time())
        elif isinstance(timestamp_raw, (int, float)):
            timestamp = int(timestamp_raw)
        else:
            timestamp = int(time.time())

        # Parse author name/email
        if "<" in author and ">" in author:
            name = author.split("<")[0].strip()
            email = author.split("<")[1].split(">")[0].strip()
        else:
            name = author
            email = f"{author.lower().replace(' ', '.')}@vesi.local"

        parent_hashes = parent_git_hashes or []

        sha1, raw = make_git_commit(
            tree_hash=git_tree,
            parent_hashes=parent_hashes,
            author_name=name,
            author_email=email,
            author_time=int(timestamp),
            committer_name=name,
            committer_email=email,
            committer_time=int(timestamp),
            message=message,
        )

        obj = ConvertedObject(
            sha1=sha1, raw=raw,
            obj_type=GIT_OBJ_COMMIT, size=len(raw),
        )
        self._hash_map.get("commit", None)  # Not stored by vesi hash
        return obj

    def get_git_sha1(self, vesi_hash: str) -> str | None:
        """Get the Git SHA-1 for a vesi hash."""
        return self._hash_map.get(vesi_hash)


# ═══════════════════════════════════════════════════════════════════
# Pack File Generator
# ═══════════════════════════════════════════════════════════════════

# Pack file format constants
PACK_VERSION = 2
PACK_SIGNATURE = b"PACK"
IDX_FANOUT_RANGE = 256
IDX_SHA1_SIZE = 20
IDX_OFFSET_SIZE = 4
IDX_CRC_SIZE = 4

# Object type encoding in pack files
OBJ_TYPES = {
    GIT_OBJ_COMMIT: 1,
    GIT_OBJ_TREE: 2,
    GIT_OBJ_BLOB: 3,
    GIT_OBJ_TAG: 4,
}


def _encode_pack_size(size: int) -> bytes:
    """Encode a size using Git's variable-length encoding."""
    result = bytearray()
    while True:
        byte = size & 0x7F
        size >>= 7
        if size:
            byte |= 0x80
        result.append(byte)
        if not size:
            break
    return bytes(result)


def _encode_pack_offset(offset: int) -> bytes:
    """Encode an offset using Git's variable-length encoding."""
    return _encode_pack_size(offset)


def generate_packfile(objects: list[ConvertedObject]) -> bytes:
    """Generate a Git pack file from a list of converted objects.

    Pack format:
    - Header: PACK + version(4) + num_objects(4)
    - For each object: type+size header + zlib-compressed data
    - Checksum: SHA-1 of everything above
    """
    buf = io.BytesIO()

    # Pack header
    buf.write(PACK_SIGNATURE)
    buf.write(struct.pack(">I", PACK_VERSION))
    buf.write(struct.pack(">I", len(objects)))

    # Object data
    for obj in objects:
        obj_type = OBJ_TYPES.get(obj.obj_type, 3)  # Default to blob

        # Type and size encoding
        # First byte: type (3 bits) + size (4 bits) + more flag (1 bit)
        type_bits = obj_type & 0x07
        size = len(obj.raw)

        # Write variable-length type+size header
        first_byte = ((type_bits << 4) | (size & 0x0F))
        if size > 0x0F:
            first_byte |= 0x80
        buf.write(bytes([first_byte]))

        remaining_size = size >> 4
        while remaining_size > 0:
            byte = remaining_size & 0x7F
            remaining_size >>= 7
            if remaining_size:
                byte |= 0x80
            buf.write(bytes([byte]))

        # Compress and write the object data
        compressed = zlib.compress(obj.raw, level=6)
        buf.write(compressed)

    # Pack checksum (SHA-1 of everything written so far)
    pack_data = buf.getvalue()
    checksum = hashlib.sha1(pack_data).digest()
    buf.write(checksum)

    return buf.getvalue()


def generate_pack_index(objects: list[ConvertedObject]) -> bytes:
    """Generate a .idx file for the pack.

    Simplified version - writes a valid but minimal index.
    """
    buf = io.BytesIO()

    # Sort objects by SHA-1 for binary search
    sorted_objects = sorted(objects, key=lambda o: o.sha1)

    # Fanout table (256 entries)
    fanout = [0] * 256
    for i, obj in sorted_objects:
        byte = int(obj.sha1[:2], 16)
        fanout[byte] = i + 1

    # Write fanout table
    for count in fanout:
        buf.write(struct.pack(">I", count))

    # Write SHA-1 table
    for obj in sorted_objects:
        buf.write(bytes.fromhex(obj.sha1))

    # Write CRC table
    for obj in sorted_objects:
        crc = zlib.crc32(obj.raw) & 0xFFFFFFFF
        buf.write(struct.pack(">I", crc))

    # Write offset table (simplified - all fit in 4 bytes)
    offset = 8 + len(PACK_SIGNATURE)  # Header size
    for obj in sorted_objects:
        buf.write(struct.pack(">I", offset))
        offset += _pack_object_size(obj)

    # Write pack checksum (placeholder)
    buf.write(b"\x00" * 20)

    return buf.getvalue()


def _pack_object_size(obj: ConvertedObject) -> int:
    """Estimate the pack file size for a single object."""
    obj_type = OBJ_TYPES.get(obj.obj_type, 3)
    size = len(obj.raw)

    # Variable header size
    header_size = 1  # First byte at minimum
    temp = size >> 4
    while temp > 0:
        header_size += 1
        temp >>= 7

    # Compressed data (estimate)
    compressed = zlib.compress(obj.raw, level=6)

    return header_size + len(compressed)


# ═══════════════════════════════════════════════════════════════════
# Git Smart HTTP Protocol Client
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PushResult:
    """Result of a push operation."""
    success: bool
    message: str
    refs_updated: dict[str, tuple[str, str]] = field(default_factory=dict)
    # ref_name → (old_hash, new_hash)


class GitSmartHTTPPush:
    """Implements the Git smart HTTP push protocol.

    This is the real protocol that GitHub/GitLab/Bitbucket use.
    """

    def __init__(
        self,
        url: str,
        auth_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.auth_token = auth_token
        self.username = username
        self.password = password

    def _make_request(
        self,
        endpoint: str,
        data: bytes | None = None,
        content_type: str = "",
        method: str = "GET",
    ) -> tuple[int, bytes, dict[str, str]]:
        """Make an HTTP request with auth headers."""
        import urllib.request
        import urllib.error
        import base64

        url = f"{self.url}/{endpoint}"

        headers = {
            "User-Agent": "vesi/0.5.0",
            "Git-Protocol": "version=2",
        }

        if content_type:
            headers["Content-Type"] = content_type

        # Auth - GitHub requires Basic auth with x-access-token for smart HTTP
        if self.auth_token:
            credentials = base64.b64encode(
                f"x-access-token:{self.auth_token}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        elif self.username and self.password:
            credentials = base64.b64encode(
                f"{self.username}:{self.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        req = urllib.request.Request(url, data=data, method=method)
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as e:
            body = e.read() if e.fp else b""
            return e.code, body, dict(e.headers) if hasattr(e, 'headers') else {}
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}")

    def discover_refs(self) -> list[tuple[str, str]]:
        """Discover remote refs via smart HTTP.

        Returns list of (ref_name, sha1_hash) pairs.
        """
        status, body, _ = self._make_request(
            "info/refs?service=git-upload-pack",
            content_type="application/x-git-upload-pack-advertisement",
        )

        if status != 200:
            raise RuntimeError(f"Ref discovery failed (HTTP {status})")

        return self._parse_upload_pack_refs(body)

    def _parse_upload_pack_refs(self, data: bytes) -> list[tuple[str, str]]:
        """Parse the git-upload-pack advertisement."""
        refs = []
        lines = data.split(b"\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith(b"#") or line == b"0000":
                continue

            # Strip packet length prefix if present
            if len(line) > 4 and all(c in b"0123456789abcdef" for c in line[:4]):
                try:
                    pkt_len = int(line[:4], 16)
                    if pkt_len > 4:
                        line = line[4:pkt_len]
                    else:
                        continue
                except ValueError:
                    pass

            # Format: <40-char-sha1> <refname>
            if b" " in line:
                parts = line.split(b" ", 1)
                sha1_hex = parts[0].decode("ascii", errors="ignore").strip()
                ref_name = parts[1].decode("utf-8", errors="replace").strip()

                # Remove capabilities suffix
                if b"\0" in parts[1]:
                    ref_name = parts[1].split(b"\0")[0].decode("utf-8", errors="replace").strip()

                if len(sha1_hex) == 40 and all(c in "0123456789abcdef" for c in sha1_hex):
                    refs.append((ref_name, sha1_hex))

        return refs

    def negotiate_and_push(
        self,
        local_objects: list[ConvertedObject],
        ref_updates: dict[str, str],
        remote_refs: list[tuple[str, str]],
    ) -> PushResult:
        """Perform the full push negotiation and data transfer.

        Args:
            local_objects: All objects to send (converted from vesi).
            ref_updates: {ref_name: new_sha1_hex} - refs to update.
            remote_refs: Current remote refs from discovery.

        Returns:
            PushResult with success status.
        """
        remote_map = {name: sha for name, sha in remote_refs}

        # Build the command batch
        commands = []
        for ref_name, new_sha in ref_updates.items():
            old_sha = remote_map.get(ref_name, "0" * 40)
            commands.append(f"{old_sha} {new_sha} {ref_name}")

        if not commands:
            return PushResult(success=True, message="Tidak ada yang perlu di-push")

        # Build the ref-update request with capabilities
        report_status = b"report-status"
        delete_refs = b"delete-refs"
        side_band = b"side-band-64k"

        cap_list = b" ".join([report_status, delete_refs, side_band])

        # Packet format for the command batch
        request = io.BytesIO()

        # First command with capabilities
        first_cmd = f"{commands[0]} {cap_list.decode()}".encode()
        pkt = _make_packet(first_cmd)
        request.write(pkt)

        # Remaining commands
        for cmd in commands[1:]:
            request.write(_make_packet(cmd.encode()))

        # Flush packet
        request.write(b"0000")

        # Generate pack file with all objects
        pack_data = generate_packfile(local_objects)

        # Side-band format: 1 byte channel + data
        # Channel 1 = pack data, Channel 2 = progress, Channel 3 = error
        sideband_data = b"1" + pack_data

        request.write(sideband_data)

        # Send the request
        status, body, headers = self._make_request(
            "git-receive-pack",
            data=request.getvalue(),
            content_type="application/x-git-receive-pack-request",
            method="POST",
        )

        if status == 200:
            # Check for unpack ok
            if b"unpack ok" in body or b"ok" in body.lower():
                return PushResult(
                    success=True,
                    message="Push berhasil!",
                    refs_updated={
                        ref: (remote_map.get(ref, "0" * 40), new)
                        for ref, new in ref_updates.items()
                    },
                )
            else:
                # Parse error from side-band
                error_msg = self._parse_sideband_errors(body)
                return PushResult(
                    success=False,
                    message=f"Push ditolak: {error_msg or 'unknown error'}",
                )
        elif status == 401:
            return PushResult(success=False, message="Autentikasi gagal. Periksa token.")
        elif status == 403:
            return PushResult(success=False, message="Akses ditolak. Periksa permissions.")
        else:
            error_msg = body.decode("utf-8", errors="replace")[:200]
            return PushResult(
                success=False,
                message=f"Push gagal (HTTP {status}): {error_msg}",
            )

    def _parse_sideband_errors(self, data: bytes) -> str:
        """Extract error messages from side-band channel 3."""
        errors = []
        pos = 0
        while pos < len(data) - 5:
            # Check for packet header
            if pos + 4 <= len(data):
                try:
                    pkt_len = int(data[pos:pos+4], 16)
                    if pkt_len < 4:
                        break
                    # Skip packet length
                    pos += 4
                    # Read packet content
                    pkt_data = data[pos:pos+pkt_len-4]
                    pos += pkt_len - 4

                    # Check side-band channel
                    if pkt_data and pkt_data[0:1] == b"3":
                        errors.append(pkt_data[1:].decode("utf-8", errors="replace"))
                except (ValueError, UnicodeDecodeError):
                    break
            else:
                break

        return "\n".join(errors) if errors else ""


def _make_packet(data: bytes) -> bytes:
    """Create a Git packet-line.

    Format: 4-hex-digit length + data
    """
    pkt_len = len(data) + 4
    return f"{pkt_len:04x}".encode() + data


# ═══════════════════════════════════════════════════════════════════
# High-Level Push API
# ═══════════════════════════════════════════════════════════════════

def push_vesi_to_git(
    vesi_objects: ObjectStore,
    commit_hashes: list[str],
    ref_name: str,
    remote_url: str,
    auth_token: str | None = None,
    on_progress: Any = None,
) -> PushResult:
    """Push vesi commits to a Git remote using native protocol v2.

    This is the main entry point. It:
    1. Walks the vesi commit graph
    2. Converts all objects to Git format
    3. Generates pack files
    4. Pushes via smart HTTP protocol v2

    Args:
        vesi_objects: The vesi object store.
        commit_hashes: Commit hashes to push (newest first).
        ref_name: Target ref (e.g., "refs/heads/main").
        remote_url: Remote repository URL.
        auth_token: GitHub/GitLab personal access token.
        on_progress: Callback function(message, current, total).

    Returns:
        PushResult with success/failure details.
    """
    from vesi.remote.protocol_v2 import GitSmartHTTPClient

    converter = VesiToGitConverter(vesi_objects)
    all_git_objects: list[ConvertedObject] = []

    def _progress(msg: str, cur: int = 0, total: int = 0) -> None:
        if on_progress:
            on_progress(msg, cur, total)

    _progress(f"Mengkonversi {len(commit_hashes)} commits...")

    # Walk the commit graph (newest first)
    for i, commit_hash in enumerate(commit_hashes):
        _progress(f"  Commit {i+1}/{len(commit_hashes)}: {short_hash(commit_hash)}", i + 1, len(commit_hashes))

        try:
            commit_data = vesi_objects.load_json(commit_hash)
        except Exception:
            _progress(f"  ⚠ Commit {short_hash(commit_hash)} tidak ditemukan")
            continue

        # Convert tree
        tree_hash = commit_data.get("tree", "")
        if tree_hash:
            try:
                tree_obj = converter.convert_tree(tree_hash)
                all_git_objects.append(tree_obj)
            except Exception as e:
                _progress(f"  ⚠ Gagal konversi tree: {e}")
                continue

        # Convert commit without parents first
        try:
            git_commit = converter.convert_commit(commit_data, parent_git_hashes=[])
            all_git_objects.append(git_commit)
        except Exception as e:
            _progress(f"  ⚠ Gagal konversi commit: {e}")
            continue

    if not all_git_objects:
        return PushResult(success=False, message="Tidak ada objek untuk di-push")

    # Find the tip commit
    tip_commit_data = vesi_objects.load_json(commit_hashes[0]) if commit_hashes else None
    if not tip_commit_data:
        return PushResult(success=False, message="Tidak dapat membaca commit terakhir")

    # Re-convert tip commit
    tip_git = converter.convert_commit(tip_commit_data, parent_git_hashes=[])
    all_git_objects.append(tip_git)

    # Deduplicate
    seen = set()
    unique_objects = []
    for obj in all_git_objects:
        if obj.sha1 not in seen:
            seen.add(obj.sha1)
            unique_objects.append(obj)

    _progress(f"Total {len(unique_objects)} Git objects dikonversi")

    # Generate pack file
    _progress("Membuat pack file...")
    pack_data = generate_packfile(unique_objects)
    _progress(f"Pack file: {len(pack_data)} bytes")

    # Connect to remote via protocol v2
    _progress(f"Menghubungkan ke {remote_url}...")

    client = GitSmartHTTPClient(remote_url, auth_token=auth_token)

    try:
        remote_refs, caps = client.discover_refs()
        _progress(f"Remote memiliki {len(remote_refs)} refs")
        _progress(f"Server capabilities: {', '.join(caps[:5])}")
    except Exception as e:
        return PushResult(success=False, message=f"Gagal mengambil refs remote: {e}")

    # Push via protocol v2
    _progress("Mengirim objects...")
    result = client.push(
        pack_data=pack_data,
        ref_updates={ref_name: tip_git.sha1},
        remote_refs=remote_refs,
    )

    return result


# ═══════════════════════════════════════════════════════════════════
# CLI-Friendly Push via subprocess fallback
# ═══════════════════════════════════════════════════════════════════

def push_via_git_subprocess(
    repo_root: Path,
    remote: str = "origin",
    branch: str | None = None,
    force: bool = False,
    remote_url: str | None = None,
    auth_token: str | None = None,
    on_progress: Any = None,
) -> tuple[bool, str]:
    """Fallback: push using the system `git` command.

    Creates a temporary git repo from vesi data, pushes it, then cleans up.
    This handles the case where vesi repos don't have .git directory.
    """
    import subprocess
    import tempfile

    def _progress(msg: str) -> None:
        if on_progress:
            on_progress(msg, 0, 0)

    # Check if .git exists
    git_dir = repo_root / ".git"
    if git_dir.is_dir():
        # Normal git repo - push directly
        return _push_from_git_dir(repo_root, remote, branch, force, _progress)

    # Vesi repo (no .git) - create temp git repo and push
    _progress("Membuat temporary git repo untuk push...")

    # Get vesi info
    from vesi.repository.repository import Repository
    from vesi.core.snapshot import SnapshotManager
    from vesi.storage.tree import Tree
    from vesi.hashing import short_hash

    try:
        repo = Repository(repo_root)
    except Exception as e:
        return False, f"Gagal membaca vesi repo: {e}"

    head = repo.get_head_commit()
    if not head:
        return False, "Tidak ada commit untuk di-push"

    # Get remote URL from vesi config
    from vesi.remote.transport import RemoteConfig
    rc = RemoteConfig(repo_root)
    url = remote_url or rc.get_remote_url(remote)
    if not url:
        return False, f"Remote '{remote}' tidak ditemukan"

    if not branch:
        branch = repo.refs.get_active_branch() or "main"

    _progress(f"  Commit: {short_hash(head)}")
    _progress(f"  Remote: {url}")
    _progress(f"  Branch: {branch}")

    # Create temporary directory with git repo
    tmp_dir = Path(tempfile.mkdtemp(prefix="vesi_push_"))

    try:
        # Init git repo with main branch
        subprocess.run(["git", "init", "-b", branch], cwd=str(tmp_dir), capture_output=True, timeout=10)
        subprocess.run(
            ["git", "config", "user.name", "vesi"],
            cwd=str(tmp_dir), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "config", "user.email", "vesi@local"],
            cwd=str(tmp_dir), capture_output=True, timeout=10,
        )

        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", url],
            cwd=str(tmp_dir), capture_output=True, timeout=10,
        )

        # Set auth
        if auth_token:
            subprocess.run(
                ["git", "config", "http.extraHeader",
                 f"Authorization: basic {__import__('base64').b64encode(f'x-access-token:{auth_token}'.encode()).decode()}"],
                cwd=str(tmp_dir), capture_output=True, timeout=10,
            )

        # Checkout all files from vesi
        snapshot_mgr = SnapshotManager(repo)
        tree = snapshot_mgr.get_tree(head)

        # Write all files from vesi to temp dir
        file_count = 0
        for entry in tree.get_blob_entries():
            try:
                content = repo.blobs.load_content(entry.hash_id)
                file_path = tmp_dir / entry.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
                file_count += 1
            except Exception:
                pass

        _progress(f"  File: {file_count} file diproses")

        # Stage all files
        subprocess.run(
            ["git", "add", "."],
            cwd=str(tmp_dir), capture_output=True, timeout=30,
        )

        # Get commit message
        commit_data = repo.objects.load_json(head)
        message = commit_data.get("message", "vesi push")
        author = commit_data.get("author", "vesi")

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message,
             "--author", f"{author} <{author}@vesi.local>"],
            cwd=str(tmp_dir), capture_output=True, timeout=30,
        )

        _progress(f"  Commit: {message}")
        _progress("\n  Push ke remote...")

        # Push
        cmd = ["git", "push", "origin", branch]
        if force:
            cmd.insert(2, "--force")

        result = subprocess.run(
            cmd, cwd=str(tmp_dir),
            capture_output=True, text=True, timeout=120,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            _progress(f"✓ {output}")
            return True, output
        else:
            error = result.stderr.strip() or result.stdout.strip()
            _progress(f"✗ {error}")
            return False, error

    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


def _push_from_git_dir(
    repo_root: Path,
    remote: str,
    branch: str | None,
    force: bool,
    _progress: Any,
) -> tuple[bool, str]:
    """Push from a normal git repo."""
    import subprocess

    if not branch:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=10,
        )
        branch = result.stdout.strip() or "main"

    _progress(f"Push {branch} ke {remote} via git...")

    cmd = ["git", "push", remote, branch]
    if force:
        cmd.insert(2, "--force")

    result = subprocess.run(
        cmd, cwd=str(repo_root),
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode == 0:
        msg = result.stdout.strip() or "Push berhasil!"
        _progress(f"✓ {msg}")
        return True, msg
    else:
        msg = result.stderr.strip() or result.stdout.strip() or "Push gagal"
        _progress(f"✗ {msg}")
        return False, msg
