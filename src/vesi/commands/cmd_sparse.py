"""Command: sebagian - Sparse checkout (partial clone/checkout).

Only checkout specific directories from the repository.
Useful for large monorepos.
"""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path

from vesi.errors.exceptions import RepositoryNotFoundError, VesiError
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_sebagian(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage sparse checkout (partial checkout).

    Usage:
      sebagian aktifkan              - Enable sparse checkout
      sebagian nonaktifkan           - Disable sparse checkout (checkout all)
      sebagian tetapkan <patterns>   - Set include patterns
      sebagian tambah <patterns>     - Add patterns
      sebagian hapus <patterns>      - Remove patterns
      sebagian daftar                - List current patterns
      sebagian status                - Show sparse checkout status
      sebagian cone                  - Use cone模式 (faster, directory-only)
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    sparse_dir = repo.root / ".vesi" / "sparse"
    config_file = sparse_dir / "config.json"

    args = parsed.args or []
    subcommand = parsed.subcommand or ""

    if subcommand == "aktifkan" or subcommand == "enable":
        return _enable_sparse(repo, sparse_dir, config_file)
    
    elif subcommand == "nonaktifkan" or subcommand == "disable":
        return _disable_sparse(repo, sparse_dir, config_file)
    
    elif subcommand == "tetapkan" or subcommand == "set":
        return _set_patterns(config_file, args)
    
    elif subcommand == "tambah" or subcommand == "add":
        return _add_patterns(config_file, args)
    
    elif subcommand == "hapus" or subcommand == "remove":
        return _remove_patterns(config_file, args)
    
    elif subcommand == "daftar" or subcommand == "list":
        return _list_patterns(config_file)
    
    elif subcommand == "status":
        return _show_status(config_file)
    
    elif subcommand == "cone":
        return _set_cone_mode(config_file, True)
    
    else:
        print_color("Subcommand tidak dikenal. Gunakan: sebagian <aktifkan|nonaktifkan|tetapkan|tambah|hapu|daftar|status>", "red")
        return 1


def _load_config(config_file: Path) -> dict:
    if config_file.is_file():
        try:
            return json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"enabled": False, "patterns": [], "cone_mode": False}


def _save_config(config_file: Path, config: dict) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _enable_sparse(repo: Repository, sparse_dir: Path, config_file: Path) -> int:
    """Enable sparse checkout."""
    config = _load_config(config_file)
    config["enabled"] = True
    
    if not config["patterns"]:
        config["patterns"] = ["/*", "!/.vesi/"]
    
    _save_config(config_file, config)
    
    print_color("✓ Sparse checkout diaktifkan.", "green")
    print(f"\n  Patterns aktif: {len(config['patterns'])}")
    for p in config["patterns"]:
        print(f"    {p}")
    
    print("\n💡 Gunakan 'sebagian tetapkan' untuk mengatur direktori yang di-checkout.")
    return 0


def _disable_sparse(repo: Repository, sparse_dir: Path, config_file: Path) -> int:
    """Disable sparse checkout (checkout everything)."""
    config = _load_config(config_file)
    config["enabled"] = False
    _save_config(config_file, config)
    
    print_color("✓ Sparse checkout dinonaktifkan. Semua file akan di-checkout.", "green")
    return 0


def _set_patterns(config_file: Path, patterns: list[str]) -> int:
    """Set sparse checkout patterns."""
    if not patterns:
        print_color("Gunakan: vesi sebagian tetapkan <pattern1> <pattern2> ...", "yellow")
        print("\nContoh:")
        print("  vesi sebagian tetapkan src/ docs/")
        print("  vesi sebagian tetapkan '/*' '!tests/'")
        return 1
    
    config = _load_config(config_file)
    config["patterns"] = patterns
    _save_config(config_file, config)
    
    print_color(f"✓ {len(patterns)} pattern diatur:", "green")
    for p in patterns:
        print(f"    {p}")
    
    return 0


def _add_patterns(config_file: Path, patterns: list[str]) -> int:
    """Add patterns to sparse checkout."""
    if not patterns:
        print_color("Gunakan: vesi sebagian tambah <pattern1> <pattern2> ...", "yellow")
        return 1
    
    config = _load_config(config_file)
    
    for p in patterns:
        if p not in config["patterns"]:
            config["patterns"].append(p)
    
    _save_config(config_file, config)
    
    print_color(f"✓ {len(patterns)} pattern ditambahkan.", "green")
    return 0


def _remove_patterns(config_file: Path, patterns: list[str]) -> int:
    """Remove patterns from sparse checkout."""
    if not patterns:
        print_color("Gunakan: vesi sebagian hapus <pattern1> ...", "yellow")
        return 1
    
    config = _load_config(config_file)
    
    removed = 0
    for p in patterns:
        if p in config["patterns"]:
            config["patterns"].remove(p)
            removed += 1
    
    _save_config(config_file, config)
    
    print_color(f"✓ {removed} pattern dihapus.", "green")
    return 0


def _list_patterns(config_file: Path) -> int:
    """List current sparse checkout patterns."""
    config = _load_config(config_file)
    
    if not config.get("enabled"):
        print_color("Sparse checkout tidak aktif.", "yellow")
        return 0
    
    patterns = config.get("patterns", [])
    
    if not patterns:
        print_color("Tidak ada pattern.", "yellow")
        return 0
    
    print_color(f"📋 {len(patterns)} sparse checkout patterns:\n", "cyan")
    for p in patterns:
        print(f"  {p}")
    
    return 0


def _show_status(config_file: Path) -> int:
    """Show sparse checkout status."""
    config = _load_config(config_file)
    
    enabled = config.get("enabled", False)
    patterns = config.get("patterns", [])
    cone = config.get("cone_mode", False)
    
    status = "Aktif ✓" if enabled else "Nonaktif"
    color = "green" if enabled else "yellow"
    
    print_color("📋 Sparse Checkout Status\n", "cyan")
    print(f"  Status:     {status}")
    print(f"  Patterns:   {len(patterns)}")
    print(f"  Cone mode:  {'Ya' if cone else 'Tidak'}")
    
    if enabled and patterns:
        print(f"\n  Patterns:")
        for p in patterns:
            print(f"    {p}")
    
    return 0


def _set_cone_mode(config_file: Path, cone: bool) -> int:
    """Enable/disable cone mode."""
    config = _load_config(config_file)
    config["cone_mode"] = cone
    _save_config(config_file, config)
    
    mode = "cone" if cone else "non-cone"
    print_color(f"✓ Sparse checkout mode: {mode}", "green")
    
    if cone:
        print("  Cone mode: hanya direktori yang di-include (lebih cepat)")
    else:
        print("  Non-cone mode: support wildcard patterns")
    
    return 0


def should_include(filepath: str, patterns: list[str]) -> bool:
    """Check if a file should be included based on sparse patterns.
    
    Args:
        filepath: Relative file path
        patterns: List of include/exclude patterns
    
    Returns:
        True if file should be checked out
    """
    if not patterns:
        return True
    
    included = False
    
    for pattern in patterns:
        if pattern.startswith("!"):
            # Exclude pattern
            exclude = pattern[1:]
            if fnmatch.fnmatch(filepath, exclude) or fnmatch.fnmatch(filepath, exclude + "/**"):
                included = False
        else:
            # Include pattern
            if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(filepath, pattern + "/**"):
                included = True
    
    return included
