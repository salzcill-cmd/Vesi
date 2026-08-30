"""Command: asisten gabung - Merge assistant with real conflict resolution."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_asisten_gabung(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Merge assistant - helps resolve merge conflicts.

    Usage:
      asisten gabung                      - Show merge help
      asisten gabung <file>               - Analyze specific conflict
      asisten gabung --pilih kami         - Choose our version for all
      asisten gabung --pilih mereka       - Choose their version for all
      asisten gabung --pilih gabung       - Combine both versions
      asisten gabung --selesaikan         - Auto-resolve simple conflicts
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    flags = parsed.flags

    # Check for resolution options
    if "--pilih" in flags:
        idx = flags.index("--pilih")
        choice = args[idx] if idx < len(args) else ""

        if choice in ("kami", "ours", "kita"):
            return _resolve_all_conflicts(repo, "ours")
        elif choice in ("mereka", "theirs", "dia"):
            return _resolve_all_conflicts(repo, "theirs")
        elif choice in ("gabung", "merge", "combine"):
            return _resolve_all_conflicts(repo, "combine")
        else:
            raise VesiError(
                "Pilihan tidak valid.",
                hint="Gunakan: kami, mereka, atau gabung",
            )

    # Auto-resolve simple conflicts
    if "--selesaikan" in flags or "--auto" in flags:
        return _auto_resolve_simple(repo)

    # Show detailed merge help
    print_color("🤖 Asisten Gabung - Bantuan Merge Conflict\n", "cyan")
    print("━" * 60)

    print("\n  📋 Apa itu Merge Conflict?")
    print("  Konflik terjadi ketika dua branch mengubah bagian yang sama.")
    print("  Vesi tidak tahu versi mana yang benar, jadi kamu harus memilih.")

    print(f"\n{'━' * 60}")
    print_color("  🔍 Cara Kerja Asisten:\n", "yellow")
    print("  1. Menganalisis file yang konflik")
    print("  2. Menunjukkan perbedaan antara kedua versi")
    print("  3. Memberikan saran resolusi")
    print("  4. Membantu menerapkan pilihan kamu")

    print(f"\n{'━' * 60}")
    print_color("  🛠️  Perintah yang Tersedia:\n", "green")
    print("  asisten gabung                  Tampilkan bantuan ini")
    print("  asisten gabung <file>           Analisis konflik di file")
    print("  asisten gabung --selesaikan     Auto-resolve konflik sederhana")
    print("  asisten gabung --pilih kami     Pilih versi kami")
    print("  asisten gabung --pilih mereka   Pilih versi mereka")
    print("  asisten gabung --pilih gabung   Gabungkan kedua versi")

    print(f"\n{'━' * 60}")
    print_color("  📖 Contoh Konflik:\n", "yellow")
    print("  <<<<<<< HEAD")
    print("  Kode dari branch kami")
    print("  =======")
    print("  Kode dari branch lain")
    print("  >>>>>>> branch-lain")

    print(f"\n{'━' * 60}")
    print_color("  💡 Tips Resolusi:\n", "cyan")
    print("  1. Baca kedua versi dengan teliti")
    print("  2. Pahami tujuan masing-masing perubahan")
    print("  3. Pilih yang paling cocok, atau gabungkan")
    print("  4. Test setelah resolusi")
    print("  5. Commit hasil resolusi")

    # Analyze specific file
    if args and args[0] not in ("--pilih", "--selesaikan", "--auto"):
        filepath = args[0]
        _analyze_conflict_file(repo, filepath)

    return 0


def _find_conflict_files(repo: Repository) -> list[Path]:
    """Find all files with merge conflict markers."""
    conflict_files = []

    # Check MERGE_CONFLICTS file first
    conflicts_path = repo.vesi_dir / "MERGE_CONFLICTS"
    if conflicts_path.is_file():
        try:
            paths = json.loads(conflicts_path.read_text(encoding="utf-8"))
            for p in paths:
                fpath = repo.root / p
                if fpath.is_file():
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    if "<<<<<<< HEAD" in content:
                        conflict_files.append(fpath)
        except (json.JSONDecodeError, OSError):
            pass

    # Also scan working directory
    if not conflict_files:
        for fpath in repo.root.rglob("*"):
            if fpath.is_file() and ".vesi" not in str(fpath):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    if "<<<<<<< HEAD" in content:
                        conflict_files.append(fpath)
                except (OSError, UnicodeDecodeError):
                    pass

    return conflict_files


def _parse_conflict_sections(content: str) -> list[dict]:
    """Parse conflict sections from a file.

    Returns list of dicts with 'ours', 'theirs', 'start', 'end' keys.
    """
    lines = content.split("\n")
    sections = []
    current_section = None

    for i, line in enumerate(lines):
        if line.startswith("<<<<<<< HEAD"):
            current_section = {
                "ours": [],
                "theirs": [],
                "start": i,
                "phase": "ours",
            }
        elif line.startswith("=======") and current_section:
            current_section["phase"] = "theirs"
        elif line.startswith(">>>>>>>") and current_section:
            current_section["end"] = i
            sections.append(current_section)
            current_section = None
        elif current_section:
            if current_section["phase"] == "ours":
                current_section["ours"].append(line)
            else:
                current_section["theirs"].append(line)

    return sections


def _resolve_all_conflicts(repo: Repository, strategy: str) -> int:
    """Resolve all conflicts in all files using the given strategy."""
    conflict_files = _find_conflict_files(repo)

    if not conflict_files:
        print_color("✓ Tidak ada konflik aktif.", "green")
        return 0

    resolved_count = 0

    for file_path in conflict_files:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        sections = _parse_conflict_sections(content)

        if not sections:
            continue

        # Resolve each conflict section
        new_lines = content.split("\n")
        offset = 0

        for section in sections:
            start = section["start"] + offset
            end = section["end"] + offset

            if strategy == "ours":
                replacement = "\n".join(section["ours"])
            elif strategy == "theirs":
                replacement = "\n".join(section["theirs"])
            elif strategy == "combine":
                # Combine both, preferring ours with theirs appended
                combined = section["ours"] + ["", "--- gabungan ---", ""] + section["theirs"]
                replacement = "\n".join(combined)
            else:
                continue

            # Replace conflict section
            new_lines[start:end + 1] = replacement.split("\n")
            offset += len(replacement.split("\n")) - (end - start + 1)

        # Write resolved content
        new_content = "\n".join(new_lines)
        file_path.write_text(new_content, encoding="utf-8")
        resolved_count += 1

        # Stage the resolved file
        rel_path = str(file_path.relative_to(repo.root))
        blob_hash = repo.blobs.save_file(file_path)
        repo.index.stage_file(rel_path, blob_hash)

        print(f"  ✓ {rel_path}")

    strategy_names = {
        "ours": "versi kami",
        "theirs": "versi mereka",
        "combine": "gabungan",
    }

    print_color(f"\n✓ {resolved_count} file diselesaikan (strategi: {strategy_names.get(strategy, strategy)})", "green")
    print(f"\n  Selanjutnya:")
    print(f"    lanjutkan gabungan")

    return 0


def _auto_resolve_simple(repo: Repository) -> int:
    """Auto-resolve simple conflicts where one side is empty or identical."""
    conflict_files = _find_conflict_files(repo)

    if not conflict_files:
        print_color("✓ Tidak ada konflik aktif.", "green")
        return 0

    resolved_count = 0

    for file_path in conflict_files:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        sections = _parse_conflict_sections(content)

        if not sections:
            continue

        new_lines = content.split("\n")
        offset = 0
        file_resolved = True

        for section in sections:
            start = section["start"] + offset
            end = section["end"] + offset

            # Check if one side is empty
            if not section["ours"].strip():
                # Our side is empty: take theirs
                replacement = "\n".join(section["theirs"])
            elif not section["theirs"].strip():
                # Their side is empty: take ours
                replacement = "\n".join(section["ours"])
            elif section["ours"] == section["theirs"]:
                # Both sides identical: take either
                replacement = "\n".join(section["ours"])
            else:
                # Can't auto-resolve
                file_resolved = False
                continue

            new_lines[start:end + 1] = replacement.split("\n")
            offset += len(replacement.split("\n")) - (end - start + 1)

        if file_resolved:
            new_content = "\n".join(new_lines)
            file_path.write_text(new_content, encoding="utf-8")
            resolved_count += 1

            rel_path = str(file_path.relative_to(repo.root))
            blob_hash = repo.blobs.save_file(file_path)
            repo.index.stage_file(rel_path, blob_hash)
            print(f"  ✓ {rel_path}")

    if resolved_count:
        print_color(f"\n✓ {resolved_count} file diselesaikan otomatis", "green")
        remaining = len(conflict_files) - resolved_count
        if remaining > 0:
            print(f"  ⚠ {remaining} file masih memiliki konflik kompleks")
            print(f"  Gunakan 'asisten gabung --pilih kami/mereka/gabung'")
        else:
            print(f"\n  Semua konflik selesai!")
            print(f"  Selanjutnya:")
            print(f"    lanjutkan gabungan")
    else:
        print_color("⚠ Tidak ada konflik sederhana yang bisa diselesaikan otomatis.", "yellow")
        print("  Gunakan 'asisten gabung --pilih kami/mereka/gabung'")

    return 0


def _analyze_conflict_file(repo: Repository, filepath: str) -> None:
    """Analyze a specific conflict file."""
    file_path = repo.root / filepath

    if not file_path.is_file():
        print(f"\n  ❌ File '{filepath}' tidak ditemukan.")
        return

    content = file_path.read_text(encoding="utf-8", errors="replace")

    if "<<<<<<< HEAD" not in content:
        print(f"\n  ✅ {filepath} tidak memiliki konflik aktif.")
        return

    sections = _parse_conflict_sections(content)
    total_conflicts = len(sections)

    print(f"\n{'━' * 60}")
    print_color(f"  🔍 Analisis: {filepath}\n", "cyan")
    print(f"  Status: Ada konflik aktif")
    print(f"  Konflik: {total_conflicts} bagian")
    print()

    for i, section in enumerate(sections, 1):
        print(f"  {'─' * 50}")
        print_color(f"  Konflik #{i}:", "yellow")
        print(f"    Baris {section['start'] + 1}-{section['end'] + 1}")
        print(f"    Versi kami: {len(section['ours'])} baris")
        print(f"    Versi mereka: {len(section['theirs'])} baris")

        # Analyze
        if section['ours'] == section['theirs']:
            print(f"    💡 Kedua versi IDENTIK - bisa diambil mana saja")
        elif not section['ours'].strip():
            print(f"    💡 Versi kami KOSONG - ambil versi mereka")
        elif not section['theirs'].strip():
            print(f"    💡 Versi mereka KOSONG - ambil versi kami")
        elif len(section['ours']) == len(section['theirs']):
            print(f"    💡 Sama panjang - perbedaan mungkin kecil")
        else:
            print(f"    💡 Panjang berbeda - perlu review manual")

        # Show content preview
        print(f"\n    Versi kami (3 baris pertama):")
        for line in section['ours'][:3]:
            print(f"      {line}")
        if len(section['ours']) > 3:
            print(f"      ... ({len(section['ours']) - 3} baris lagi)")

        print(f"\n    Versi mereka (3 baris pertama):")
        for line in section['theirs'][:3]:
            print(f"      {line}")
        if len(section['theirs']) > 3:
            print(f"      ... ({len(section['theirs']) - 3} baris lagi)")

    print(f"\n{'━' * 60}")
    print_color("  🛠️  Opsi Resolusi:\n", "green")
    print(f"  asisten gabung --pilih kami     Ambil versi kami")
    print(f"  asisten gabung --pilih mereka   Ambil versi mereka")
    print(f"  asisten gabung --pilih gabung   Gabungkan keduanya")
