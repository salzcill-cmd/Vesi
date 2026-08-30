"""Command: ulang - Rerere (Reuse Recorded Resolution).

Record, replay, and manage conflict resolutions.
"""

from __future__ import annotations

from vesi.errors.exceptions import RepositoryNotFoundError, VesiError
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_rerere(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage rerere (Reuse Recorded Resolution).

    Usage:
      ulang                          - List recorded resolutions
      ulang status                   - Show rerere status
      ulang catatan                  - List all records
      ulang hapus <file>             - Forget resolutions for file
      ulang hapus --semua            - Forget all resolutions
      ulang bersihkan                - Remove old records (>90 days)
      ulang beda <hash>              - Show diff for a record
      ulang aktifkan                 - Enable rerere in config
      ulang nonaktifkan              - Disable rerere in config
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    from vesi.core.rerere import RerereManager
    rerere = RerereManager(repo.root)

    args = parsed.args or []
    subcommand = parsed.subcommand or ""

    # Determine action
    if subcommand == "status" or not subcommand:
        return _show_status(rerere, verbose)
    
    elif subcommand == "catatan" or subcommand == "list":
        return _list_records(rerere, args)
    
    elif subcommand == "hapus":
        return _forget_records(rerere, args)
    
    elif subcommand == "bersihkan" or subcommand == "cleanup":
        return _cleanup(rerere)
    
    elif subcommand == "beda" or subcommand == "diff":
        return _show_diff(rerere, args)
    
    elif subcommand == "aktifkan" or subcommand == "enable":
        return _set_config(repo, True)
    
    elif subcommand == "nonaktifkan" or subcommand == "disable":
        return _set_config(repo, False)
    
    else:
        print_color(f"Subcommand tidak dikenal: {subcommand}", "red")
        return 1


def _show_status(rerere: RerereManager, verbose: bool) -> int:
    """Show rerere status."""
    stats = rerere.stats()
    
    print_color("📋 Rerere (Reuse Recorded Resolution)\n", "cyan")
    print(f"  Total rekaman:    {stats['total_records']}")
    print(f"  File unik:        {stats['unique_files']}")
    
    if stats['total_records'] > 0:
        print(f"  Tertua:           {stats['oldest_record']:.0f} hari lalu")
        print(f"  Terbaru:          {stats['newest_record']:.0f} hari lalu")
    
    print()
    
    if stats['total_records'] == 0:
        print("  💡 Rerere merekam resolusi konflik secara otomatis.")
        print("     Saat kamu menyelesaikan konflik, vesi menyimpan")
        print("     cara kamu menyelesaikannya. Jika konflik yang sama")
        print("     muncul lagi, vesi akan menerapkan resolusi yang sama.")
        print()
        print("  Untuk mengaktifkan:")
        print("    vesi ulang aktifkan")
    
    return 0


def _list_records(rerere: RerereManager, args: list[str]) -> int:
    """List recorded resolutions."""
    filepath = args[0] if args else None
    records = rerere.list_records(filepath=filepath)
    
    if not records:
        print_color("Tidak ada rekaman resolusi.", "yellow")
        return 0
    
    print_color(f"📋 {len(records)} rekaman resolusi:\n", "cyan")
    
    for record in records:
        age = f"{record.age_days:.0f}d" if record.age_days >= 1 else f"{record.age_hours:.0f}h"
        print(f"  [{record.conflict_hash[:8]}] {record.filepath}")
        print(f"    Umur: {age} | Resolusi: {record.resolution_hash[:8]}")
        if record.branch_context:
            print(f"    Branch: {record.branch_context}")
        print()
    
    return 0


def _forget_records(rerere: RerereManager, args: list[str]) -> int:
    """Forget recorded resolutions."""
    if "--semua" in args or "--all" in args:
        forgotten = rerere.forget()
        print_color(f"✓ {forgotten} rekaman dihapus.", "green")
        return 0
    
    if not args:
        print_color("Gunakan: vesi ulang hapus <file> atau vesi ulang hapus --semua", "yellow")
        return 1
    
    filepath = args[0]
    forgotten = rerere.forget(filepath=filepath)
    print_color(f"✓ {forgotten} rekaman untuk '{filepath}' dihapus.", "green")
    return 0


def _cleanup(rerere: RerereManager) -> int:
    """Remove old records."""
    removed = rerere.cleanup(max_age_days=90)
    print_color(f"✓ {removed} rekaman lama dihapus (>90 hari).", "green")
    return 0


def _show_diff(rerere: RerereManager, args: list[str]) -> int:
    """Show diff for a record."""
    if not args:
        print_color("Gunakan: vesi ulang beda <hash>", "yellow")
        return 1
    
    conflict_hash = args[0]
    result = rerere.get_diff(conflict_hash)
    
    if not result:
        print_color(f"Rekaman '{conflict_hash}' tidak ditemukan.", "red")
        return 1
    
    conflict, resolution = result
    
    print_color("📝 Konflik Original:", "yellow")
    print(conflict[:500])
    print()
    print_color("✅ Resolusi:", "green")
    print(resolution[:500])
    
    return 0


def _set_config(repo: Repository, enabled: bool) -> int:
    """Enable/disable rerere in config."""
    from vesi.config.manager import ConfigManager
    config = ConfigManager(repo.root)
    
    config.set("rerere", "enabled", str(enabled).lower())
    
    status = "diaktifkan" if enabled else "dinonaktifkan"
    print_color(f"✓ Rerere {status}.", "green")
    
    if enabled:
        print("\nSekarang vesi akan otomatis merekam resolusi konflik.")
        print("Saat kamu menyelesaikan merge/rebase conflict, resolusi")
        print("akan disimpan dan diterapkan otomatis jika konflik sama muncul lagi.")
    
    return 0
