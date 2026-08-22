"""Command: bantuan - Show help information."""

from __future__ import annotations

from vesi.parser.parser import ParsedCommand


# Help text for each command
HELP_TEXT: dict[str, str] = {
    "mulai": """NAMA: mulai proyek
TUJUAN: Membuat repository baru di direktori saat ini
SINTAKS: mulai [proyek] [nama]
CONTOH:
    mulai
    mulai proyek
    mulai proyek "tugas-sekolah\"""",
    "lihat": """NAMA: lihat
TUJUAN: Melihat informasi tentang repository

Sub-perintah:
  lihat perubahan    Lihat file yang berubah (= status)
  lihat riwayat      Lihat daftar versi (= riwayat, log)
  lihat cabang       Lihat semua cabang (= cabang)

CONTOH:
    lihat perubahan
    lihat riwayat
    lihat riwayat 20
    lihat cabang""",
    "stel": """NAMA: stel
TUJUAN: Menyiapkan file untuk disimpan dalam versi berikutnya
SINTAKS: stel <file> | stel .
ALIAS: siap, add, stage
CONTOH:
    stel main.py
    stel src/
    stel . (semua file yang berubah)""",
    "simpan": """NAMA: simpan versi
TUJUAN: Menyimpan snapshot dari file yang di-stage
SINTAKS: simpan "pesan" | simpan versi "pesan"
ALIAS: save, commit
CONTOH:
    simpan "halaman login selesai"
    simpan versi "tugas matematika awal\"""",
    "bandingkan": """NAMA: bandingkan
TUJUAN: Menampilkan perbedaan antara versi atau working directory
SINTAKS: bandingkan [versi1] [versi2]
ALIAS: diff, perbedaan
CONTOH:
    bandingkan
    bandingkan a1b2c3d f4e5d6a""",
    "pulihkan": """NAMA: pulihkan
TUJUAN: Mengembalikan file ke keadaan dari versi tertentu
SINTAKS: pulihkan <file> [dari <versi>]
ALIAS: restore
CONTOH:
    pulihkan main.py
    pulihkan main.py dari a1b2c3d""",
    "batalkan": """NAMA: batalkan
TUJUAN: Membatalkan perubahan atau penggabungan

Sub-perintah:
  batalkan perubahan <file>    Batalkan perubahan file (= batal)
  batalkan gabungan            Batalkan merge yang sedang berlangsung

CONTOH:
    batalkan perubahan main.py
    batal main.py
    batalkan gabungan""",
    "buat": """NAMA: buat cabang
TUJUAN: Membuat branch baru
SINTAKS: buat cabang <nama> | cabang baru <nama>
CONTOH:
    buat cabang fitur-login
    cabang baru fitur-login""",
    "pindah": """NAMA: pindah cabang
TUJUAN: Beralih ke cabang lain
SINTAKS: pindah cabang <nama> | cabang pindah <nama>
CONTOH:
    pindah cabang fitur-login
    cabang pindah fitur-login""",
    "hapus": """NAMA: hapus cabang
TUJUAN: Menghapus cabang
SINTAKS: hapus cabang <nama> | cabang hapus <nama>
CONTOH:
    hapus cabang percobaan
    cabang hapus percobaan""",
    "gabungkan": """NAMA: gabungkan
TUJUAN: Menggabungkan branch ke branch aktif
SINTAKS: gabungkan <cabang> | gabung <cabang>
CONTOH:
    gabungkan fitur-login
    gabung fitur-login""",
    "cek": """NAMA: cek
TUJUAN: Memverifikasi integritas repository
SINTAKS: cek
ALIAS: check, verify, fsck""",
    "konfigurasi": """NAMA: konfigurasi
TUJUAN: Mengelola pengaturan repository
SINTAKS: konfigurasi [key] [value]
ALIAS: config, set
CONTOH:
    konfigurasi
    konfigurasi user.name
    konfigurasi user.name "Nama Anda"
    konfigurasi user.email "email@contoh.com\"""",
    "bantuan": """NAMA: bantuan
TUJUAN: Menampilkan panduan penggunaan
SINTAKS: bantuan [command]
ALIAS: help, ?
CONTOH:
    bantuan
    bantuan simpan""",
    "jelaskan": """NAMA: jelaskan
TUJUAN: Menjelaskan konsep version control
SINTAKS: jelaskan <konsep>
ALIAS: explain, apa
CONTOH:
    jelaskan versi
    jelaskan cabang
    jelaskan konflik""",
}


def cmd_bantuan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show help information."""
    if parsed.args:
        # Show help for specific command
        command = parsed.args[0]
        # Find matching help text
        for key, text in HELP_TEXT.items():
            if command.startswith(key) or key.startswith(command):
                print(text)
                return 0

        print(f"Tidak ada bantuan untuk command '{command}'.")
        print("\nGunakan 'bantuan' untuk melihat semua command.")
        return 1

    # Show general help
    print("vesi — Version control yang gampang dipelajari\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  CEPAT MULAI                                            ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  mulai                  Buat repository baru            ║")
    print("║  stel .                 Siapkan semua file              ║")
    print('║  simpan "pesan"         Simpan versi                    ║')
    print("║  lihat riwayat          Lihat daftar versi              ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    print("SEMUA COMMAND:\n")
    print("  ── Repository ──")
    print("  mulai [proyek]          Buat repository baru")
    print("  status                  Lihat file yang berubah")
    print("  cek                     Periksa integritas repository")
    print("  konfigurasi             Kelola pengaturan\n")
    print("  ── Menyimpan ──")
    print("  stel <file>             Siapkan file (= siap, add)")
    print('  simpan "pesan"          Simpan versi (= save, commit)')
    print("  riwayat                 Lihat daftar versi (= log)")
    print("  bandingkan              Lihat perbedaan (= diff)\n")
    print("  ── Memulihkan ──")
    print("  pulihkan <file>         Kembalikan file (= restore)")
    print("  batal <file>            Batalkan perubahan (= undo)\n")
    print("  ── Cabang ──")
    print("  cabang baru <nama>      Buat cabang baru")
    print("  cabang                  Lihat semua cabang")
    print("  cabang pindah <nama>    Pindah ke cabang lain")
    print("  cabang hapus <nama>     Hapus cabang")
    print("  gabung <nama>           Gabungkan cabang\n")
    print("  ── Lainnya ──")
    print("  bantuan                 Tampilkan bantuan ini (= help)")
    print("  jelaskan <konsep>       Pelajari konsep (= explain)\n")
    print("Gunakan 'vesi bantuan <command>' untuk detail.\n")
    print("Opsi:")
    print("  --version               Tampilkan versi")
    print("  --verbose               Output detail")
    print("  --debug                 Debug information")
    print("  --json                  Output dalam format JSON")
    print("  --no-color              Tanpa warna\n")
    print("Contoh workflow:")
    print("  vesi mulai")
    print("  vesi stel .")
    print('  vesi simpan "inisialisasi"')
    print("  vesi status")
    print("  vesi riwayat")

    return 0
