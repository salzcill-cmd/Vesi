"""Smart commit - generate intelligent commit messages."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CommitSuggestion:
    """A suggested commit message."""

    message: str
    type: str  # feat, fix, docs, etc.
    confidence: float  # 0-1
    description: str = ""


# File type to commit type mapping
FILE_TYPE_MAP = {
    # Python
    ".py": "chore",
    # JavaScript/TypeScript
    ".js": "chore",
    ".ts": "chore",
    ".jsx": "feat",
    ".tsx": "feat",
    # Web
    ".html": "feat",
    ".css": "style",
    ".scss": "style",
    # Config
    ".json": "chore",
    ".yaml": "chore",
    ".yml": "chore",
    ".toml": "chore",
    # Documentation
    ".md": "docs",
    ".rst": "docs",
    ".txt": "docs",
    # Test
    "test_": "test",
    "_test.py": "test",
    ".test.": "test",
    ".spec.": "test",
    # Build
    "Makefile": "chore",
    "Dockerfile": "chore",
    "docker-compose": "chore",
    # Dependencies
    "requirements": "chore",
    "package.json": "chore",
    "Cargo.toml": "chore",
}

# Change pattern detection
CHANGE_PATTERNS = [
    (r"def\s+\w+", "add function", "feat"),
    (r"class\s+\w+", "add class", "feat"),
    (r"import\s+", "add import", "chore"),
    (r"from\s+\w+\s+import", "add import", "chore"),
    (r"print\(", "add debug output", "chore"),
    (r"TODO|FIXME|HACK|XXX", "add TODO", "chore"),
    (r"raise\s+\w+Error", "add error handling", "fix"),
    (r"try\s*:", "add error handling", "fix"),
    (r"assert\s+", "add assertion", "test"),
    (r"def\s+test_", "add test", "test"),
]


def generate_commit_suggestions(
    changed_files: list[str],
    diff_content: str = "",
    staged_content: str = "",
) -> list[CommitSuggestion]:
    """Generate commit message suggestions based on changes.

    Args:
        changed_files: List of changed file paths
        diff_content: Diff content (optional)
        staged_content: Staged content (optional)

    Returns List of suggestions sorted by confidence.
    """
    suggestions = []

    # Analyze file types
    file_types = _analyze_file_types(changed_files)

    # Analyze change patterns
    change_patterns = _analyze_change_patterns(diff_content)

    # Generate suggestions based on analysis
    if file_types.get("docs", 0) > file_types.get("code", 0):
        suggestions.append(CommitSuggestion(
            message="docs: update documentation",
            type="docs",
            confidence=0.8,
            description="File dokumentasi berubah",
        ))

    if file_types.get("test", 0) > 0:
        suggestions.append(CommitSuggestion(
            message="test: add or update tests",
            type="test",
            confidence=0.7,
            description="File test berubah",
        ))

    if file_types.get("config", 0) > 0:
        suggestions.append(CommitSuggestion(
            message="chore: update configuration",
            type="chore",
            confidence=0.6,
            description="File konfigurasi berubah",
        ))

    # Analyze diff patterns
    if "def " in diff_content or "class " in diff_content:
        suggestions.append(CommitSuggestion(
            message="feat: add new functionality",
            type="feat",
            confidence=0.7,
            description="Function atau class baru ditambahkan",
        ))

    if "raise " in diff_content or "except " in diff_content:
        suggestions.append(CommitSuggestion(
            message="fix: improve error handling",
            type="fix",
            confidence=0.6,
            description="Error handling ditambahkan/diubah",
        ))

    if "test" in diff_content.lower() and ("assert" in diff_content or "def test" in diff_content):
        suggestions.append(CommitSuggestion(
            message="test: add test coverage",
            type="test",
            confidence=0.7,
            description="Test cases ditambahkan",
        ))

    # Check for specific patterns
    if any("README" in f or "docs" in f.lower() for f in changed_files):
        suggestions.append(CommitSuggestion(
            message="docs: update README",
            type="docs",
            confidence=0.9,
            description="README atau dokumentasi diupdate",
        ))

    if any("requirements" in f or "package.json" in f for f in changed_files):
        suggestions.append(CommitSuggestion(
            message="chore: update dependencies",
            type="chore",
            confidence=0.8,
            description="Dependencies diupdate",
        ))

    # Default suggestion
    if not suggestions:
        num_files = len(changed_files)
        suggestions.append(CommitSuggestion(
            message=f"chore: update {num_files} file{'s' if num_files > 1 else ''}",
            type="chore",
            confidence=0.5,
            description=f"{num_files} file berubah",
        ))

    # Sort by confidence
    suggestions.sort(key=lambda x: x.confidence, reverse=True)

    return suggestions[:5]  # Return top 5


def generate_conventional_commit(
    change_type: str,
    scope: str = "",
    description: str = "",
    body: str = "",
) -> str:
    """Generate a conventional commit message.

    Format: <type>(<scope>): <description>

    Args:
        change_type: feat, fix, docs, style, refactor, test, chore
        scope: Optional scope (e.g., "auth", "api")
        description: Short description
        body: Optional longer description

    Returns Formatted commit message.
    """
    if scope:
        header = f"{change_type}({scope}): {description}"
    else:
        header = f"{change_type}: {description}"

    if body:
        return f"{header}\n\n{body}"

    return header


def analyze_commit_message(message: str) -> dict:
    """Analyze a commit message for conventions.

    Returns analysis with suggestions for improvement.
    """
    analysis = {
        "is_conventional": False,
        "type": None,
        "scope": None,
        "description": None,
        "issues": [],
        "suggestions": [],
    }

    # Check conventional format
    conventional_pattern = r"^(feat|fix|docs|style|refactor|test|chore|breaking|perf|ci|build|revert)(\(.+\))?:\s+.+"
    if re.match(conventional_pattern, message):
        analysis["is_conventional"] = True

        # Extract parts
        parts = message.split(":", 1)
        type_scope = parts[0]

        if "(" in type_scope:
            type_part, scope_part = type_scope.split("(", 1)
            analysis["type"] = type_part
            analysis["scope"] = scope_part.rstrip(")")
        else:
            analysis["type"] = type_scope

        analysis["description"] = parts[1].strip()
    else:
        analysis["issues"].append("Tidak mengikuti conventional commit format")

    # Check description length
    if analysis.get("description"):
        desc = analysis["description"]
        if len(desc) > 72:
            analysis["issues"].append("Deskripsi terlalu panjang (max 72 karakter)")
        if len(desc) < 10:
            analysis["issues"].append("Deskripsi terlalu pendek (min 10 karakter)")
        if desc[0].isupper():
            analysis["suggestions"].append("Gunakan huruf kecil untuk deskripsi")
        if desc.endswith("."):
            analysis["suggestions"].append("Hapus titik di akhir deskripsi")

    return analysis


def _analyze_file_types(files: list[str]) -> dict[str, int]:
    """Analyze file types in the change set."""
    counts = {
        "code": 0,
        "docs": 0,
        "test": 0,
        "config": 0,
        "other": 0,
    }

    for filepath in files:
        filename = filepath.lower()

        if "test" in filename or "spec" in filename:
            counts["test"] += 1
        elif any(filepath.endswith(ext) for ext in [".md", ".rst", ".txt"]):
            counts["docs"] += 1
        elif any(filepath.endswith(ext) for ext in [".json", ".yaml", ".yml", ".toml", ".ini"]):
            counts["config"] += 1
        elif any(filepath.endswith(ext) for ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs"]):
            counts["code"] += 1
        else:
            counts["other"] += 1

    return counts


def _analyze_change_patterns(diff_content: str) -> dict[str, int]:
    """Analyze patterns in diff content."""
    patterns = {}

    for pattern, name, change_type in CHANGE_PATTERNS:
        matches = len(re.findall(pattern, diff_content))
        if matches > 0:
            patterns[name] = matches

    return patterns
