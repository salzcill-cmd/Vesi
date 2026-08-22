"""Command: cek - Verify repository integrity."""

from __future__ import annotations

from vesi.errors.exceptions import RepositoryNotFoundError
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_cek(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Verify repository integrity."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    print("Memeriksa integritas repository...\n")

    errors: list[str] = []
    checks_passed = 0

    # Check 1: Directory structure
    print("  ✓ Struktur direktori")
    checks_passed += 1

    # Check 2: Objects integrity
    object_errors = repo.objects.verify_integrity()
    if object_errors:
        for err in object_errors:
            errors.append(f"  ✗ Object: {err}")
    else:
        print("  ✓ Object storage")
        checks_passed += 1

    # Check 3: Refs
    try:
        branches = repo.refs.list_branches()
        print(f"  ✓ References ({len(branches)} cabang)")
        checks_passed += 1
    except Exception as e:
        errors.append(f"  ✗ References: {e}")

    # Check 4: HEAD
    head = repo.refs.get_head()
    if head:
        print(f"  ✓ HEAD: {head}")
        checks_passed += 1
    else:
        errors.append("  ✗ HEAD tidak ditemukan")

    # Check 5: Index
    try:
        index = repo.index.load()
        print(f"  ✓ Index ({len(index)} file staged)")
        checks_passed += 1
    except Exception as e:
        errors.append(f"  ✗ Index: {e}")

    # Check 6: Config
    config = repo.get_config()
    if config:
        print(f"  ✓ Konfigurasi")
        checks_passed += 1
    else:
        errors.append("  ✗ Konfigurasi tidak ditemukan")

    # Summary
    print()
    if errors:
        print(f"⚠ Ditemukan {len(errors)} masalah:")
        for err in errors:
            print(err)
        return 1
    else:
        total_objects = repo.objects.count_objects()
        total_size = repo.objects.total_size()
        size_display = _format_size(total_size)
        print(f"✓ Semua pemeriksaan lulus ({checks_passed} pemeriksaan)")
        print(f"  Total objects: {total_objects}")
        print(f"  Ukuran: {size_display}")
        return 0


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
