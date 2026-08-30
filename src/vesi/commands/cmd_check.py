"""Command: cek - Repository integrity check with repair and GC."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.storage.pack import ObjectPacker
from vesi.utils.platform import print_color


def cmd_cek(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Check repository integrity.

    Options:
      --repair       Attempt to fix issues
      --gc           Run garbage collection
      --deep         Deep integrity check (verify all hashes)
      --stat         Show repository statistics
      --objects      Show object statistics
      --orphan       Find orphaned objects
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Handle special modes
    if "--gc" in parsed.flags:
        return _run_gc(repo, verbose)

    if "--stat" in parsed.flags:
        return _show_stats(repo, verbose)

    if "--objects" in parsed.flags:
        return _show_object_stats(repo, verbose)

    if "--orphan" in parsed.flags:
        return _find_orphans(repo, verbose)

    # Standard integrity check
    repair = "--repair" in parsed.flags
    deep = "--deep" in parsed.flags

    print_color("🔍 Pemeriksaan integritas repository...\n", "cyan")

    errors = []
    warnings = []
    checks_passed = 0

    # 1. Check directory structure
    print("  1. Struktur directory...")
    vesi_dir = repo.vesi_dir
    required_dirs = ["objects", "refs", "refs/heads"]
    for d in required_dirs:
        if not (vesi_dir / d).is_dir():
            errors.append(f"Directory '{d}' tidak ditemukan")
        else:
            checks_passed += 1

    # 2. Check HEAD
    print("  2. HEAD reference...")
    head = repo.refs.get_head()
    if head:
        checks_passed += 1
        if verbose:
            print(f"     HEAD: {head}")
    else:
        warnings.append("HEAD tidak terdefinisi")

    # 3. Check active branch
    print("  3. Branch aktif...")
    active_branch = repo.refs.get_active_branch()
    if active_branch:
        branch_hash = repo.refs.get_branch_hash(active_branch)
        if branch_hash:
            checks_passed += 1
            if verbose:
                print(f"     {active_branch} -> {short_hash(branch_hash)}")
        else:
            warnings.append(f"Branch '{active_branch}' tidak memiliki commit")
    else:
        warnings.append("Tidak ada branch aktif")

    # 4. Check all branches
    print("  4. Semua branch...")
    branches = repo.refs.list_branches()
    for branch in branches:
        branch_hash = repo.refs.get_branch_hash(branch)
        if branch_hash:
            checks_passed += 1
        else:
            warnings.append(f"Branch '{branch}' kosong")

    # 5. Check objects
    print("  5. Object store...")
    object_count = repo.objects.count_objects()
    if object_count > 0:
        checks_passed += 1
        if verbose:
            print(f"     {object_count} objek")
    else:
        warnings.append("Object store kosong")

    # 6. Verify object hashes (deep check)
    if deep:
        print("  6. Verifikasi hash objek (deep)...")
        integrity_errors = repo.objects.verify_integrity()
        if integrity_errors:
            errors.extend(integrity_errors)
        else:
            checks_passed += 1
            if verbose:
                print(f"     Semua {object_count} objek valid")
    else:
        print("  6. Verifikasi hash (gunakan --deep untuk pemeriksaan lengkap)")

    # 7. Check index
    print("  7. Index (staging area)...")
    index = repo.index.load()
    checks_passed += 1
    if verbose and index:
        print(f"     {len(index)} file ter-stage")

    # 8. Check config
    print("  8. Konfigurasi...")
    config = repo.get_config()
    if config:
        checks_passed += 1
    else:
        warnings.append("Konfigurasi tidak ditemukan")

    # Report
    print(f"\n{'─' * 50}")

    if errors:
        print_color(f"\n✗ {len(errors)} error ditemukan:", "red")
        for error in errors:
            print(f"    • {error}")

        if repair:
            print_color("\n🔧 Mencoba memperbaiki...", "yellow")
            repaired = _attempt_repair(repo, errors)
            print(f"    {repaired} masalah diperbaiki")
    else:
        print_color(f"\n✓ Tidak ada error.", "green")

    if warnings:
        print_color(f"\n⚠ {len(warnings)} peringatan:", "yellow")
        for warning in warnings:
            print(f"    • {warning}")

    print(f"\n  {checks_passed} pemeriksaan berhasil.")

    # Pack stats
    packer = ObjectPacker(repo.vesi_dir / "objects", repo.vesi_dir / "packs")
    pack_stats = packer.pack_stats()
    if pack_stats["packs"] > 0:
        print(f"\n  📦 Pack files: {pack_stats['packs']} ({pack_stats['packed_objects']} objek)")

    return 1 if errors else 0


def _run_gc(repo: Repository, verbose: bool) -> int:
    """Run garbage collection."""
    print_color("🗑️  Garbage collection...\n", "cyan")

    removed = 0
    packer = ObjectPacker(repo.vesi_dir / "objects", repo.vesi_dir / "packs")

    # Find orphaned objects
    print("  1. Mencari objek orphan...")
    orphans = _find_orphan_hashes(repo)

    if orphans:
        print(f"     Ditemukan {len(orphans)} objek orphan")
        if verbose:
            for h in orphans[:10]:
                print(f"       {short_hash(h)}")
            if len(orphans) > 10:
                print(f"       ... dan {len(orphans) - 10} lainnya")
    else:
        print("     Tidak ada objek orphan")

    # Run expire on reflog
    print("  2. Expiring reflog...")
    from vesi.commands.cmd_reflog import ReflogManager
    reflog = ReflogManager(repo)
    expired = reflog.expire_entries(90)
    print(f"     {expired} entri reflog expired")

    # Pack loose objects if threshold reached
    print("  3. Packing loose objects...")
    pack_path = packer.pack_loose_objects(max_count=200)
    if pack_path:
        print(f"     Pack dibuat: {pack_path.name}")
    else:
        print("     Belum perlu packing")

    # Remove empty directories
    print("  4. Membersihkan directory kosong...")
    empty_dirs = _find_empty_dirs(repo.vesi_dir)
    for d in empty_dirs:
        if verbose:
            print(f"     Menghapus: {d.relative_to(repo.vesi_dir)}")
        d.rmdir()
        removed += 1
    print(f"     {removed} directory kosong dihapus")

    print_color(f"\n✓ GC selesai!", "green")
    return 0


def _show_stats(repo: Repository, verbose: bool) -> int:
    """Show repository statistics."""
    print_color("📊 Statistik Repository:\n", "cyan")

    # Object store
    object_count = repo.objects.count_objects()
    object_size = repo.objects.total_size()
    print(f"  📁 Object Store:")
    print(f"     Objek:      {object_count}")
    print(f"     Ukuran:     {_human_size(object_size)}")

    # Branches
    branches = repo.refs.list_branches()
    active = repo.refs.get_active_branch()
    print(f"\n  🌿 Branches:")
    print(f"     Total:      {len(branches)}")
    print(f"     Aktif:      {active or '(none)'}")

    # Tags
    tags_dir = repo.vesi_dir / "refs" / "tags"
    tag_count = len(list(tags_dir.iterdir())) if tags_dir.is_dir() else 0
    print(f"\n  🏷️  Tags:")
    print(f"     Total:      {tag_count}")

    # Index
    index = repo.index.load()
    print(f"\n  📋 Index:")
    print(f"     Staged:     {len(index)} file")

    # Pack files
    packer = ObjectPacker(repo.vesi_dir / "objects", repo.vesi_dir / "packs")
    pack_stats = packer.pack_stats()
    print(f"\n  📦 Pack Files:")
    print(f"     Packs:      {pack_stats['packs']}")
    print(f"     Packed:     {pack_stats['packed_objects']}")
    print(f"     Loose:      {pack_stats['loose_objects']}")
    print(f"     Total size: {pack_stats['total_size']}")

    # Reflog
    reflog_file = repo.vesi_dir / "reflog.json"
    if reflog_file.is_file():
        try:
            reflog = json.loads(reflog_file.read_text(encoding="utf-8"))
            print(f"\n  📜 Reflog:")
            print(f"     Entries:    {len(reflog)}")
        except (json.JSONDecodeError, OSError):
            pass

    # Config
    config = repo.get_config()
    print(f"\n  ⚙️  Config:")
    for section, values in config.items():
        if isinstance(values, dict):
            for key, value in values.items():
                if value:
                    print(f"     {section}.{key}: {value}")

    return 0


def _show_object_stats(repo: Repository, verbose: bool) -> int:
    """Show object statistics."""
    print_color("📦 Object Statistics:\n", "cyan")

    objects_dir = repo.vesi_dir / "objects"
    if not objects_dir.is_dir():
        print("Object store kosong.")
        return 0

    # Count by prefix
    prefix_counts: dict[str, int] = {}
    total = 0
    total_size = 0

    for prefix_dir in objects_dir.iterdir():
        if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
            count = sum(1 for _ in prefix_dir.iterdir())
            prefix_counts[prefix_dir.name] = count
            total += count

    # Get top prefixes
    top_prefixes = sorted(prefix_counts.items(), key=lambda x: -x[1])[:20]

    print(f"  Total objek: {total}")
    print(f"\n  Top prefixes:")
    for prefix, count in top_prefixes:
        bar = "█" * min(count, 30)
        print(f"    {prefix}: {count:>4}  {bar}")

    if len(prefix_counts) > 20:
        print(f"    ... dan {len(prefix_counts) - 20} prefix lainnya")

    return 0


def _find_orphans(repo: Repository) -> list[str]:
    """Find object hashes not referenced by any commit."""
    from vesi.core.snapshot import SnapshotManager

    snapshot_mgr = SnapshotManager(repo)

    # Collect all referenced hashes
    referenced: set[str] = set()

    # Walk all commits
    for branch in repo.refs.list_branches():
        branch_hash = repo.refs.get_branch_hash(branch)
        if not branch_hash:
            continue

        current = branch_hash
        visited = set()
        while current and current not in visited:
            visited.add(current)
            referenced.add(current)

            try:
                data = snapshot_mgr.load_snapshot(current)
                referenced.add(data.get("tree", ""))

                # Add parent
                current = data.get("parent")
            except (FileNotFoundError, ValueError):
                break

    # Get all hashes
    all_hashes = set()
    objects_dir = repo.vesi_dir / "objects"
    if objects_dir.is_dir():
        for prefix_dir in objects_dir.iterdir():
            if prefix_dir.is_dir() and len(prefix_dir.name) == 2:
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        all_hashes.add(full_hash)

    # Orphans = all - referenced
    return list(all_hashes - referenced)


def _find_orphan_hashes(repo: Repository) -> list[str]:
    """Alias for _find_orphans."""
    return _find_orphans(repo)


def _attempt_repair(repo: Repository, errors: list[str]) -> int:
    """Attempt to repair repository issues."""
    repaired = 0

    for error in errors:
        if "Directory" in error and "tidak ditemukan" in error:
            # Missing directory
            dir_name = error.split("'")[1]
            dir_path = repo.vesi_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ Directory '{dir_name}' dibuat")
            repaired += 1

        elif "hash" in error.lower() and "rusak" in error.lower():
            # Corrupted object
            hash_str = error.split()[1] if len(error.split()) > 1 else ""
            if hash_str:
                # Try to find and remove corrupted object
                obj_path = repo.vesi_dir / "objects" / hash_str[:2] / hash_str[2:]
                if obj_path.is_file():
                    obj_path.unlink()
                    print(f"    ✓ Objek rusak '{hash_str}' dihapus")
                    repaired += 1

    return repaired


def _find_empty_dirs(start: Path) -> list[Path]:
    """Find empty directories recursively."""
    empty = []
    for item in start.rglob("*"):
        if item.is_dir() and not any(item.iterdir()):
            empty.append(item)
    return empty


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
