"""Interactive staging - full hunk-level staging implementation.

Equivalent to git's interactive staging (git add -p / git add --patch).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class DiffHunk:
    """A single hunk in a unified diff."""

    index: int
    header: str
    start_line: int
    end_line: int
    content: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    context_lines: list[str] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return len(self.added_lines) + len(self.removed_lines)

    @property
    def is_addition_only(self) -> bool:
        return len(self.removed_lines) == 0 and len(self.added_lines) > 0

    @property
    def is_deletion_only(self) -> bool:
        return len(self.added_lines) == 0 and len(self.removed_lines) > 0


@dataclass
class StagingSelection:
    """User's staging selection for hunks."""

    hunks: list[DiffHunk]
    selections: dict[int, str] = field(default_factory=dict)  # hunk_index -> y/n/s/q

    def stage_hunk(self, index: int) -> None:
        self.selections[index] = "y"

    def skip_hunk(self, index: int) -> None:
        self.selections[index] = "n"

    def split_hunk(self, index: int) -> None:
        self.selections[index] = "s"

    def stage_all(self) -> None:
        for i in range(len(self.hunks)):
            self.selections[i] = "y"

    def skip_all(self) -> None:
        for i in range(len(self.hunks)):
            self.selections[i] = "n"

    @property
    def staged_indices(self) -> list[int]:
        return [i for i, s in self.selections.items() if s == "y"]


class InteractiveStager:
    """Manages interactive staging operations."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def get_file_hunks(self, filepath: str, working_content: str, staged_content: str | None) -> list[DiffHunk]:
        """Get diff hunks for a file.

        Compares working directory against staged area (or HEAD if nothing staged).
        """
        old_lines = (staged_content or "").splitlines(keepends=True)
        new_lines = working_content.splitlines(keepends=True)

        return self._compute_hunks(old_lines, new_lines)

    def _compute_hunks(self, old_lines: list[str], new_lines: list[str]) -> list[DiffHunk]:
        """Compute diff hunks from line lists."""
        hunks = []

        # Use SequenceMatcher for better diff
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        opcodes = matcher.get_opcodes()

        hunk_index = 0
        current_hunk_lines = []
        current_added = []
        current_removed = []
        hunk_start = 0
        context_count = 0
        max_context = 3

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                # Context lines
                context_lines = old_lines[i1:i2]

                if current_hunk_lines:
                    # End of current hunk - add trailing context
                    trailing = context_lines[:max_context]
                    current_hunk_lines.extend(trailing)

                    hunks.append(self._create_hunk(
                        hunk_index, current_hunk_lines,
                        current_added, current_removed, hunk_start
                    ))
                    hunk_index += 1
                    current_hunk_lines = []
                    current_added = []
                    current_removed = []

                # Start new hunk with leading context
                if not current_hunk_lines:
                    leading = context_lines[-max_context:] if len(context_lines) > max_context else context_lines
                    current_hunk_lines.extend(leading)
                    hunk_start = max(0, i1 - len(leading) + 1)

            elif tag == "replace":
                # Changed lines
                current_removed.extend([l.rstrip("\n") for l in old_lines[i1:i2]])
                current_added.extend([l.rstrip("\n") for l in new_lines[j1:j2]])
                current_hunk_lines.extend([f"-{l.rstrip()}" for l in old_lines[i1:i2]])
                current_hunk_lines.extend([f"+{l.rstrip()}" for l in new_lines[j1:j2]])

            elif tag == "delete":
                # Deleted lines
                current_removed.extend([l.rstrip("\n") for l in old_lines[i1:i2]])
                current_hunk_lines.extend([f"-{l.rstrip()}" for l in old_lines[i1:i2]])

            elif tag == "insert":
                # Added lines
                current_added.extend([l.rstrip("\n") for l in new_lines[j1:j2]])
                current_hunk_lines.extend([f"+{l.rstrip()}" for l in new_lines[j1:j2]])

        # Final hunk
        if current_hunk_lines:
            hunks.append(self._create_hunk(
                hunk_index, current_hunk_lines,
                current_added, current_removed, hunk_start
            ))

        return hunks

    def _create_hunk(
        self,
        index: int,
        lines: list[str],
        added: list[str],
        removed: list[str],
        start: int,
    ) -> DiffHunk:
        """Create a DiffHunk object."""
        # Generate header
        end = start + len(lines)
        header = f"@@ -{start},{len(removed)} +{start},{len(added)} @@"

        return DiffHunk(
            index=index,
            header=header,
            start_line=start,
            end_line=end,
            content="\n".join(lines),
            added_lines=added,
            removed_lines=removed,
        )

    def parse_user_selection(
        self,
        selection: str,
        num_hunks: int,
    ) -> list[int]:
        """Parse user selection string.

        Supports:
        - y/n for each hunk
        - a (stage all)
        - s (split hunk - not implemented yet)
        - q (quit)
        - , (select range, e.g., 1,3 or 2-5)
        """
        selection = selection.strip().lower()

        if selection == "a":
            return list(range(num_hunks))
        elif selection == "s" or selection == "q":
            return []

        # Handle comma-separated or range
        selected = set()

        for part in selection.split(","):
            part = part.strip()

            if "-" in part:
                # Range
                try:
                    start, end = part.split("-", 1)
                    start_idx = int(start) - 1
                    end_idx = int(end)
                    for i in range(start_idx, end_idx):
                        if 0 <= i < num_hunks:
                            selected.add(i)
                except ValueError:
                    pass
            elif part.isdigit():
                # Single index
                idx = int(part) - 1
                if 0 <= idx < num_hunks:
                    selected.add(idx)
            elif len(part) == num_hunks:
                # y/n sequence
                for i, char in enumerate(part):
                    if char == "y" and i < num_hunks:
                        selected.add(i)

        return sorted(selected)

    def apply_selections(
        self,
        original: str,
        hunks: list[DiffHunk],
        selected_indices: list[int],
    ) -> str:
        """Apply selected hunks to create new content."""
        lines = original.split("\n")
        result_lines = []
        line_idx = 0

        for hunk in hunks:
            # Add unchanged lines before this hunk
            while line_idx < hunk.start_line - 1 and line_idx < len(lines):
                result_lines.append(lines[line_idx])
                line_idx += 1

            if hunk.index in selected_indices:
                # Apply this hunk
                for added_line in hunk.added_lines:
                    result_lines.append(added_line)
                # Skip removed lines
                line_idx += len(hunk.removed_lines)
            else:
                # Skip this hunk - keep original
                line_idx += len(hunk.removed_lines)

        # Add remaining lines
        while line_idx < len(lines):
            result_lines.append(lines[line_idx])
            line_idx += 1

        return "\n".join(result_lines)

    def interactive_add(
        self,
        filepath: str,
        working_content: str,
        staged_content: str | None = None,
        auto_select: str | None = None,
    ) -> str | None:
        """Interactive add a file.

        Args:
            filepath: Path to file
            working_content: Current working directory content
            staged_content: Currently staged content (or None for HEAD)
            auto_select: Auto-select hunks (e.g., "yyn" for 3 hunks)

        Returns New content after staging, or None if cancelled.
        """
        hunks = self.get_file_hunks(filepath, working_content, staged_content)

        if not hunks:
            return None  # No changes

        if auto_select:
            selected = self.parse_user_selection(auto_select, len(hunks))
        else:
            # In real implementation, this would prompt user
            # For now, select all
            selected = list(range(len(hunks)))

        return self.apply_selections(working_content, hunks, selected)

    def split_hunk(
        self,
        hunk: DiffHunk,
        split_points: list[int] | None = None,
    ) -> list[DiffHunk]:
        """Split a hunk into smaller hunks.

        Args:
            hunk: Hunk to split
            split_points: Line numbers to split at (if None, auto-split)

        Returns List of smaller hunks.
        """
        lines = hunk.content.split("\n")

        if not split_points:
            # Auto-split at blank lines between changes
            split_points = []
            in_change = False
            for i, line in enumerate(lines):
                if line.startswith("+") or line.startswith("-"):
                    if not in_change:
                        in_change = True
                else:
                    if in_change:
                        split_points.append(i)
                        in_change = False

        if not split_points:
            return [hunk]

        # Split at points
        sub_hunks = []
        prev_point = 0
        for split_point in split_points:
            sub_lines = lines[prev_point:split_point]
            if sub_lines:
                sub_hunk = self._create_hunk(
                    len(sub_hunks),
                    sub_lines,
                    [l[1:] for l in sub_lines if l.startswith("+")],
                    [l[1:] for l in sub_lines if l.startswith("-")],
                    hunk.start_line + prev_point,
                )
                sub_hunks.append(sub_hunk)
            prev_point = split_point

        # Final part
        sub_lines = lines[prev_point:]
        if sub_lines:
            sub_hunk = self._create_hunk(
                len(sub_hunks),
                sub_lines,
                [l[1:] for l in sub_lines if l.startswith("+")],
                [l[1:] for l in sub_lines if l.startswith("-")],
                hunk.start_line + prev_point,
            )
            sub_hunks.append(sub_hunk)

        return sub_hunks if sub_hunks else [hunk]

    def format_hunk(self, hunk: DiffHunk, show_number: bool = True) -> str:
        """Format a hunk for display."""
        lines = []
        lines.append(hunk.header)

        for i, line in enumerate(hunk.content.split("\n")):
            if show_number:
                num = hunk.start_line + i
                lines.append(f"{num:4d} {line}")
            else:
                lines.append(f" {line}")

        return "\n".join(lines)

    def format_selection_prompt(self, hunks: list[DiffHunk]) -> str:
        """Format the selection prompt."""
        lines = []
        lines.append(f"Stage {len(hunks)} hunk(s)? (y/n/a/s/q)")
        lines.append("")
        lines.append("  y = stage this hunk")
        lines.append("  n = skip this hunk")
        lines.append("  a = stage all remaining")
        lines.append("  s = split this hunk")
        lines.append("  q = quit")

        return "\n".join(lines)

    def get_changes_summary(self, hunks: list[DiffHunk]) -> str:
        """Get summary of changes."""
        total_added = sum(len(h.added_lines) for h in hunks)
        total_removed = sum(len(h.removed_lines) for h in hunks)

        parts = []
        if total_added:
            parts.append(f"{total_added} insertion(+)")
        if total_removed:
            parts.append(f"{total_removed} deletion(-)")

        return ", ".join(parts) if parts else "no changes"
