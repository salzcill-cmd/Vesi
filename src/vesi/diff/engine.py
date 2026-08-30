"""Diff engine - line-based diff for text files with rename detection."""

from __future__ import annotations

import difflib
from pathlib import Path
from dataclasses import dataclass, field

from vesi.utils.paths import is_binary_file


@dataclass
class DiffStats:
    """Statistics for a diff operation."""

    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    renames: list[tuple[str, str]] = field(default_factory=list)

    def __str__(self) -> str:
        parts = [f"{self.files_changed} file{'s' if self.files_changed != 1 else ''} changed"]
        if self.insertions > 0:
            parts.append(f"{self.insertions} insertion{'s' if self.insertions != 1 else ''}(+)")
        if self.deletions > 0:
            parts.append(f"{self.deletions} deletion{'s' if self.deletions != 1 else ''}(-)")
        if self.renames:
            parts.append(f"{len(self.renames)} rename{'s' if len(self.renames) != 1 else ''}")
        return ", ".join(parts)


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


def compute_diff_stats(
    old_tree_entries: dict[str, bytes],
    new_tree_entries: dict[str, bytes],
) -> DiffStats:
    """Compute statistics for a diff between two trees."""
    stats = DiffStats()
    all_files = set(list(old_tree_entries.keys()) + list(new_tree_entries.keys()))

    for filepath in all_files:
        old_content = old_tree_entries.get(filepath)
        new_content = new_tree_entries.get(filepath)

        if old_content is None:
            # New file
            stats.files_changed += 1
            try:
                lines = new_content.decode("utf-8").splitlines()
                stats.insertions += len(lines)
            except (UnicodeDecodeError, AttributeError):
                pass
        elif new_content is None:
            # Deleted file
            stats.files_changed += 1
            try:
                lines = old_content.decode("utf-8").splitlines()
                stats.deletions += len(lines)
            except (UnicodeDecodeError, AttributeError):
                pass
        elif old_content != new_content:
            # Modified file
            stats.files_changed += 1
            try:
                old_lines = old_content.decode("utf-8").splitlines()
                new_lines = new_content.decode("utf-8").splitlines()

                # Count actual insertions and deletions using unified diff
                diff = list(difflib.unified_diff(
                    old_lines, new_lines, lineterm=""
                ))
                for line in diff:
                    if line.startswith("+") and not line.startswith("+++"):
                        stats.insertions += 1
                    elif line.startswith("-") and not line.startswith("---"):
                        stats.deletions += 1
            except (UnicodeDecodeError, AttributeError):
                pass

    return stats


def detect_renames(
    old_entries: dict[str, bytes],
    new_entries: dict[str, bytes],
    similarity_threshold: float = 0.6,
) -> list[tuple[str, str, float]]:
    """Detect file renames between two trees.

    Uses content similarity to detect renames.
    Returns list of (old_path, new_path, similarity) tuples.
    """
    renames = []

    # Find deleted and added files
    deleted = {k: v for k, v in old_entries.items() if k not in new_entries}
    added = {k: v for k, v in new_entries.items() if k not in old_entries}

    if not deleted or not added:
        return renames

    # Compare content of deleted vs added files
    matched_new = set()
    matched_old = set()

    for old_path, old_content in deleted.items():
        best_match = None
        best_similarity = 0.0

        for new_path, new_content in added.items():
            if new_path in matched_new:
                continue

            # Quick check: if same content, it's definitely a rename
            if old_content == new_content:
                renames.append((old_path, new_path, 1.0))
                matched_new.add(new_path)
                matched_old.add(old_path)
                best_match = None
                break

            # Compute similarity using line-based comparison
            try:
                old_lines = old_content.decode("utf-8").splitlines()
                new_lines = new_content.decode("utf-8").splitlines()

                if old_lines and new_lines:
                    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
                    similarity = matcher.ratio()

                    if similarity > best_similarity and similarity >= similarity_threshold:
                        best_similarity = similarity
                        best_match = new_path
            except (UnicodeDecodeError, AttributeError):
                continue

        if best_match:
            renames.append((old_path, best_match, best_similarity))
            matched_new.add(best_match)
            matched_old.add(old_path)

    return renames


def diff_with_rename_detection(
    repo_root: Path,
    old_tree_entries: dict[str, bytes],
    new_tree_entries: dict[str, bytes],
) -> tuple[str, DiffStats]:
    """Compute diff with rename detection.

    Returns (diff_text, stats).
    """
    # Detect renames
    renames = detect_renames(old_tree_entries, new_tree_entries)

    # Build adjusted tree entries (remove renamed files from add/delete)
    adjusted_old = dict(old_tree_entries)
    adjusted_new = dict(new_tree_entries)

    rename_old_paths = {r[0] for r in renames}
    rename_new_paths = {r[1] for r in renames}

    for old_path, new_path, similarity in renames:
        if old_path in adjusted_old:
            del adjusted_old[old_path]
        if new_path in adjusted_new:
            del adjusted_new[new_path]

    # Compute stats
    stats = compute_diff_stats(adjusted_old, adjusted_new)
    stats.renames = [(old, new) for old, new, _ in renames]

    # Compute diff
    diffs = []

    # Show renames
    for old_path, new_path, similarity in renames:
        pct = int(similarity * 100)
        diffs.append(f"rename {old_path} → {new_path} ({pct}% similar)")

    # Show regular diffs
    all_files = sorted(set(list(adjusted_old.keys()) + list(adjusted_new.keys())))
    for filepath in all_files:
        old_content = adjusted_old.get(filepath)
        new_content = adjusted_new.get(filepath)

        if old_content is None:
            diffs.append(_diff_new(filepath, new_content or b""))
        elif new_content is None:
            diffs.append(_diff_deleted(filepath, old_content))
        else:
            d = diff_files(old_content, new_content, f"a/{filepath}", f"b/{filepath}")
            if d:
                diffs.append(d)

    diff_text = "\n".join(diffs) if diffs else "Tidak ada perbedaan."
    return diff_text, stats


def diff_word_level(
    old_content: str,
    new_content: str,
) -> str:
    """Compute word-level diff between two strings.

    Returns unified diff with word-level granularity.
    """
    old_words = old_content.split()
    new_words = new_content.split()

    # Use SequenceMatcher for word-level diff
    matcher = difflib.SequenceMatcher(None, old_words, new_words)

    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append(" ".join(old_words[i1:i2]))
        elif tag == "replace":
            result.append(f"\033[31m{' '.join(old_words[i1:i2])}\033[0m")
            result.append(f"\033[32m{' '.join(new_words[j1:j2])}\033[0m")
        elif tag == "delete":
            result.append(f"\033[31m{' '.join(old_words[i1:i2])}\033[0m")
        elif tag == "insert":
            result.append(f"\033[32m{' '.join(new_words[j1:j2])}\033[0m")

    return " ".join(result)


def format_diff_header(mode: str, label: str) -> str:
    """Format diff section header."""
    return f"\n{label}\n{'─' * len(label)}\n"


def format_stat_summary(stats: DiffStats) -> str:
    """Format a stat summary line."""
    return str(stats)
