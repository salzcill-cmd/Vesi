"""Partial staging - hunk-level staging for fine-grained commits.

Equivalent to git's interactive staging (git add -p).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from vesi.hashing import hash_content


@dataclass
class DiffHunk:
    """A single hunk in a unified diff."""

    start_line: int
    end_line: int
    content: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)

    @property
    def is_addition_only(self) -> bool:
        return len(self.removed_lines) == 0 and len(self.added_lines) > 0

    @property
    def is_deletion_only(self) -> bool:
        return len(self.added_lines) == 0 and len(self.removed_lines) > 0


@dataclass
class StagingHunk:
    """A hunk that can be staged individually."""

    index: int
    hunk: DiffHunk
    status: str = "pending"  # pending, staged, skipped


class PartialStaging:
    """Manages partial/hunk-level staging."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def get_hunks(self, filepath: str) -> list[DiffHunk]:
        """Get diff hunks for a file.

        Parses unified diff output into individual hunks.
        """
        file_path = self.repo_root / filepath
        if not file_path.is_file():
            return []

        # Get the diff for this file
        current_content = file_path.read_bytes()
        try:
            current_lines = current_content.decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            return []

        # We need the base version to diff against
        # For now, return empty - this needs tree access
        # This will be called from cmd_stage with proper context
        return []

    def parse_diff_hunks(self, diff_text: str) -> list[DiffHunk]:
        """Parse unified diff text into hunks."""
        hunks = []
        current_hunk = None

        for line in diff_text.split("\n"):
            # Match hunk header: @@ -start,count +start,count @@
            hunk_match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$", line)
            if hunk_match:
                if current_hunk:
                    hunks.append(current_hunk)

                start_line = int(hunk_match.group(2))
                current_hunk = DiffHunk(
                    start_line=start_line,
                    end_line=start_line,
                    content=line + "\n",
                )
                continue

            if current_hunk:
                current_hunk.content += line + "\n"
                current_hunk.end_line += 1

                if line.startswith("+") and not line.startswith("+++"):
                    current_hunk.added_lines.append(line[1:])
                elif line.startswith("-") and not line.startswith("---"):
                    current_hunk.removed_lines.append(line[1:])

        if current_hunk:
            hunks.append(current_hunk)

        return hunks

    def apply_hunks(
        self,
        filepath: str,
        original_content: str,
        hunks: list[DiffHunk],
        selected_indices: list[int],
    ) -> str:
        """Apply selected hunks to create new file content.

        Args:
            filepath: Path to file
            original_content: Original file content
            hunks: All diff hunks
            selected_indices: Which hunks to apply (0-based)

        Returns:
            New file content with selected hunks applied.
        """
        lines = original_content.split("\n")
        result_lines = []
        line_idx = 0

        for i, hunk in enumerate(hunks):
            # Add unchanged lines before this hunk
            while line_idx < hunk.start_line - 1 and line_idx < len(lines):
                result_lines.append(lines[line_idx])
                line_idx += 1

            if i in selected_indices:
                # Apply this hunk: add new lines, skip old lines
                for added_line in hunk.added_lines:
                    result_lines.append(added_line)
                # Skip removed lines from original
                line_idx += len(hunk.removed_lines)
            else:
                # Skip this hunk: keep original lines
                total_change = len(hunk.added_lines) - len(hunk.removed_lines)
                line_idx += len(hunk.removed_lines)

        # Add remaining lines
        while line_idx < len(lines):
            result_lines.append(lines[line_idx])
            line_idx += 1

        return "\n".join(result_lines)

    def interactive_select(
        self,
        hunks: list[DiffHunk],
    ) -> list[int]:
        """Interactive hunk selection (for non-interactive mode, selects all).

        In a real implementation, this would show each hunk and ask y/n/q.
        For now, returns all indices.
        """
        return list(range(len(hunks)))

    def split_into_changes(
        self,
        filepath: str,
        old_content: bytes,
        new_content: bytes,
    ) -> list[dict]:
        """Split a file diff into individual line changes.

        Returns list of change dicts with line info.
        """
        try:
            old_text = old_content.decode("utf-8").splitlines()
            new_text = new_content.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            return []

        matcher = difflib.SequenceMatcher(None, old_text, new_text)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            change = {
                "type": tag,
                "old_start": i1 + 1,
                "old_end": i2,
                "new_start": j1 + 1,
                "new_end": j2,
                "old_lines": old_text[i1:i2],
                "new_lines": new_text[j1:j2],
            }
            changes.append(change)

        return changes

    def stage_hunks_from_diff(
        self,
        filepath: str,
        diff_text: str,
        original_content: str,
        selection: str,
    ) -> str | None:
        """Stage specific hunks based on user selection.

        Args:
            filepath: File path
            diff_text: Unified diff text
            original_content: Original file content
            selection: User selection string (e.g., "yyn" for 3 hunks)

        Returns:
            New content with selected hunks applied, or None if no changes.
        """
        hunks = self.parse_diff_hunks(diff_text)
        if not hunks:
            return None

        # Parse selection
        selected = []
        for i, char in enumerate(selection.lower()):
            if i < len(hunks) and char == "y":
                selected.append(i)

        if not selected:
            return None

        return self.apply_hunks(filepath, original_content, hunks, selected)

    def get_line_changes(
        self,
        old_lines: list[str],
        new_lines: list[str],
    ) -> list[dict]:
        """Get line-by-line changes between two versions.

        Returns list of change records.
        """
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            changes.append({
                "type": tag,
                "old_range": (i1, i2),
                "new_range": (j1, j2),
                "old_lines": old_lines[i1:i2],
                "new_lines": new_lines[j1:j2],
            })

        return changes

    def create_patch(
        self,
        filepath: str,
        old_lines: list[str],
        new_lines: list[str],
        context_lines: int = 3,
    ) -> str:
        """Create a unified diff patch between two line lists."""
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=context_lines,
        )
        return "".join(diff)

    def parse_selection(self, selection: str, max_hunks: int) -> list[int]:
        """Parse user selection string.

        Supports:
        - "y" or "n" for each hunk
        - "a" to stage all
        - "s" to skip all
        - "1,3" to select specific hunks
        - "1-3" to select range
        """
        selection = selection.strip().lower()

        if selection == "a":
            return list(range(max_hunks))
        if selection == "s":
            return []

        # Check for comma-separated indices
        if "," in selection:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
                return [i for i in indices if 0 <= i < max_hunks]
            except ValueError:
                pass

        # Check for range
        if "-" in selection:
            try:
                start, end = selection.split("-", 1)
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip())
                return [i for i in range(start_idx, end_idx) if 0 <= i < max_hunks]
            except ValueError:
                pass

        # Treat as y/n sequence
        selected = []
        for i, char in enumerate(selection):
            if i < max_hunks and char == "y":
                selected.append(i)
        return selected
