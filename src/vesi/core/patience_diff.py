"""Patience Diff Algorithm.

A better diff algorithm that produces cleaner, more readable diffs.
Used by Git's --diff-algorithm=patience option.

Key difference from Myers:
- Matches unique lines first, producing cleaner hunks
- Better at handling code with shifted blocks
- Produces fewer, larger hunks
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class DiffLine:
    """A single line in a diff."""
    old_num: int | None  # Line number in old (None for additions)
    new_num: int | None  # Line number in new (None for deletions)
    content: str
    type: str  # "context", "add", "delete"


@dataclass
class DiffHunk:
    """A group of changes in a diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]
    
    @property
    def header(self) -> str:
        return f"@@ -{self.old_start},{self.old_count} +{self.new_start},{self.new_count} @@"


@dataclass
class DiffResult:
    """Complete diff result."""
    hunks: list[DiffHunk]
    old_file: str = ""
    new_file: str = ""
    
    @property
    def total_added(self) -> int:
        return sum(1 for h in self.hunks for l in h.lines if l.type == "add")
    
    @property
    def total_deleted(self) -> int:
        return sum(1 for h in self.hunks for l in h.lines if l.type == "delete")
    
    @property
    def has_changes(self) -> bool:
        return len(self.hunks) > 0


def patience_diff(old_lines: list[str], new_lines: list[str]) -> DiffResult:
    """Compute diff using patience algorithm.
    
    Falls back to Myers (difflib) when patience doesn't help.
    """
    if old_lines == new_lines:
        return DiffResult(hunks=[])
    
    if not old_lines:
        return DiffResult(hunks=[
            DiffHunk(
                old_start=1, old_count=0,
                new_start=1, new_count=len(new_lines),
                lines=[DiffLine(None, i+1, line, "add") for i, line in enumerate(new_lines)],
            )
        ])
    
    if not new_lines:
        return DiffResult(hunks=[
            DiffHunk(
                old_start=1, old_count=len(old_lines),
                new_start=1, new_count=0,
                lines=[DiffLine(i+1, None, line, "delete") for i, line in enumerate(old_lines)],
            )
        ])
    
    # Try patience: find unique lines and match them
    unique_old = _find_unique_lines(old_lines)
    unique_new = _find_unique_lines(new_lines)
    
    # Find common unique lines
    matches = []
    for line, old_idx in unique_old.items():
        if line in unique_new:
            new_idx = unique_new[line]
            matches.append((old_idx, new_idx))
    
    # If we have enough unique matches, use patience
    if len(matches) >= min(3, min(len(old_lines), len(new_lines)) // 10):
        return _patience_with_matches(old_lines, new_lines, matches)
    
    # Fall back to Myers
    return _myers_diff(old_lines, new_lines)


def _find_unique_lines(lines: list[str]) -> dict[str, int]:
    """Find lines that appear exactly once."""
    # Count occurrences
    counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped:
            counts[stripped] = counts.get(stripped, 0) + 1
    
    # Keep only unique lines
    unique: dict[str, int] = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and counts.get(stripped, 0) == 1:
            unique[stripped] = i
    
    return unique


def _patience_with_matches(
    old_lines: list[str],
    new_lines: list[str],
    matches: list[tuple[int, int]],
) -> DiffResult:
    """Build diff using patience matches."""
    # Sort matches by old line number
    matches.sort(key=lambda m: m[0])
    
    # Build hunks from matches and gaps
    hunks = []
    prev_old = -1
    prev_new = -1
    
    for old_idx, new_idx in matches:
        # Context before match
        ctx_start = max(0, old_idx - 3)
        ctx_end = old_idx
        
        # Lines between matches
        if prev_old >= 0:
            gap_old = old_lines[prev_old + 1:ctx_start]
            gap_new = new_lines[prev_new + 1:max(0, new_idx - 3)]
            
            if gap_old or gap_new:
                hunk_lines = _build_hunk_lines(
                    old_lines, new_lines,
                    prev_old + 1, ctx_start,
                    prev_new + 1, max(0, new_idx - 3),
                )
                if hunk_lines:
                    hunks.append(DiffHunk(
                        old_start=prev_old + 2,
                        old_count=len(gap_old),
                        new_start=prev_new + 2,
                        new_count=len(gap_new),
                        lines=hunk_lines,
                    ))
        
        prev_old = old_idx
        prev_new = new_idx
    
    # Gap after last match
    if prev_old >= 0 and prev_old < len(old_lines) - 1:
        gap_old = old_lines[prev_old + 1:]
        gap_new = new_lines[prev_new + 1:]
        
        if gap_old or gap_new:
            hunk_lines = _build_hunk_lines(
                old_lines, new_lines,
                prev_old + 1, len(old_lines),
                prev_new + 1, len(new_lines),
            )
            if hunk_lines:
                hunks.append(DiffHunk(
                    old_start=prev_old + 2,
                    old_count=len(gap_old),
                    new_start=prev_new + 2,
                    new_count=len(gap_new),
                    lines=hunk_lines,
                ))
    
    # Merge adjacent hunks
    hunks = _merge_hunks(hunks)
    
    return DiffResult(hunks=hunks)


def _build_hunk_lines(
    old_lines: list[str],
    new_lines: list[str],
    old_start: int,
    old_end: int,
    new_start: int,
    new_end: int,
) -> list[DiffLine]:
    """Build diff lines for a hunk."""
    lines = []
    
    # Use SequenceMatcher for the gap
    old_slice = old_lines[old_start:old_end]
    new_slice = new_lines[new_start:new_end]
    
    matcher = difflib.SequenceMatcher(None, old_slice, new_slice)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                lines.append(DiffLine(
                    old_num=old_start + k + 1,
                    new_num=new_start + k + 1,
                    content=old_slice[k],
                    type="context",
                ))
        elif tag == "replace":
            for k in range(i1, i2):
                lines.append(DiffLine(
                    old_num=old_start + k + 1,
                    new_num=None,
                    content=old_slice[k],
                    type="delete",
                ))
            for k in range(j1, j2):
                lines.append(DiffLine(
                    old_num=None,
                    new_num=new_start + k + 1,
                    content=new_slice[k],
                    type="add",
                ))
        elif tag == "delete":
            for k in range(i1, i2):
                lines.append(DiffLine(
                    old_num=old_start + k + 1,
                    new_num=None,
                    content=old_slice[k],
                    type="delete",
                ))
        elif tag == "insert":
            for k in range(j1, j2):
                lines.append(DiffLine(
                    old_num=None,
                    new_num=new_start + k + 1,
                    content=new_slice[k],
                    type="add",
                ))
    
    return lines


def _merge_hunks(hunks: list[DiffHunk], context: int = 3) -> list[DiffHunk]:
    """Merge hunks that are close together."""
    if not hunks:
        return []
    
    merged = [hunks[0]]
    
    for hunk in hunks[1:]:
        prev = merged[-1]
        
        # Check if hunks should be merged
        gap = hunk.old_start - (prev.old_start + prev.old_count)
        
        if gap <= context * 2:
            # Merge
            new_lines = prev.lines + hunk.lines
            merged[-1] = DiffHunk(
                old_start=prev.old_start,
                old_count=hunk.old_start + hunk.old_count - prev.old_start,
                new_start=prev.new_start,
                new_count=hunk.new_start + hunk.new_count - prev.new_start,
                lines=new_lines,
            )
        else:
            merged.append(hunk)
    
    return merged


def _myers_diff(old_lines: list[str], new_lines: list[str]) -> DiffResult:
    """Standard Myers diff (fallback)."""
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    
    hunks = []
    current_lines = []
    current_old_start = 0
    current_new_start = 0
    current_old_count = 0
    current_new_count = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            if current_lines:
                hunks.append(DiffHunk(
                    old_start=current_old_start + 1,
                    old_count=current_old_count,
                    new_start=current_new_start + 1,
                    new_count=current_new_count,
                    lines=current_lines,
                ))
                current_lines = []
                current_old_count = 0
                current_new_count = 0
        else:
            if not current_lines:
                current_old_start = i1
                current_new_start = j1
            
            if tag in ("replace", "delete"):
                for k in range(i1, i2):
                    current_lines.append(DiffLine(
                        old_num=i1 + k + 1,
                        new_num=None,
                        content=old_lines[k],
                        type="delete",
                    ))
                    current_old_count += 1
            
            if tag in ("replace", "insert"):
                for k in range(j1, j2):
                    current_lines.append(DiffLine(
                        old_num=None,
                        new_num=j1 + k + 1,
                        content=new_lines[k],
                        type="add",
                    ))
                    current_new_count += 1
    
    if current_lines:
        hunks.append(DiffHunk(
            old_start=current_old_start + 1,
            old_count=current_old_count,
            new_start=current_new_start + 1,
            new_count=current_new_count,
            lines=current_lines,
        ))
    
    return DiffResult(hunks=hunks)
