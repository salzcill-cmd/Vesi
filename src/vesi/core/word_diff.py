"""Word-level diff - highlight individual word changes within lines.

Similar to git diff --word-diff, shows changes at the word level
within each line, making it easier to see exactly what changed.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass


@dataclass
class WordChange:
    """A word-level change."""
    word: str
    type: str  # "equal", "add", "delete"


@dataclass
class WordDiffLine:
    """A line with word-level diff markers."""
    old_num: int | None
    new_num: int | None
    content: str  # Formatted with markers
    has_changes: bool


# Regex for splitting into words (preserves whitespace)
WORD_PATTERN = re.compile(r'(\S+|\s+)')


def word_diff_line(old_line: str, new_line: str) -> tuple[str, str]:
    """Compute word diff between two lines.
    
    Returns (old_formatted, new_formatted) with change markers.
    
    Markers:
      [-deleted-] — deleted words
      {+added+}   — added words
    """
    old_words = _tokenize(old_line)
    new_words = _tokenize(new_line)
    
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    
    old_result = []
    new_result = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            old_result.append("".join(old_words[i1:i2]))
            new_result.append("".join(new_words[j1:j2]))
        elif tag == "replace" or tag == "delete":
            deleted = "".join(old_words[i1:i2])
            if deleted.strip():
                old_result.append(f"[-{deleted}-]")
            else:
                old_result.append(deleted)
        elif tag == "insert" or tag == "replace":
            pass  # handled below
        
        if tag == "replace" or tag == "insert":
            added = "".join(new_words[j1:j2])
            if added.strip():
                new_result.append(f"{{+{added}+}}")
            else:
                new_result.append(added)
    
    return "".join(old_result), "".join(new_result)


def word_diff_block(
    old_lines: list[str],
    new_lines: list[str],
    context: int = 0,
) -> list[tuple[str, str]]:
    """Compute word diff for a block of lines.
    
    Returns list of (old_formatted, new_formatted) pairs.
    Only returns lines that have word-level changes.
    """
    results = []
    
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        
        # Process changed lines
        max_len = max(i2 - i1, j2 - j1)
        
        for k in range(max_len):
            old_line = old_lines[i1 + k] if (i1 + k) < i2 else ""
            new_line = new_lines[j1 + k] if (j1 + k) < j2 else ""
            
            old_fmt, new_fmt = word_diff_line(old_line, new_line)
            
            if old_fmt != new_fmt:
                results.append((old_fmt, new_fmt))
    
    return results


def word_diff_stats(
    old_lines: list[str],
    new_lines: list[str],
) -> dict[str, int]:
    """Get word-level diff statistics."""
    old_words = set()
    new_words = set()
    
    for line in old_lines:
        for word in line.split():
            old_words.add(word)
    
    for line in new_lines:
        for word in line.split():
            new_words.add(word)
    
    added = new_words - old_words
    removed = old_words - new_words
    
    return {
        "words_added": len(added),
        "words_removed": len(removed),
        "words_unchanged": len(old_words & new_words),
    }


def format_word_diff_unified(
    old_lines: list[str],
    new_lines: list[str],
    filepath: str = "",
) -> str:
    """Format word diff as unified output.
    
    Uses markers:
      [-deleted-] for removed words
      {+added+} for added words
    """
    lines = []
    
    if filepath:
        lines.append(f"--- a/{filepath}")
        lines.append(f"+++ b/{filepath}")
    
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                lines.append(f" {old_lines[k]}")
        elif tag == "replace":
            # Show word diff for each pair
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                old_line = old_lines[i1 + k] if (i1 + k) < i2 else ""
                new_line = new_lines[j1 + k] if (j1 + k) < j2 else ""
                
                old_fmt, new_fmt = word_diff_line(old_line, new_line)
                
                if old_fmt:
                    lines.append(f"-{old_fmt}")
                if new_fmt:
                    lines.append(f"+{new_fmt}")
        elif tag == "delete":
            for k in range(i1, i2):
                lines.append(f"-{old_lines[k]}")
        elif tag == "insert":
            for k in range(j1, j2):
                lines.append(f"+{new_lines[k]}")
    
    return "\n".join(lines)


def _tokenize(text: str) -> list[str]:
    """Split text into words and whitespace tokens."""
    return WORD_PATTERN.findall(text)
