"""Command: cari - Search for pattern in files."""

from __future__ import annotations

import os
import re
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.ignore import load_ignore_patterns, is_ignored
from vesi.repository.repository import Repository
from vesi.utils.paths import is_binary_file


def cmd_cari(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Search for pattern in tracked files."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan pola yang akan dicari.",
            hint="Contoh:\n    cari <pola>\n    cari <pola> di <folder>",
        )

    pattern = parsed.args[0]
    search_dir = parsed.options.get("di") or parsed.options.get("in") or "."

    ignore_patterns = load_ignore_patterns(repo.root)
    search_path = repo.root / search_dir

    if not search_path.exists():
        raise VesiError(f"Folder '{search_dir}' tidak ditemukan.")

    # Compile regex pattern
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        # Fall back to literal search
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    matches: list[dict] = []

    # Search in files
    for root_dir, dirs, files in os.walk(search_path):
        # Skip .vesi and ignored dirs
        dirs[:] = [
            d for d in dirs
            if d != ".vesi" and not is_ignored(
                str(Path(root_dir).relative_to(repo.root) / d),
                ignore_patterns,
            )
        ]

        for filename in files:
            file_path = Path(root_dir) / filename
            rel_path = str(file_path.relative_to(repo.root))

            # Skip ignored files
            if is_ignored(rel_path, ignore_patterns):
                continue

            # Skip binary files
            if is_binary_file(file_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append({
                            "file": rel_path,
                            "line": i,
                            "content": line.rstrip(),
                        })
            except (OSError, UnicodeDecodeError):
                continue

    # Display results
    if not matches:
        print(f"Tidak ditemukan pola '{pattern}' di '{search_dir}'.")
        return 0

    # Group by file
    files_match: dict[str, list[dict]] = {}
    for match in matches:
        file = match["file"]
        if file not in files_match:
            files_match[file] = []
        files_match[file].append(match)

    # Print results
    total_files = len(files_match)
    total_matches = len(matches)
    print(f"Hasil pencarian '{pattern}': {total_matches} kecocokan di {total_files} file\n")

    for file, file_matches in files_match.items():
        print(f"  {file}:")
        for match in file_matches:
            line_num = match["line"]
            line_content = match["content"]
            # Highlight match
            highlighted = regex.sub(lambda m: f"\033[1;31m{m.group()}\033[0m", line_content)
            print(f"    {line_num:4d}: {highlighted}")
        print()

    return 0
