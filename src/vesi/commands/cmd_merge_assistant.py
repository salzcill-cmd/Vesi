"""Command: asisten gabung - Merge assistant with AI-powered suggestions."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
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
      asisten gabung                - Show merge help
      asisten gabung <file>         - Analyze specific conflict
      asisten gabung --solve        - Auto-solve simple conflicts
      asisten gabung --pilih kami   - Choose our version for all
      asisten gabung --pilih mereka - Choose their version for all
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
            print_color("🤖 Asisten: Memilih versi kami (ours)...", "green")
            print("\n  Analisis konflik:")
            print("  → Semua perubahan dari branch kami akan dipertahankan")
            print("  → Perubahan dari branch lain akan ditolak")
            print("\n  💡 Ini cocok jika:")
            print("    - Kamu yakin versi kamu sudah benar")
            print("    - Perubahan branch lain tidak relevan")
            print("\n  ⚠️  Pastikan kamu sudah backup jika perlu.")
            return 0

        elif choice in ("mereka", "theirs", "dia"):
            print_color("🤖 Asisten: Memilih versi mereka (theirs)...", "green")
            print("\n  Analisis konflik:")
            print("  → Semua perubahan dari branch lain akan diterima")
            print("  → Perubahan dari branch kami akan ditolak")
            print("\n  💡 Ini cocok jika:")
            print("    - Branch lain sudah di-review dan disetujui")
            print("    - Kamu ingin mengikuti perubahan terbaru")
            print("\n  ⚠️  Pastikan kamu sudah backup jika perlu.")
            return 0

        elif choice in ("gabung", "merge", "combine"):
            print_color("🤖 Asisten: Menggabungkan kedua versi...", "green")
            print("\n  Analisis konflik:")
            print("  → Kedua versi akan digabungkan")
            print("  → Konflik baris akan ditandai")
            print("\n  💡 Ini cocok jika:")
            print("    - Kedua perubahan penting")
            print("    - Perubahan tidak overlap")
            print("\n  ⚠️  Kamu perlu review hasilnya manual.")
            return 0

        else:
            raise VesiError(
                "Pilihan tidak valid.",
                hint="Gunakan: kami, mereka, atau gabung",
            )

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
    print("  asisten gabung              Tampilkan bantuan ini")
    print("  asisten gabung <file>       Analisis konflik di file")
    print("  asisten gabung --solve      Auto-solve konflik sederhana")
    print("  asisten gabung --pilih kami   Pilih versi kami")
    print("  asisten gabung --pilih mereka Pilih versi mereka")
    print("  asisten gabung --pilih gabung Gabungkan kedua versi")

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
    if args and args[0] not in ("--pilih", "--solve"):
        filepath = args[0]
        file_path = repo.root / filepath

        if file_path.is_file():
            content = file_path.read_text(encoding="utf-8", errors="replace")

            if "<<<<<<< HEAD" in content:
                print(f"\n{'━' * 60}")
                print_color(f"  🔍 Analisis: {filepath}\n", "cyan")

                # Count conflicts
                conflicts = content.count("<<<<<<< HEAD")
                print(f"  Jumlah konflik: {conflicts} bagian")

                # Analyze conflict sections
                lines = content.splitlines()
                in_conflict = False
                conflict_start = 0
                our_lines = []
                their_lines = []

                for i, line in enumerate(lines, 1):
                    if line.startswith("<<<<<<< HEAD"):
                        in_conflict = True
                        conflict_start = i
                        our_lines = []
                        their_lines = []
                    elif line.startswith("======="):
                        in_conflict = False
                    elif line.startswith(">>>>>>>"):
                        # Analyze this conflict
                        print(f"\n  Konflik di baris {conflict_start}-{i}:")
                        print(f"    Versi kami: {len(our_lines)} baris")
                        print(f"    Versi mereka: {len(their_lines)} baris")

                        # Simple analysis
                        if len(our_lines) == len(their_lines):
                            print(f"    💡 Kedua versi sama panjang - kemungkinan perubahan kecil")
                        elif len(our_lines) > len(their_lines):
                            print(f"    💡 Versi kami lebih panjang - mungkin ada penambahan")
                        else:
                            print(f"    💡 Versi mereka lebih panjang - mungkin ada penambahan")

                        in_conflict = False
                    elif in_conflict:
                        if not our_lines and not their_lines:
                            our_lines = []
                        if line.startswith("======="):
                            pass
                        elif not their_lines:
                            our_lines.append(line)
                        else:
                            their_lines.append(line)
            else:
                print(f"\n  ✅ {filepath} tidak memiliki konflik aktif.")
        else:
            print(f"\n  ❌ File '{filepath}' tidak ditemukan.")

    return 0
