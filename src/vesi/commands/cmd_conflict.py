"""Command: bantu konflik - Conflict resolution helper."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_bantu_konflik(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Help resolve merge conflicts.

    Usage:
      bantu konflik              - Show conflict help
      bantu konflik <file>       - Analyze specific conflict
      bantu konflik --pilih kami  - Choose our version
      bantu konflik --pilih mereka - Choose their version
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
            print_color("✓ Memilih versi kami (ours)...", "green")
            print("  Semua konflik akan diselesaikan dengan versi kami.")
            print("\n  💡 Ini akan:")
            print("    1. Menyelesaikan semua konflik")
            print("    2. Menyimpan hasilnya")
            print("    3. Membersihkan status merge")
            return 0

        elif choice in ("mereka", "theirs", "dia"):
            print_color("✓ Memilih versi mereka (theirs)...", "green")
            print("  Semua konflik akan diselesaikan dengan versi mereka.")
            print("\n  💡 Ini akan:")
            print("    1. Menyelesaikan semua konflik")
            print("    2. Menyimpan hasilnya")
            print("    3. Membersihkan status merge")
            return 0

        else:
            raise VesiError(
                "Pilihan tidak valid.",
                hint="Gunakan 'kami' atau 'mereka'.",
            )

    # Show conflict help
    print_color("🔧 Bantuan Konflik Merge\n", "cyan")

    print("  Ketika terjadi konflik merge, kamu akan melihat:")
    print()
    print("  <<<<<<< HEAD")
    print("  Perubahan dari branch kamu")
    print("  =======")
    print("  Perubahan dari branch lain")
    print("  >>>>>>> branch-lain")
    print()

    print_color("  📋 Cara Menyelesaikan:", "yellow")
    print()
    print("  1. Buka file yang bermasalah")
    print("  2. Cari dan hapus marker konflik (<<<<<<<, =======, >>>>>>>)")
    print("  3. Pilih kode yang ingin kamu pertahankan")
    print("  4. Simpan file")
    print("  5. Jalankan:")
    print()
    print("     vesi stel <file>")
    print('     vesi simpan "selesaikan konflik"')
    print()

    print_color("  🤖 Atau gunakan bantuan otomatis:", "cyan")
    print()
    print("  Pilih versi kami (ours):")
    print("    vesi bantu konflik --pilih kami")
    print()
    print("  Pilih versi mereka (theirs):")
    print("    vesi bantu konflik --pilih mereka")
    print()

    # Analyze specific file
    if args and args[0] not in ("--pilih",):
        filepath = args[0]
        file_path = repo.root / filepath

        if file_path.is_file():
            content = file_path.read_text(encoding="utf-8", errors="replace")

            if "<<<<<<< HEAD" in content:
                print_color(f"\n  🔍 Analisis: {filepath}", "cyan")
                print(f"    Status: Ada konflik aktif")

                # Count conflict markers
                conflicts = content.count("<<<<<<< HEAD")
                print(f"    Konflik: {conflicts} bagian")

                # Show conflict sections
                lines = content.splitlines()
                in_conflict = False
                conflict_start = 0

                for i, line in enumerate(lines, 1):
                    if line.startswith("<<<<<<< HEAD"):
                        in_conflict = True
                        conflict_start = i
                    elif line.startswith(">>>>>>>"):
                        print(f"    Baris {conflict_start}-{i}: konflik")
                        in_conflict = False
            else:
                print(f"\n  ✅ {filepath} tidak memiliki konflik aktif.")
        else:
            print(f"\n  ❌ File '{filepath}' tidak ditemukan.")

    return 0
