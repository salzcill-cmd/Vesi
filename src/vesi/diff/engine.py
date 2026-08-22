"""Diff engine - line-based diff for text files."""

from __future__ import annotations

import difflib
from pathlib import Path

from vesi.utils.paths import is_binary_file


def diff_files(
    old_content: bytes,
    new_content: bytes,
    old_label: str = "sebelum",
    new_label: str = "sesudah",
) -> str:
    """Compute unified diff between two byte contents.

    Returns formatted diff string.
    """
    try:
        old_text = old_content.decode("utf-8").splitlines(keepends=True)
        new_text = new_content.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return f"Binary file berubah. Tidak bisa menampilkan diff."

    if old_text == new_text:
        return ""

    diff = difflib.unified_diff(
        old_text,
        new_text,
        fromfile=old_label,
        tofile=new_label,
        lineterm="",
    )
    return "".join(diff)


def diff_working_vs_snapshot(
    repo_root: Path,
    filepath: str,
    snapshot_content: bytes | None,
) -> str:
    """Diff a working directory file against its snapshot version."""
    file_path = repo_root / filepath

    if is_binary_file(file_path):
        if snapshot_content is None:
            return f"Binary file baru: {filepath}"
        return f"Binary file \"{filepath}\" berubah."

    if not file_path.is_file():
        if snapshot_content is not None:
            return _diff_deleted(filepath, snapshot_content)
        return ""

    working_content = file_path.read_bytes()

    if snapshot_content is None:
        return _diff_new(filepath, working_content)

    return diff_files(snapshot_content, working_content, f"a/{filepath}", f"b/{filepath}")


def diff_between_trees(
    repo_root: Path,
    old_tree_entries: dict[str, bytes],
    new_tree_entries: dict[str, bytes],
) -> str:
    """Compute diff between two trees (sets of file contents)."""
    all_files = sorted(set(list(old_tree_entries.keys()) + list(new_tree_entries.keys())))

    diffs: list[str] = []
    for filepath in all_files:
        old_content = old_tree_entries.get(filepath)
        new_content = new_tree_entries.get(filepath)

        if old_content is None:
            diffs.append(_diff_new(filepath, new_content or b""))
        elif new_content is None:
            diffs.append(_diff_deleted(filepath, old_content))
        else:
            d = diff_files(old_content, new_content, f"a/{filepath}", f"b/{filepath}")
            if d:
                diffs.append(d)

    return "\n".join(diffs) if diffs else "Tidak ada perbedaan."


def _diff_new(filepath: str, content: bytes) -> str:
    """Format diff for a new file."""
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return f"[file baru binary: {filepath}]"

    result = f"{filepath} [file baru]\n"
    for line in lines:
        result += f"+{line}\n"
    return result


def _diff_deleted(filepath: str, content: bytes) -> str:
    """Format diff for a deleted file."""
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return f"[file dihapus binary: {filepath}]"

    result = f"{filepath} [file dihapus]\n"
    for line in lines:
        result += f"-{line}\n"
    return result


def format_diff_header(mode: str, label: str) -> str:
    """Format diff section header."""
    return f"\n{label}\n{'─' * len(label)}\n"
