"""Command: jelaskan - Educational: explain version control concepts."""

from __future__ import annotations

from vesi.parser.parser import ParsedCommand


# Concept explanations
CONCEPTS: dict[str, str] = {
    "versi": """Apa itu "versi" (commit)?

Versi (commit) adalah "foto" dari kondisi proyek kamu pada waktu tertentu.

Bayangkan kamu menulis surat. Setiap kali kamu menyimpan perubahan,
vesi mencatat:
  - Siapa yang membuat perubahan
  - Kapan perubahan dibuat
  - Pesan tentang apa yang berubah

Kamu bisa kembali ke versi mana saja kapan saja.
Ini seperti "undo" yang sangat kuat!

Contoh:
  simpan versi "halaman login selesai"
  lihat riwayat

Istilah teknis: commit, snapshot""",

    "cabang": """Apa itu "cabang" (branch)?

Cabang adalah jalur pengembangan paralel.

Bayangkan kamu sedang menulis buku. Kamu ingin mencoba bab baru,
tapi tidak yakin apakah itu bagus. Dengan cabang:
  1. Buat cabang baru: "cabang baru bab-baru"
  2. Kerja di cabang baru itu
  3. Jika bagus, gabungkan: "gabung bab-baru"
  4. Jika tidak bagus, hapus: "cabang hapus bab-baru"

Cabang utama (default) disebut "utama".

Contoh:
  cabang baru fitur-baru
  cabang pindah fitur-baru
  ... kerja ...
  cabang pindah utama
  gabung fitur-baru

Istilah teknis: branch""",

    "gabungan": """Apa itu "gabungan" (merge)?

Gabungan adalah menggabungkan perubahan dari dua cabang.

Ketika kamu selesai mengerjakan fitur di cabang baru,
kamu perlu menggabungkannya ke cabang utama.

Tipe gabungan:
  1. Fast-forward: Jika cabang utama belum berubah,
     cukup pindahkan pointer.
  2. Three-way merge: Jika kedua cabang berubah,
     vesi menggabungkan perubahan secara otomatis.

Jika ada konflik (kedua cabang mengubah bagian yang sama),
vesi akan memberitahu file mana yang konflik.

Contoh:
  gabung fitur-login

Istilah teknis: merge""",

    "staging": """Apa itu "staging" (persiapan)?

Staging adalah menyiapkan file sebelum disimpan.

Bayangkan kamu ingin mengirim paket. Sebelum dikirim:
  1. Pilih barang yang akan dikirim (stel file)
  2. Kemas dalam kotak (simpan versi)

Kenapa tidak langsung simpan semua?
  - Kamu mungkin hanya ingin menyimpan beberapa file
  - Kamu bisa membuat pesan yang lebih spesifik

Contoh:
  stel main.py          # Siapkan main.py
  stel src/             # Siapkan semua file di src/
  stel .                # Siapkan semua perubahan
  simpan versi "pesan"

Istilah teknis: staging, index""",

    "riwayat": """Apa itu "riwayat" (history)?

Riwayat adalah daftar semua versi yang pernah disimpan.

Kamu bisa melihat:
  - Kapan setiap perubahan dibuat
  - Siapa yang membuat perubahan
  - Pesan deskriptif untuk setiap perubahan
  - File mana saja yang berubah

Contoh:
  riwayat
  riwayat 20      # Tampilkan 20 versi terakhir

Istilah teknis: log, history""",

    "perbandingan": """Apa itu "perbandingan" (diff)?

Perbandingan menunjukkan perbedaan antara dua versi.

Ketika kamu melihat perbandingan:
  - Baris yang ditambahkan ditampilkan dengan +
  - Baris yang dihapus ditampilkan dengan -
  - Baris yang tidak berubah tidak ditampilkan

Contoh:
  diff                      # vs versi terakhir
  diff a1b2c3d f4e5d6a      # antara dua versi

Istilah teknis: diff""",

    "hash": """Apa itu "hash"?

Hash adalah kode unik yang dihasilkan dari isi file.

Setiap file memiliki hash unik berdasarkan SHA-256.
Jika isi file berubah sedikit saja, hash-nya berubah total.

Ini memastikan:
  - Integritas data (file tidak rusak)
  - Penyimpanan efisien (file sama = hash sama)
  - Keamanan (sulit memalsukan file)

Istilah teknis: SHA-256, content hash""",

    "repository": """Apa itu "repository"?

Repository adalah folder yang dikelola oleh vesi.

Ketika kamu menjalankan "mulai proyek", vesi membuat:
  - Folder .vesi/ (penyimpanan internal)
  - File .abaikan (daftar file yang diabaikan)

Semua file di folder utama (selain .vesi) adalah
bagian dari repository.

Istilah teknis: repository, repo""",

    "head": """Apa itu "HEAD"?

HEAD adalah referensi ke versi terakhir di cabang aktif.

Bayangkan HEAD seperti penanda buku:
  - Selalu menunjuk ke "kamu di sini"
  - Setiap kali kamu menyimpan versi baru, HEAD berpindah

Jika HEAD tersembunyi (detached), kamu melihat versi tertentu
bukan di cabang manapun.

Istilah teknis: HEAD""",

    "konflik": """Apa itu "konflik" (merge conflict)?

Konflik terjadi ketika dua cabang mengubah bagian yang sama dari file.

Ketika vesi tidak bisa menggabungkan perubahan secara otomatis,
dia memberitahu kamu file mana yang konflik.

Untuk menyelesaikan konflik:
  1. Buka file yang konflik
  2. Cari bagian yang ditandai (<<<<<<<, =======, >>>>>>>)
  3. Pilih versi yang benar
  4. Hapus tanda konflik
  5. Simpan file
  6. Jalankan: lanjutkan gabungan

Atau batalkan: batalkan gabungan

Istilah teknis: merge conflict""",

    "snapshot": """Apa itu "snapshot"?

Snapshot adalah gambaran lengkap dari semua file pada waktu tertentu.

Ketika kamu menyimpan versi, vesi membuat snapshot:
  - Semua file yang di-stage difoto
  - Foto disimpan dengan hash unik
  - Hash disimpan di "tree" (pohon file)

Tree adalah struktur data yang mencatat:
  - Nama file
  - Hash file (isi file)
  - Struktur folder

Istilah teknis: snapshot, tree, blob""",

    "blob": """Apa itu "blob"?

Blob (Binary Large Object) adalah isi file yang disimpan di repository.

Ketika kamu menyimpan file:
  1. Vesi membaca isi file
  2. Menghitung hash SHA-256
  3. Menyimpan isi + hash di object store

Jika dua file memiliki isi yang sama,
mereka akan memiliki hash yang sama.
Ini menghemat ruang penyimpanan!

Istilah teknis: blob, object""",

    "object": """Apa itu "object"?

Object adalah unit penyimpanan di vesi.

Ada 3 jenis object:
  1. Blob: isi file
  2. Tree: struktur folder
  3. Snapshot: versi/commit

Semua object disimpan berdasarkan hash:
  .vesi/objects/ab/cdef1234...

Hash unik memastikan:
  - Tidak ada duplikat
  - Integritas terjaga
  - Penyimpanan efisien

Istilah teknis: object, content-addressed storage""",

    "ref": """Apa itu "ref" (reference)?

Ref adalah pointer ke object (biasanya snapshot).

Contoh ref:
  - HEAD: pointer ke versi terakhir di cabang aktif
  - Branch: pointer ke versi terakhir di cabang

Ref disimpan di:
  .vesi/refs/heads/utama   → hash commit
  .vesi/HEAD              → ref: refs/heads/utama

Ketika kamu membuat cabang baru, vesi membuat ref baru.
Ketika kamu menyimpan versi, ref diperbarui.

Istilah teknis: ref, reference, branch pointer""",

    "ignore": """Apa itu "ignore" (abaikan)?

Ignore adalah daftar file yang tidak perlu dilacak.

File yang diabaikan:
  - File sementara (*.pyc, __pycache__)
  - File konfigurasi lokal (.env)
  - File dependency (node_modules)
  - File OS (.DS_Store, Thumbs.db)

Daftar ignore ada di file .abaikan (di root repository).

Contoh .abaikan:
  __pycache__/
  *.pyc
  .env
  node_modules/

Istilah teknis: .gitignore, ignore patterns""",

    "aliran kerja": """Apa itu "aliran kerja" (workflow)?

Aliran kerja adalah cara kerja dengan vesi.

Aliran kerja dasar:
  1. Mulai proyek: mulai
  2. Kerja pada file: [edit file]
  3. Lihat perubahan: status
  4. Siapkan file: stel <file>
  5. Simpan versi: simpan "pesan"
  6. Ulangi dari langkah 2

Aliran kerja dengan cabang:
  1. Buat cabang: cabang baru fitur-baru
  2. Pindah ke cabang: cabang pindah fitur-baru
  3. Kerja dan simpan versi
  4. Kembali ke utama: cabang pindah utama
  5. Gabungkan: gabung fitur-baru

Istilah teknis: workflow""",

    "konfigurasi": """Apa itu "konfigurasi"?

Konfigurasi adalah pengaturan untuk repository.

Beberapa pengaturan penting:
  - user.name: Nama kamu (untuk metadata versi)
  - user.email: Email kamu
  - core.language: Bahasa antarmuka

Contoh:
  konfigurasi user.name "Budi"
  konfigurasi user.email "budi@contoh.com"

Konfigurasi tersimpan di .vesi/config

Istilah teknis: config, configuration""",

    "backup": """Apa itu "backup"?

Backup adalah salinan file sebelum diubah.

Ketika kamu menggunakan:
  - pulihkan <file>: backup dibuat sebelum overwrite
  - batalkan <file>: backup dibuat sebelum restore

Backup tersimpan di:
  .vesi/backups/

Ini memastikan kamu tidak kehilangan data
bahkan jika operasi gagal.

Istilah teknis: backup, safe operation""",

    "integritas": """Apa itu "integritas"?

Integritas adalah kepastian bahwa data tidak rusak atau diubah.

Vesi memastikan integritas dengan:
  - Hash SHA-256 untuk setiap file
  - Content-addressed storage
  - Pemeriksaan rutin dengan "cek"

Jika file rusak, hash tidak akan cocok
dan vesi akan memberitahu kamu.

Contoh:
  cek                    # Periksa integritas repository

Istilah teknis: integrity, checksum, verification""",

    "author": """Apa itu "author"?

Author adalah orang yang membuat perubahan.

Author tersimpan di metadata setiap versi:
  - Nama (dari konfigurasi user.name)
  - Timestamp (waktu pembuatan)

Untuk mengatur author:
  konfigurasi user.name "Nama Kamu"
  konfigurasi user.email "email@kamu.com"

Istilah teknis: author, committer""",

    "tag": """Apa itu "tag"?

Tag adalah penanda untuk versi tertentu.

Tag digunakan untuk menandai:
  - Rilis penting (v1.0.0, v2.0.0)
  - Milestone project
  - Titik referensi

Contoh penggunaan (coming soon):
  tag v1.0.0 "Rilis pertama"

Istilah teknis: tag, label""",

    "remote": """Apa itu "remote"?

Remote adalah repository di server lain.

Remote memungkinkan:
  - Sharing repository dengan orang lain
  - Backup di cloud
  - Kolaborasi tim

Contoh remote (coming soon):
  bagikan origin          # Set remote
  unduh origin            # Download dari remote
  kirim origin            # Upload ke remote

Istilah teknis: remote, origin, push, pull""",
}


def cmd_jelaskan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Explain a version control concept."""
    if not parsed.args:
        # Show available concepts
        print("Konsep yang bisa dijelaskan:\n")
        for concept in sorted(CONCEPTS.keys()):
            print(f"  jelaskan {concept}")
        print("\nGunakan 'jelaskan <konsep>' untuk penjelasan lengkap.")
        return 0

    concept = parsed.args[0].lower()

    # Try exact match
    if concept in CONCEPTS:
        print(CONCEPTS[concept])
        return 0

    # Try partial match
    for key, text in CONCEPTS.items():
        if concept in key or key in concept:
            print(text)
            return 0

    print(f"Konsep '{concept}' tidak ditemukan.")
    print("\nKonsep yang tersedia:")
    for key in sorted(CONCEPTS.keys()):
        print(f"  - {key}")

    return 1
