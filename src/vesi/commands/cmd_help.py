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
    # Tag commands
    "beri": (
        "NAMA: beri tag\n"
        "TUJUAN: Memberi tag pada versi tertentu\n"
        "SINTAKS: beri tag <nama> [pesan]\n"
        "CONTOH:\n"
        "    beri tag v1.0.0\n"
        '    beri tag v1.0.0 "Rilis pertama"'
    ),
    "tag": """NAMA: lihat tag
TUJUAN: Menampilkan daftar tag
SINTAKS: lihat tag | tag""",
    # Stash commands
    "simpan": (
        "NAMA: simpan versi\n"
        "TUJUAN: Menyimpan snapshot dari file yang di-stage\n"
        'SINTAKS: simpan "pesan" | simpan versi "pesan"\n'
        "ALIAS: save, commit\n\n"
        "Sub-perintah:\n"
        '  simpan "pesan"          Simpan versi (commit)\n'
        "  simpan --amend          Ubah commit terakhir\n"
        "  simpan sementara        Simpan perubahan sementara (stash)\n\n"
        "CONTOH:\n"
        '    simpan "halaman login selesai"\n'
        '    simpan versi "tugas matematika awal"\n'
        '    simpan sementara "perubahan sementara"'
    ),
    "ambil": """NAMA: ambil
TUJUAN: Mengambil stash atau commit tertentu

Sub-perintah:
  ambil stash             Ambil stash terakhir (pop)
  ambil versi <commit>    Cherry-pick commit tertentu

CONTOH:
    ambil stash
    ambil versi a1b2c3d""",
    "lihat": """NAMA: lihat
TUJUAN: Melihat informasi tentang repository

Sub-perintah:
  lihat perubahan    Lihat file yang berubah (= status)
  lihat riwayat      Lihat daftar versi (= riwayat, log)
  lihat cabang       Lihat semua cabang (= cabang)
  lihat tag          Lihat semua tag
  lihat stash        Lihat stash tersimpan

CONTOH:
    lihat perubahan
    lihat riwayat
    lihat riwayat 20
    lihat cabang
    lihat tag
    lihat stash""",
    # Rebase command
    "susun": """NAMA: susun ulang
TUJUAN: Menyatukan beberapa commit menjadi satu (rebase/squash)
SINTAKS: susun ulang [jumlah]
ALIAS: rebase, squash
CONTOH:
    susun ulang          Gabungkan 2 commit terakhir
    susun ulang 3        Gabungkan 3 commit terakhir""",
    # Blame command
    "siapa": """NAMA: siapa ubah
TUJUAN: Melihat siapa yang mengubah setiap baris kode (blame)
SINTAKS: siapa ubah <file>
ALIAS: blame, annotate
CONTOH:
    siapa ubah main.py""",
    # Bisect command
    "bagi": """NAMA: bagi cari
TUJUAN: Mencari commit yang menyebabkan bug (bisect)
SINTAKS: bagi cari [mulai|baik|buruk|selesai]
ALIAS: bisect

Sub-perintah:
  bagi cari mulai <baik> <buruk>   Mulai sesi bisect
  bagi cari baik                   Tandai commit saat ini baik
  bagi cari buruk                  Tandai commit saat ini buruk
  bagi cari selesai                Akhiri sesi bisect

CONTOH:
    bagi cari mulai a1b2c3d f4e5d6a
    bagi cari baik
    bagi cari buruk""",
    # Reflog command
    "jejak": """NAMA: jejak
TUJUAN: Menampilkan riwayat pergerakan HEAD (reflog)
SINTAKS: jejak [jumlah]
ALIAS: reflog
CONTOH:
    jejak              Tampilkan semua jejak
    jejak 20           Tampilkan 20 jejak terakhir""",
    # Worktree command
    "folder": """NAMA: folder kerja
TUJUAN: Mengelola worktree (checkout branch di folder berbeda)
SINTAKS: folder kerja [buat|hapus] <path> <branch>
ALIAS: worktree

Sub-perintah:
  folder kerja                      Lihat semua worktree
  folder kerja buat <path> <branch> Buat worktree baru
  folder kerja hapus <path>         Hapus worktree

CONTOH:
    folder kerja buat ../project-v2 fitur-baru
    folder kerja
    folder kerja hapus ../project-v2""",
    # Undo commit
    "batalkan": (
        "NAMA: batalkan\n"
        "TUJUAN: Membatalkan perubahan, commit, atau merge\n\n"
        "Sub-perintah:\n"
        "  batalkan perubahan <file>    Batalkan perubahan file\n"
        "  batalkan gabungan            Batalkan merge\n"
        "  batalkan versi               Undo commit terakhir\n\n"
        "CONTOH:\n"
        "    batalkan perubahan main.py\n"
        "    batalkan gabungan\n"
        "    batalkan versi"
    ),
    # Backup
    "cadangan": """NAMA: cadangan
TUJUAN: Sistem backup otomatis sebelum operasi destruktif
SINTAKS: cadangan [buat|pulihkan] [alasan]
ALIAS: backup

Sub-perintah:
  cadangan                      Lihat semua backup
  cadangan buat [alasan]        Buat backup baru
  cadangan pulihkan <id>        Pulihkan dari backup

CONTOH:
    cadangan buat
    cadangan buat "sebelum refactor"
    cadangan pulihkan backup_1234567890""",
    # Commit templates
    "pola": """NAMA: pola commit
TUJUAN: Template pesan commit yang konsisten
SINTAKS: pola commit [type] [deskripsi]
ALIAS: template

Type yang tersedia:
  feat      Fitur baru
  fix       Perbaikan bug
  docs      Dokumentasi
  style     Style/format
  refactor  Refactor kode
  test      Test
  chore     Maintenance
  breaking  Breaking change

CONTOH:
    pola commit
    pola commit feat
    pola commit feat 'tambah login'
""",
    # File insights
    "lihat": """NAMA: lihat
TUJUAN: Melihat informasi tentang repository

Sub-perintah:
  lihat perubahan    Lihat file yang berubah
  lihat riwayat      Lihat daftar versi
  lihat cabang       Lihat semua cabang
  lihat tag          Lihat semua tag
  lihat stash        Lihat stash tersimpan
  lihat file         Lihat statistik file
  cari riwayat       Cari dalam riwayat commit

CONTOH:
    lihat perubahan
    lihat riwayat
    lihat file main.py
    cari riwayat login""",
    # Smart diff
    "bandingkan": """NAMA: bandingkan
TUJUAN: Menampilkan perbedaan antara versi atau working directory
SINTAKS: bandingkan [pintar] [versi1] [versi2]
ALIAS: diff

Sub-perintah:
  bandingkan              Diff biasa
  bandingkan pintar       Diff dengan ringkasan
  bandingkan pintar --stat - Hanya statistik

CONTOH:
    bandingkan
    bandingkan pintar
    bandingkan pintar --stat""",
    # Conflict helper
    "bantu": """NAMA: bantu konflik
TUJUAN: Membantu menyelesaikan merge conflict
SINTAKS: bantu konflik [file] [--pilih kami|mereka]
ALIAS: help

Sub-perintah:
  bantu konflik              Tampilkan panduan konflik
  bantu konflik <file>       Analisis konflik di file
  bantu konflik --pilih kami   Pilih versi kami
  bantu konflik --pilih mereka Pilih versi mereka

CONTOH:
    bantu konflik
    bantu konflik main.py
    bantu konflik --pilih kami""",
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
    print("  konfigurasi             Kelola pengaturan")
    print("  jejak                   Riwayat pergerakan HEAD\n")
    print("  ── Menyimpan ──")
    print("  stel <file>             Siapkan file (= siap, add)")
    print('  simpan "pesan"          Simpan versi (= save, commit)')
    print("  simpan sementara        Simpan perubahan sementara (stash)")
    print("  riwayat                 Lihat daftar versi (= log)")
    print("  bandingkan              Lihat perbedaan (= diff)\n")
    print("  ── Memulihkan ──")
    print("  pulihkan <file>         Kembalikan file (= restore)")
    print("  batal <file>            Batalkan perubahan (= undo)")
    print("  ambil stash             Ambil stash tersimpan")
    print("  ambil versi <commit>    Cherry-pick commit\n")
    print("  ── Cabang ──")
    print("  cabang baru <nama>      Buat cabang baru")
    print("  cabang                  Lihat semua cabang")
    print("  cabang pindah <nama>    Pindah ke cabang lain")
    print("  cabang hapus <nama>     Hapus cabang")
    print("  gabung <nama>           Gabungkan cabang")
    print("  folder kerja             Kelola worktree\n")
    print("  ── Tag ──")
    print("  beri tag <nama>         Tandai versi penting")
    print("  lihat tag               Lihat semua tag")
    print("  hapus tag <nama>        Hapus tag\n")
    print("  ── Analisis ──")
    print("  siapa ubah <file>       Lihat siapa ubah baris (blame)")
    print("  bagi cari               Cari commit bug (bisect)")
    print("  susun ulang             Gabungkan commit (rebase)")
    print("  cari riwayat            Cari dalam riwayat commit")
    print("  lihat file <file>       Lihat statistik file\n")
    print("  ── Canggih ──")
    print("  batalkan versi          Undo commit terakhir")
    print("  bandingkan pintar       Diff dengan ringkasan")
    print("  cadangan buat           Buat backup otomatis")
    print("  pola commit             Template pesan commit")
    print("  bantu konflik           Bantu selesaikan konflik\n")
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
