"""Delta compression for efficient object storage.

Implements Git-style delta compression where similar objects
store only the differences from a base object.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Optional


# Delta instruction types
OPS_DELTA_INSERT = 0  # Insert data from delta stream
OPS_DELTA_COPY = 1    # Copy data from base object


@dataclass
class DeltaOps:
    """Operations in a delta instruction."""

    offset: int = 0
    size: int = 0
    data: bytes = b""


def compute_delta_size(base_size: int, target_size: int) -> int:
    """Estimate delta size between two objects."""
    # Simple estimation: smaller delta = more similar objects
    return min(base_size, target_size) // 4


def create_delta(base: bytes, target: bytes) -> bytes:
    """Create delta encoding of target relative to base.

    The delta format:
    - Header: base_size (variable), target_size (variable)
    - Instructions: sequence of insert/copy operations

    Returns compressed delta bytes.
    """
    # Build delta instructions
    instructions = bytearray()

    # Header: base size and target size
    instructions.extend(_encode_size(len(base)))
    instructions.extend(_encode_size(len(target)))

    # Generate instructions using LCS-based diff
    ops = _diff_to_ops(base, target)

    for op in ops:
        if op.data:
            # Insert instruction
            instructions.append(OPS_DELTA_INSERT)
            instructions.extend(_encode_size(len(op.data)))
            instructions.extend(op.data)
        else:
            # Copy instruction
            instructions.append(OPS_DELTA_COPY | _copy_offset_encoding(op.offset))
            instructions.extend(_encode_copy_offset(op.offset))
            instructions.extend(_encode_size(op.size))

    return bytes(instructions)


def apply_delta(base: bytes, delta: bytes) -> bytes:
    """Apply delta to base object to reconstruct target.

    Args:
        base: Base object content
        delta: Delta instructions

    Returns Reconstructed target content.
    """
    pos = 0

    # Read header
    base_size, pos = _decode_size(delta, pos)
    target_size, pos = _decode_size(delta, pos)

    if base_size != len(base):
        raise ValueError(f"Base size mismatch: expected {base_size}, got {len(base)}")

    result = bytearray()

    # Process instructions
    while pos < len(delta):
        cmd = delta[pos]
        pos += 1

        if cmd & OPS_DELTA_INSERT:
            # Insert from delta stream
            size, pos = _decode_size(delta, pos)
            result.extend(delta[pos:pos + size])
            pos += size
        else:
            # Copy from base
            # Parse offset encoding
            offset = 0
            for bit in range(4):
                if cmd & (1 << bit):
                    offset |= delta[pos] << (bit * 8)
                    pos += 1

            # Parse size
            size, pos = _decode_size(delta, pos)

            result.extend(base[offset:offset + size])

    if len(result) != target_size:
        raise ValueError(f"Target size mismatch: expected {target_size}, got {len(result)}")

    return bytes(result)


def _encode_size(size: int) -> bytes:
    """Encode size as variable-length bytes."""
    result = bytearray()
    while size > 0x7f:
        result.append((size & 0x7f) | 0x80)
        size >>= 7
    result.append(size & 0x7f)
    return bytes(result)


def _decode_size(data: bytes, pos: int) -> tuple[int, int]:
    """Decode variable-length size."""
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos


def _encode_copy_offset(offset: int) -> bytes:
    """Encode copy offset."""
    result = bytearray()
    for _ in range(4):
        result.append(offset & 0xff)
        offset >>= 8
    return bytes(result)


def _copy_offset_encoding(offset: int) -> int:
    """Determine which offset bytes are non-zero."""
    encoding = 0
    for i in range(4):
        if (offset >> (i * 8)) & 0xff:
            encoding |= 1 << i
    return encoding << 4


def _diff_to_ops(base: bytes, target: bytes) -> list[DeltaOps]:
    """Generate delta operations from base to target.

    Uses a simplified LCS algorithm.
    """
    if not base:
        return [DeltaOps(data=target)]

    if not target:
        return []

    # Find matching regions using rolling hash
    ops = []
    target_pos = 0
    base_len = len(base)
    target_len = len(target)

    while target_pos < target_len:
        # Try to find a match in base
        match_offset, match_size = _find_match(base, target, target_pos)

        if match_size >= 3:  # Minimum match size to be worth it
            # Copy from base
            ops.append(DeltaOps(offset=match_offset, size=match_size))
            target_pos += match_size
        else:
            # Collect insert data
            insert_start = target_pos
            while target_pos < target_len:
                match_offset, match_size = _find_match(base, target, target_pos)
                if match_size >= 3:
                    break
                target_pos += 1

            ops.append(DeltaOps(data=target[insert_start:target_pos]))

    return ops


def _find_match(base: bytes, target: bytes, target_pos: int) -> tuple[int, int]:
    """Find the longest match of target[target_pos:] in base.

    Returns (offset, size) tuple.
    """
    best_offset = 0
    best_size = 0
    target_len = len(target)
    base_len = len(base)

    # Quick scan for first byte match
    first_byte = target[target_pos]
    for i in range(base_len):
        if base[i] != first_byte:
            continue

        # Extend match
        size = 0
        while (target_pos + size < target_len and
               i + size < base_len and
               base[i + size] == target[target_pos + size]):
            size += 1

        if size > best_size:
            best_size = size
            best_offset = i

    return best_offset, best_size


class DeltaCompressor:
    """Manages delta compression for object storage."""

    def __init__(self, min_delta_ratio: float = 0.5) -> None:
        self.min_delta_ratio = min_delta_ratio

    def should_delta_compress(self, base_size: int, target_size: int) -> bool:
        """Check if delta compression would be beneficial."""
        if base_size == 0 or target_size == 0:
            return False

        # Estimate delta size
        delta_size = compute_delta_size(base_size, target_size)

        # Check ratio
        ratio = delta_size / target_size
        return ratio < self.min_delta_ratio

    def compress_pair(self, base: bytes, target: bytes) -> tuple[bytes, bool]:
        """Try to delta-compress target against base.

        Returns (compressed_data, was_delta_encoded).
        """
        delta = create_delta(base, target)

        # Check if delta is smaller
        if len(delta) < len(target):
            # Store as delta
            return delta, True
        else:
            # Store as full object
            return target, False

    def decompress(self, base: bytes, data: bytes, is_delta: bool) -> bytes:
        """Decompress data (delta or full object)."""
        if is_delta:
            return apply_delta(base, data)
        return data
