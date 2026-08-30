"""Pack file system - efficient object storage using compression.

Equivalent to Git's packfiles for storage efficiency.
Objects are stored in compressed packs with delta compression.
"""

from __future__ import annotations

import zlib
import struct
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator

from vesi.hashing import hash_content, short_hash


# Pack file format constants
PACK_SIGNATURE = b"VESIPACK"
PACK_VERSION = 1
PACK_HEADER_SIZE = 12  # 8 (sig) + 4 (version)
OBJECT_HEADER_SIZE = 5  # 1 (type+size) + 4 (size continuation)


@dataclass
class PackObject:
    """A single object in a pack file."""

    obj_type: int  # 1=blob, 2=tree, 3=snapshot, 4=commit
    data: bytes
    offset: int = 0
    hash_id: str = ""

    def __post_init__(self):
        if not self.hash_id:
            self.hash_id = hash_content(self.data)


@dataclass
class PackIndex:
    """Index for fast lookup in pack files."""

    fanout: list[int] = field(default_factory=list)  # 256-entry fanout table
    offsets: dict[str, int] = field(default_factory=dict)  # hash -> offset
    pack_path: Path = field(default_factory=lambda: Path(""))

    def lookup(self, hash_id: str) -> int | None:
        """Look up object offset by hash."""
        return self.offsets.get(hash_id)

    def contains(self, hash_id: str) -> bool:
        """Check if pack contains this object."""
        return hash_id in self.offsets


class PackWriter:
    """Writes objects to pack files with compression."""

    def __init__(self, packs_dir: Path) -> None:
        self.packs_dir = packs_dir
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self._current_pack: Path | None = None
        self._current_offset = 0
        self._objects_in_pack: dict[str, int] = {}
        self._index = PackIndex()

    def should_pack(self, loose_count: int = 500) -> bool:
        """Check if we should repack loose objects."""
        loose_dir = self.packs_dir.parent / "objects"
        if not loose_dir.is_dir():
            return False

        count = 0
        for prefix_dir in loose_dir.iterdir():
            if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                count += sum(1 for _ in prefix_dir.iterdir())
        return count >= loose_count

    def create_pack(self, objects: list[PackObject]) -> Path:
        """Create a new pack file from a list of objects.

        Returns path to the created pack file.
        """
        # Generate pack filename from hash of first object
        if objects:
            pack_name = objects[0].hash_id[:16]
        else:
            pack_name = hashlib.sha256(b"empty").hexdigest()[:16]

        pack_path = self.packs_dir / f"pack-{pack_name}.pack"
        idx_path = self.packs_dir / f"pack-{pack_name}.idx"

        with open(pack_path, "wb") as f:
            # Write header
            f.write(PACK_SIGNATURE)
            f.write(struct.pack(">I", PACK_VERSION))
            f.write(struct.pack(">I", len(objects)))

            # Write each object
            for obj in objects:
                self._write_object(f, obj)

        # Build index
        self._build_index(pack_path, idx_path, objects)

        self._current_pack = pack_path
        return pack_path

    def _write_object(self, f, obj: PackObject) -> None:
        """Write a single object to pack file with zlib compression."""
        # Object header: type (4 bits) + size (variable)
        obj_type_byte = (obj.obj_type & 0x0F) << 4
        size = len(obj.data)

        # Variable-length size encoding (like Git)
        header = bytearray()
        byte = obj_type_byte | (size & 0x7F)
        size >>= 7
        while size > 0:
            header.append(byte | 0x80)  # Continue bit
            byte = size & 0x7F
            size >>= 7
        header.append(byte)

        f.write(bytes(header))

        # Compress and write data
        compressed = zlib.compress(obj.data, level=6)
        f.write(compressed)

    def _build_index(
        self, pack_path: Path, idx_path: Path, objects: list[PackObject]
    ) -> None:
        """Build pack index file for fast lookups."""
        # Sort objects by hash for binary search
        sorted_objects = sorted(objects, key=lambda o: o.hash_id)

        # Build fanout table (256 entries, one per possible first byte)
        fanout = [0] * 256
        for obj in sorted_objects:
            byte_val = int(obj.hash_id[:2], 16)
            fanout[byte_val] += 1

        # Convert to cumulative
        for i in range(1, 256):
            fanout[i] += fanout[i - 1]

        # Build offset table
        offsets = {}
        offset = PACK_HEADER_SIZE
        for obj in sorted_objects:
            # Calculate object size in pack
            obj_size = len(self._encode_object_header(obj))
            compressed = zlib.compress(obj.data, level=6)
            total_size = obj_size + len(compressed)
            offsets[obj.hash_id] = offset
            offset += total_size

        # Write index file
        with open(idx_path, "wb") as f:
            # Fanout table
            for entry in fanout:
                f.write(struct.pack(">I", entry))

            # Hash table
            for obj in sorted_objects:
                f.write(bytes.fromhex(obj.hash_id))

            # Offset table
            for obj in sorted_objects:
                f.write(struct.pack(">I", offsets[obj.hash_id]))

            # Pack checksum
            pack_data = pack_path.read_bytes()
            pack_checksum = hashlib.sha256(pack_data).digest()
            f.write(pack_checksum)

    def _encode_object_header(self, obj: PackObject) -> bytes:
        """Encode object header (same as _write_object but returns bytes)."""
        obj_type_byte = (obj.obj_type & 0x0F) << 4
        size = len(obj.data)
        header = bytearray()
        byte = obj_type_byte | (size & 0x7F)
        size >>= 7
        while size > 0:
            header.append(byte | 0x80)
            byte = size & 0x7F
            size >>= 7
        header.append(byte)
        return bytes(header)


class PackReader:
    """Reads objects from pack files."""

    def __init__(self, pack_path: Path) -> None:
        self.pack_path = pack_path
        self._index: PackIndex | None = None

    def get_index(self) -> PackIndex:
        """Load or create pack index."""
        if self._index is None:
            idx_path = self.pack_path.with_suffix(".idx")
            if idx_path.is_file():
                self._index = self._load_index(idx_path)
            else:
                self._index = PackIndex()
        return self._index

    def has_object(self, hash_id: str) -> bool:
        """Check if pack contains this object."""
        index = self.get_index()
        return index.contains(hash_id)

    def read_object(self, hash_id: str) -> PackObject | None:
        """Read an object from the pack file."""
        index = self.get_index()
        offset = index.lookup(hash_id)
        if offset is None:
            return None

        with open(self.pack_path, "rb") as f:
            f.seek(offset)
            return self._read_object_at(f, offset)

    def _read_object_at(self, f, offset: int) -> PackObject:
        """Read object starting at given offset."""
        # Read header
        first_byte = f.read(1)[0]
        obj_type = (first_byte >> 4) & 0x0F
        size = first_byte & 0x7F

        shift = 7
        while first_byte & 0x80:
            first_byte = f.read(1)[0]
            size |= (first_byte & 0x7F) << shift
            shift += 7

        # Read compressed data
        # We need to decompress until we have enough bytes
        decompressor = zlib.decompressobj()
        data = b""
        while len(data) < size:
            chunk = f.read(4096)
            if not chunk:
                break
            try:
                data += decompressor.decompress(chunk)
            except zlib.error:
                break

        return PackObject(
            obj_type=obj_type,
            data=data[:size],
        )

    def _load_index(self, idx_path: Path) -> PackIndex:
        """Load pack index file."""
        index = PackIndex(pack_path=self.pack_path)

        with open(idx_path, "rb") as f:
            # Read fanout table
            for _ in range(256):
                entry = struct.unpack(">I", f.read(4))[0]
                index.fanout.append(entry)

            # Calculate number of objects
            num_objects = index.fanout[255] if index.fanout else 0

            # Read hash table
            hashes = []
            for _ in range(num_objects):
                hash_bytes = f.read(20)
                hashes.append(hash_bytes.hex())

            # Read offset table
            for hash_id in hashes:
                offset = struct.unpack(">I", f.read(4))[0]
                index.offsets[hash_id] = offset

        return index

    def list_objects(self) -> list[str]:
        """List all object hashes in this pack."""
        index = self.get_index()
        return list(index.offsets.keys())

    def pack_info(self) -> dict:
        """Get information about this pack file."""
        index = self.get_index()
        file_size = self.pack_path.stat().st_size if self.pack_path.is_file() else 0

        return {
            "pack_file": str(self.pack_path),
            "objects": len(index.offsets),
            "size_bytes": file_size,
            "size_human": _human_size(file_size),
        }


class ObjectPacker:
    """Manages packing and unpacking of objects."""

    def __init__(self, objects_dir: Path, packs_dir: Path) -> None:
        self.objects_dir = objects_dir
        self.packs_dir = packs_dir
        self.packs_dir.mkdir(parents=True, exist_ok=True)

    def pack_loose_objects(self, max_count: int = 500) -> Path | None:
        """Pack loose objects into a pack file.

        Args:
            max_count: Maximum loose objects before triggering pack.

        Returns:
            Path to created pack, or None if no packing needed.
        """
        # Count loose objects
        loose_objects = self._list_loose_objects()
        if len(loose_objects) < max_count:
            return None

        print(f"Packing {len(loose_objects)} loose objects...")

        # Convert to PackObjects
        pack_objects = []
        for hash_id in loose_objects:
            obj_path = self._loose_path(hash_id)
            if obj_path.is_file():
                data = obj_path.read_bytes()
                obj_type = self._detect_type(data)
                pack_objects.append(PackObject(
                    obj_type=obj_type,
                    data=data,
                    hash_id=hash_id,
                ))

        # Create pack
        writer = PackWriter(self.packs_dir)
        pack_path = writer.create_pack(pack_objects)

        # Remove packed loose objects (optional, keep for safety)
        # for hash_id in loose_objects:
        #     obj_path = self._loose_path(hash_id)
        #     if obj_path.is_file():
        #         obj_path.unlink()

        print(f"Pack created: {pack_path.name} ({len(pack_objects)} objects)")
        return pack_path

    def find_object(self, hash_id: str) -> bytes | None:
        """Find an object in loose storage or packs."""
        # Try loose first
        loose_path = self._loose_path(hash_id)
        if loose_path.is_file():
            return loose_path.read_bytes()

        # Try packs
        for pack_path in self.packs_dir.glob("pack-*.pack"):
            reader = PackReader(pack_path)
            if reader.has_object(hash_id):
                obj = reader.read_object(hash_id)
                if obj:
                    return obj.data

        return None

    def has_object(self, hash_id: str) -> bool:
        """Check if object exists in any storage."""
        loose_path = self._loose_path(hash_id)
        if loose_path.is_file():
            return True

        for pack_path in self.packs_dir.glob("pack-*.pack"):
            reader = PackReader(pack_path)
            if reader.has_object(hash_id):
                return True

        return False

    def pack_stats(self) -> dict:
        """Get statistics about pack files."""
        packs = []
        total_objects = 0
        total_size = 0

        for pack_path in self.packs_dir.glob("pack-*.pack"):
            reader = PackReader(pack_path)
            info = reader.pack_info()
            packs.append(info)
            total_objects += info["objects"]
            total_size += info["size_bytes"]

        # Count loose objects
        loose_count = len(self._list_loose_objects())

        return {
            "packs": len(packs),
            "packed_objects": total_objects,
            "loose_objects": loose_count,
            "total_size": _human_size(total_size),
        }

    def _list_loose_objects(self) -> list[str]:
        """List all loose object hashes."""
        hashes = []
        if not self.objects_dir.is_dir():
            return hashes

        for prefix_dir in self.objects_dir.iterdir():
            if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        hashes.append(full_hash)

        return hashes

    def _loose_path(self, hash_id: str) -> Path:
        """Get filesystem path for a loose object."""
        return self.objects_dir / hash_id[:2] / hash_id[2:]

    def _detect_type(self, data: bytes) -> int:
        """Detect object type from content."""
        # Simple heuristic: JSON with 'tree' key = snapshot, JSON with 'entries' = tree
        if data.startswith(b"{"):
            try:
                import json
                obj = json.loads(data.decode("utf-8"))
                if "tree" in obj and "message" in obj:
                    return 3  # snapshot
                elif "entries" in obj:
                    return 2  # tree
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        return 1  # blob


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
