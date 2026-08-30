"""Visual diff - colorized, side-by-side diff display."""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field


# ANSI colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"


@dataclass
class DiffLine:
    """A single line in a diff."""

    line_num_old: int | None = None
    line_num_new: int | None = None
    content: str = ""
    change_type: str = "context"  # "add", "delete", "context", "hunk"


@dataclass
class DiffHunk:
    """A hunk in a diff."""

    header: str
    lines: list[DiffLine] = field(default_factory=list)


class VisualDiff:
    """Generates colorized visual diff output."""

    def __init__(self, use_color: bool = True) -> None:
        self.use_color = use_color

    def _c(self, color: str, text: str) -> str:
        """Apply color to text."""
        if not self.use_color:
            return text
        return f"{color}{text}{RESET}"

    def side_by_side(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "sebelum",
        new_label: str = "sesudah",
        width: int = 80,
    ) -> str:
        """Generate side-by-side diff."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        # Calculate column width
        col_width = (width - 5) // 2  # 5 chars for separators

        result = []
        result.append(self._c(BOLD, f"{'─' * width}"))
        result.append(self._c(CYAN, f" {old_label:<{col_width}} │ {new_label:<{col_width}}"))
        result.append(self._c(BOLD, f"{'─' * width}"))

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    result.append(f"  {self._c(DIM, line[:col_width]):<{col_width + 10}} │ {self._c(DIM, line[:col_width])}")

            elif tag == "replace":
                max_len = max(i2 - i1, j2 - j1)
                for k in range(max_len):
                    old_line = old_lines[i1 + k] if i1 + k < i2 else ""
                    new_line = new_lines[j1 + k] if j1 + k < j2 else ""

                    old_display = self._c(BG_RED + WHITE, f"-{old_line[:col_width - 1]:<{col_width - 1}}")
                    new_display = self._c(BG_GREEN + WHITE, f"+{new_line[:col_width - 1]:<{col_width - 1}}")

                    result.append(f"  {old_display} │ {new_display}")

            elif tag == "delete":
                for line in old_lines[i1:i2]:
                    display = self._c(BG_RED + WHITE, f"-{line[:col_width - 1]:<{col_width - 1}}")
                    empty = " " * col_width
                    result.append(f"  {display} │ {empty}")

            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    empty = " " * col_width
                    display = self._c(BG_GREEN + WHITE, f"+{line[:col_width - 1]:<{col_width - 1}}")
                    result.append(f"  {empty} │ {display}")

        result.append(self._c(BOLD, f"{'─' * width}"))

        return "\n".join(result)

    def unified(
        self,
        old_text: str,
        new_text: str,
        old_label: str = "sebelum",
        new_label: str = "sesudah",
        context_lines: int = 3,
    ) -> str:
        """Generate unified diff with colors."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=old_label,
            tofile=new_label,
            n=context_lines,
        ))

        result = []
        for line in diff:
            line = line.rstrip("\n")

            if line.startswith("+++") or line.startswith("---"):
                result.append(self._c(BOLD, line))
            elif line.startswith("@@"):
                result.append(self._c(CYAN, line))
            elif line.startswith("+"):
                result.append(self._c(GREEN, line))
            elif line.startswith("-"):
                result.append(self._c(RED, line))
            else:
                result.append(line)

        return "\n".join(result)

    def inline(
        self,
        old_text: str,
        new_text: str,
    ) -> str:
        """Generate inline diff with word-level highlighting."""
        old_words = old_text.split()
        new_words = new_text.split()

        matcher = difflib.SequenceMatcher(None, old_words, new_words)

        result = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                result.append(" ".join(old_words[i1:i2]))
            elif tag == "replace":
                result.append(self._c(RED + BOLD, " ".join(old_words[i1:i2])))
                result.append(self._c(GREEN + BOLD, " ".join(new_words[j1:j2])))
            elif tag == "delete":
                result.append(self._c(RED, " ".join(old_words[i1:i2])))
            elif tag == "insert":
                result.append(self._c(GREEN, " ".join(new_words[j1:j2])))

        return " ".join(result)

    def stat_summary(
        self,
        old_text: str,
        new_text: str,
    ) -> str:
        """Generate stat summary."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        added = len(new_lines) - len(old_lines)
        removed = 0

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                removed += i2 - i1
            elif tag == "replace":
                removed += i2 - i1

        parts = []
        if added > 0:
            parts.append(self._c(GREEN, f"+{added}"))
        if removed > 0:
            parts.append(self._c(RED, f"-{removed}"))

        return " ".join(parts) if parts else "no changes"

    def file_stat(
        self,
        filename: str,
        old_text: str,
        new_text: str,
    ) -> str:
        """Generate file-level stat."""
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        added = max(0, len(new_lines) - len(old_lines))
        removed = max(0, len(old_lines) - len(new_lines))

        # Count actual changes
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        actual_added = 0
        actual_removed = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                actual_added += j2 - j1
            elif tag == "delete":
                actual_removed += i2 - i1
            elif tag == "replace":
                actual_added += j2 - j1
                actual_removed += i2 - i1

        # Format with colors
        name_width = 40
        stat_width = 20

        stat_parts = []
        if actual_added:
            stat_parts.append(self._c(GREEN, f"+{actual_added}"))
        if actual_removed:
            stat_parts.append(self._c(RED, f"-{actual_removed}"))

        stat_str = " ".join(stat_parts) if stat_parts else self._c(DIM, "no changes")

        # Create bar
        total = actual_added + actual_removed
        bar_width = 10
        if total > 0:
            add_bar = int((actual_added / total) * bar_width)
            rem_bar = bar_width - add_bar
            bar = self._c(GREEN, "█" * add_bar) + self._c(RED, "█" * rem_bar)
        else:
            bar = self._c(DIM, "─" * bar_width)

        return f" {filename:<{name_width}} {stat_str:<{stat_width}} {bar}"


def format_visual_diff(
    filepath: str,
    old_content: str,
    new_content: str,
    mode: str = "unified",
    use_color: bool = True,
) -> str:
    """Format a visual diff for a file."""
    differ = VisualDiff(use_color=use_color)

    if mode == "side-by-side":
        return differ.side_by_side(old_content, new_content, f"a/{filepath}", f"b/{filepath}")
    elif mode == "inline":
        return differ.inline(old_content, new_content)
    else:
        return differ.unified(old_content, new_content, f"a/{filepath}", f"b/{filepath}")
