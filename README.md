# vesi

> **Version control yang gampang dipelajari**

`vesi` adalah Version Control System (VCS) dengan antarmuka command-line berbahasa Indonesia yang dirancang untuk kemudahan belajar pemula tanpa mengorbankan kemampuan teknis.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-0.1.0-orange)

## Fitur Utama

- 🇮🇩 **Bahasa Indonesia Natural** — Command menggunakan kata-kata yang sudah dikenal
- 🎓 **Educational by Design** — Fitur `jelaskan` membantu memahami konsep
- 🔒 **Safe by Default** — Operasi destruktif selalu meminta konfirmasi
- 🧩 **Professional Engine** — Content-addressed storage, SHA-256 hashing, proper merge

## Instalasi

### Dari Source

```bash
# Clone repository
git clone https://github.com/username/vesi.git
cd vesi

# Install dalam mode development
pip install -e .

# Atau langsung gunakan
PYTHONPATH=src python -m vesi.cli.app
```

### Dari PyPI (coming soon)

```bash
pip install vesi-vcs
```

## Mulai Cepat

### 1. Buat Repository Baru

```bash
vesi mulai
# Atau
vesi mulai proyek nama-proyek
```

### 2. Simpan Perubahan Pertama

```bash
# Lihat file yang berubah
vesi status

# Siapkan semua file
vesi stel .

# Simpan versi
vesi simpan "inisialisasi project"
```

### 3. Workflow Harian

```bash
# Edit file
# ...

# Lihat perubahan
vesi status

# Lihat perbedaan
vesi bandingkan

# Siapkan dan simpan
vesi stel .
vesi simpan "update fitur baru"
```

## Command Reference

### Repository

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi mulai` | `vesi mulai proyek` | Buat repository baru |
| `vesi status` | `vesi lihat perubahan` | Lihat file yang berubah |
| `vesi cek` | `vesi check` | Periksa integritas repository |
| `vesi konfigurasi` | `vesi config` | Kelola pengaturan |

### Menyimpan

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi stel <file>` | `vesi siap`, `vesi add` | Siapkan file untuk disimpan |
| `vesi simpan "pesan"` | `vesi save`, `vesi commit` | Simpan versi baru |
| `vesi riwayat` | `vesi log` | Lihat daftar versi |
| `vesi bandingkan` | `vesi diff` | Lihat perbedaan |

### Memulihkan

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi pulihkan <file>` | `vesi restore` | Kembalikan file ke versi sebelumnya |
| `vesi batal <file>` | `vesi undo` | Batalkan perubahan |

### Cabang

| Command | Fungsi |
|---------|--------|
| `vesi cabang baru <nama>` | Buat cabang baru |
| `vesi cabang` | Lihat semua cabang |
| `vesi cabang pindah <nama>` | Pindah ke cabang lain |
| `vesi cabang hapus <nama>` | Hapus cabang |
| `vesi gabung <nama>` | Gabungkan cabang |

### Lainnya

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi bantuan` | `vesi help`, `vesi ?` | Tampilkan bantuan |
| `vesi jelaskan <konsep>` | `vesi explain` | Pelajari konsep VCS |

## Contoh Workflow

### Pemula

```bash
# Mulai
vesi mulai

# Buat file
echo 'print("hello")' > main.py

# Simpan
vesi stel .
vesi simpan "hello world"

# Lihat riwayat
vesi riwayat
```

### Programmer

```bash
# Mulai project
vesi mulai website

# Buat cabang fitur
vesi cabang baru login

# Pindah ke cabang fitur
vesi cabang pindah login

# Kerja dan simpan
vesi stel .
vesi simpan "fitur login selesai"

# Kembali ke utama
vesi cabang pindah utama

# Gabungkan
vesi gabung login

# Lihat riwayat
vesi riwayat
```

### Recovery

```bash
# Lihat riwayat
vesi riwayat

# Bandingkan versi
vesi bandingkan abc1234 def5678

# Pulihkan file dari versi tertentu
vesi pulihkan main.py dari abc1234

# Simpan perbaikan
vesi simpan "membetulkan kesalahan"
```

## Opsi Global

| Opsi | Fungsi |
|------|--------|
| `--version` | Tampilkan versi |
| `--verbose` | Output detail |
| `--debug` | Debug information |
| `--json` | Output dalam format JSON |
| `--no-color` | Tanpa warna |

## Konsep VCS

Gunakan `vesi jelaskan` untuk mempelajari konsep:

```bash
vesi jelaskan versi        # Apa itu commit?
vesi jelaskan cabang       # Apa itu branch?
vesi jelaskan gabungan     # Apa itu merge?
vesi jelaskan staging      # Apa itu staging?
vesi jelaskan riwayat      # Apa itu history?
vesi jelaskan perbandingan # Apa itu diff?
vesi jelaskan konflik      # Apa itu merge conflict?
```

## Struktur Repository

```
project/
├── .vesi/                 # Folder internal vesi
│   ├── HEAD               # Pointer ke branch aktif
│   ├── config             # Konfigurasi repository
│   ├── objects/           # Content-addressed storage
│   ├── refs/              # Branch references
│   └── backups/           # Backup sebelum restore
├── .abaikan               # File yang diabaikan
├── main.py                # File project kamu
└── ...
```

## Kontribusi

Kontribusi selalu diterima! Lihat CONTRIBUTING.md untuk panduan.

## Lisensi

MIT License - Lihat LICENSE untuk detail.

---

**Tagline:** *Easy to learn, serious to use.*
