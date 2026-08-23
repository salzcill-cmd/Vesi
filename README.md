<div align="center">

# 🪶 vesi

**Version control yang gampang dipelajari.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-00ff88?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-ff6b6b?style=for-the-badge)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-190%20passed-4ecdc4?style=for-the-badge)](#testing)
[![Features](https://img.shields.io/badge/features-35+-9b59b6?style=for-the-badge)](#semua-command)

<br/>

`vesi` bukan "Git yang diterjemahkan". Ini VCS baru dengan command Bahasa Indonesia yang dirancang dari nol untuk **pemula** — tapi engine-nya serius.

[**Mulai Pakai**](#mulai-cepat) • [**Command List**](#semua-command) • [**Workflow**](#workflow) • [**Fitur Pro**](#fitur-pro) • [**Kontribusi**](#kontribusi)

<br/>

![vesi demo](https://img.shields.io/badge/-WATCH%20DEMO%20VIDEO-blue?style=for-the-badge&logo=youtube&logoColor=white)

</div>

---

## Kenapa vesi?

<table>
<tr>
<td width="50%" valign="top">

### 😵 Pakai Git?

```
$ git add .
$ git commit -m "fix: update login"
$ git push origin feature/login
$ git checkout main
$ git merge feature/login
$ git branch -d feature/login
```

**6 command. 3 istilah asing. 1 headache.**

</td>
<td width="50%" valign="top">

### 😎 Pakai vesi?

```
$ vesi stel .
$ vesi simpan "fix: update login"
$ vesi cabang pindah utama
$ vesi gabung login
$ vesi cabang hapus login
```

**5 command. 0 istilah asing. 0 headache.**

</td>
</tr>
</table>

### 🏆 Vesi vs Git

| Fitur | Vesi | Git |
|-------|------|-----|
| **Basic VCS** | ✅ | ✅ |
| **Bahasa Indonesia** | ✅ Natural | ❌ Inggris teknis |
| **Undo Commit** | ✅ `batalkan versi` | ⚠️ `git reset` (ribet) |
| **Search History** | ✅ `cari riwayat` | ⚠️ `git log --grep` |
| **Auto Backup** | ✅ `cadangan buat` | ❌ Manual |
| **File Insights** | ✅ `lihat file` | ⚠️ `git log --follow` |
| **Commit Templates** | ✅ `pola commit` | ❌ Tidak ada |
| **Smart Diff** | ✅ `bandingkan pintar` | ⚠️ `git diff --stat` |
| **Conflict Helper** | ✅ `bantu konflik` | ❌ Tidak ada |
| **Interactive Commit** | ✅ `simpan interaktif` | ❌ Tidak ada |
| **Project Statistics** | ✅ `statistik` | ❌ Tidak ada |
| **Auto Save** | ✅ `auto simpan` | ❌ Tidak ada |
| **Export/Import** | ✅ `ekspor` / `impor` | ⚠️ `git archive` |
| **Custom Aliases** | ✅ `alias tambah` | ⚠️ `git config alias` |
| **File Locking** | ✅ `kunci file` | ❌ Tidak ada |
| **Merge Assistant** | ✅ `asisten gabung` | ❌ Tidak ada |

---

## Mulai Cepat

### 1️⃣ Install

```bash
git clone https://github.com/salzcill-cmd/vesi.git
cd vesi
pip install -e .
```

### 2️⃣ Buat Repository

```bash
vesi mulai
```

```
✓ Repository berhasil dibuat!
  Lokasi: ./project-ku
  Struktur: .vesi
  File awal: .abaikan
```

### 3️⃣ Simpan Pertama Kali

```bash
vesi stel .                          # Siapkan semua file
vesi simpan "inisialisasi project"   # Simpan versi
```

### 4️⃣ Kerja Seperti Biasa

```bash
# Edit file...
vesi status                          # Lihat yang berubah
vesi bandingkan                      # Lihat bedanya
vesi stel .
vesi simpan "tambah fitur login"
```

**Udah.** Nggak perlu Google "git vs reset vs revert vs checkout".

---

## Semua Command

<details>
<summary><b>📁 Repository Management</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi mulai` | `vesi init` | Buat repository baru |
| `vesi status` | `vesi lihat perubahan` | Lihat file yang berubah |
| `vesi cek` | `vesi check` | Periksa integritas repository |
| `vesi konfigurasi` | `vesi config` | Kelola pengaturan |
| `vesi jejak` | `vesi reflog` | Riwayat pergerakan HEAD |

</details>

<details>
<summary><b>💾 Menyimpan Perubahan</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi stel <file>` | `vesi add` | Siapkan file untuk commit |
| `vesi simpan "pesan"` | `vesi save` | Simpan versi (commit) |
| `vesi simpan --amend` | | Ubah commit terakhir |
| `vesi simpan sementara` | `vesi stash` | Simpan perubahan sementara |
| `vesi simpan interaktif` | `vesi wizard` | Wizard commit langkah demi langkah |
| `vesi riwayat` | `vesi log` | Lihat daftar versi |
| `vesi bandingkan` | `vesi diff` | Lihat perbedaan |
| `vesi bandingkan pintar` | `vesi smart diff` | Diff dengan ringkasan |
| `vesi isi <file>` | `vesi show` | Tampilkan isi file |

</details>

<details>
<summary><b>↩️ Memulihkan</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi pulihkan <file>` | `vesi restore` | Kembalikan file ke versi sebelumnya |
| `vesi batal <file>` | `vesi undo` | Batalkan perubahan |
| `vesi batalkan versi` | `vesi undo commit` | Batalkan commit terakhir |
| `vesi ambil stash` | `vesi pop` | Ambil stash tersimpan |
| `vesi ambil versi <commit>` | `vesi cherry-pick` | Apply commit tertentu |

</details>

<details>
<summary><b>🌿 Branch Management</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi cabang baru <nama>` | `vesi create` | Buat cabang baru |
| `vesi cabang` | `vesi branch` | Lihat semua cabang |
| `vesi cabang pindah <nama>` | `vesi switch` | Pindah ke cabang lain |
| `vesi cabang hapus <nama>` | `vesi delete` | Hapus cabang |
| `vesi gabung <nama>` | `vesi merge` | Gabungkan cabang |
| `vesi folder kerja` | `vesi worktree` | Kelola worktree |

</details>

<details>
<summary><b>🏷️ Tagging</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi beri tag <nama>` | `vesi tag` | Tandai versi penting |
| `vesi lihat tag` | `vesi tags` | Lihat semua tag |
| `vesi hapus tag <nama>` | | Hapus tag |

</details>

<details>
<summary><b>🔬 Analisis & Debugging</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi siapa ubah <file>` | `vesi blame` | Lihat siapa ubah setiap baris |
| `vesi bagi cari` | `vesi bisect` | Cari commit penyebab bug |
| `vesi susun ulang <n>` | `vesi rebase` | Gabungkan N commit jadi satu |
| `vesi cari <pola>` | `vesi grep` | Cari pola di dalam file |
| `vesi cari riwayat <kata>` | `vesi search history` | Cari dalam riwayat commit |

</details>

<details>
<summary><b>📊 Statistik & Insights</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi statistik` | `vesi stats` | Statistik proyek |
| `vesi statistik --detail` | | Statistik lengkap |
| `vesi lihat file <file>` | `vesi insights` | Statistik file |

</details>

<details>
<summary><b>🤖 Fitur Canggih</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi pola commit` | `vesi template` | Template pesan commit |
| `vesi cadangan buat` | `vesi backup` | Buat backup otomatis |
| `vesi cadangan pulihkan` | | Pulihkan dari backup |
| `vesi bantu konflik` | `vesi conflict help` | Bantu selesaikan konflik |
| `vesi asisten gabung` | `vesi merge assistant` | Asisten merge interaktif |

</details>

<details>
<summary><b>⚡ Fitur Pro</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi auto simpan aktifkan` | `vesi autosave on` | Aktifkan auto-save |
| `vesi auto simpan nonaktifkan` | `vesi autosave off` | Nonaktifkan auto-save |
| `vesi ekspor` | `vesi export` | Export ke zip |
| `vesi impor` | `vesi import` | Import dari zip |
| `vesi alias tambah <nama> <cmd>` | `vesi add alias` | Buat custom alias |
| `vesi kunci file <file>` | `vesi lock` | Kunci file |
| `vesi kunci buka <file>` | `vesi unlock` | Buka kunci file |

</details>

<details>
<summary><b>🎓 Belajar</b></summary>

| Command | Alias | Fungsi |
|---------|-------|--------|
| `vesi jelaskan <konsep>` | `vesi explain` | Pelajari konsep VCS |
| `vesi bantuan` | `vesi help` | Tampilkan bantuan |

</details>

---

## Workflow

### 🎯 Pemula — Simpan & Lihat Riwayat

```bash
vesi mulai                              # 1. Buat repository

echo 'print("hello")' > main.py        # 2. Buat file

vesi stel .                             # 3. Siapkan
vesi simpan "hello world"              # 4. Simpan

vesi riwayat                            # 5. Lihat riwayat
```

### 🔀 Programmer — Branch & Merge

```bash
vesi mulai website                      # 1. Mulai project

vesi cabang baru fitur-login            # 2. Buat branch
vesi cabang pindah fitur-login          # 3. Pindah ke branch

# ... kode fitur login ...

vesi stel .
vesi simpan "fitur login selesai"       # 4. Simpan

vesi cabang pindah utama                # 5. Kembali ke main
vesi gabung fitur-login                 # 6. Gabungkan
vesi cabang hapus fitur-login           # 7. Hapus branch
```

### 🔍 Debugging — Cari Bug dengan Bisect

```bash
vesi bagi cari mulai abc1234 def5678    # 1. Mulai bisect

# Test code...
vesi bagi cari baik                      # 2. Tandai commit ini OK
# Test code...
vesi bagi cari buruk                     # 3. Tandai commit ini buggy

# Hasil:
# ✓ Bisect selesai!
#   Commit yang menyebabkan bug:
#   7f8a9b0
```

### 💾 Stash — Simpan Sementara

```bash
# Lagi kerja, tapi harus pindah branch
vesi simpan sementara "setengah jadi"   # 1. Simpan sementara

vesi cabang pindah utama                # 2. Pindah branch

# ... kerja lain ...

vesi ambil stash                        # 3. Ambil lagi
```

### 🔄 Undo — Batalkan Commit

```bash
vesi riwayat                            # 1. Lihat riwayat

# Ups, commit salah!
vesi batalkan versi                     # 2. Batalkan commit terakhir

# Perubahan tetap di staging, bisa commit lagi
vesi simpan "pesan yang benar"
```

### 🔎 Search — Cari dalam Riwayat

```bash
vesi cari riwayat login                 # 1. Cari commit terkait login
vesi cari riwayat --file main.py        # 2. Cari yang ubah main.py
vesi cari riwayat --author budi         # 3. Cari commit author budi
```

---

## Fitur Pro

### 📊 Statistik Proyek

```bash
vesi statistik
```

```
📊 Statistik Proyek

  📁 Repository:
    Total commit:     42
    Total file:       15
    Total author:     3

  👥 Kontributor:
    budi               25x (59%) ████████████
    ani                12x (28%) █████
    deni                5x (11%) ██

  🕐 Aktivitas Terakhir:
    a1b2c3d  2026-08-23  fitur login selesai
    f4e5d6a  2026-08-22  update homepage
    ...
```

### 🤖 Interactive Commit

```bash
vesi simpan interaktif
```

```
🔄 Simpan Interaktif - Langkah demi Langkah

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 Langkah 1: File yang akan disimpan (3 file)
  ✓ main.py
  ✓ utils.py
  ✓ config.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️  Langkah 2: Pilih tipe commit

  1. feat      Fitur baru
  2. fix       Perbaikan bug
  3. docs      Dokumentasi
  ...
  Pilih (1-8) [1]: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✍️  Langkah 3: Deskripsi perubahan

  Deskripsi: tambah halaman login

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👀 Langkah 4: Preview

  Pesan: "feat: tambah halaman login"
  File:  3 file

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Langkah 5: Konfirmasi

  Simpan? [Y/n]: y

🎉 Berhasil!
  ID:    a1b2c3d
  Pesan: feat: tambah halaman login
  File:  3 file disimpan
```

### 📦 Export/Import

```bash
# Export ke zip
vesi ekspor backup-hari-ini.zip

# Import dari zip
vesi impor backup-hari-ini.zip
```

### 🔒 File Locking

```bash
# Kunci file agar tidak diedit orang lain
vesi kunci file main.py

# Cek status lock
vesi kunci status main.py

# Buka kunci
vesi kunci buka main.py
```

### 🎨 Custom Aliases

```bash
# Buat alias
vesi alias tambah s simpan
vesi alias tambah st stel
vesi alias tambah co "cabang baru"

# Gunakan alias
vesi s "fix bug login"
vesi st .
vesi co fitur-baru
```

### 🤖 Merge Assistant

```bash
vesi asisten gabung
```

```
🤖 Asisten Gabung - Bantuan Merge Conflict

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Apa itu Merge Conflict?
Konflik terjadi ketika dua branch mengubah bagian yang sama.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️  Perintah yang Tersedia:

  asisten gabung              Tampilkan bantuan ini
  asisten gabung <file>       Analisis konflik di file
  asisten gabung --solve      Auto-solve konflik sederhana
  asisten gabung --pilih kami   Pilih versi kami
  asisten gabung --pilih mereka Pilih versi mereka
  asisten gabung --pilih gabung Gabungkan kedua versi
```

---

## Konsep VCS

Baru pertama kali pakai version control? Gunakan `vesi jelaskan`:

```bash
vesi jelaskan versi         # Apa itu commit/versi?
vesi jelaskan cabang        # Apa itu branch?
vesi jelaskan gabungan      # Apa itu merge?
vesi jelaskan staging       # Apa itu staging?
vesi jelaskan konflik       # Apa itu merge conflict?
vesi jelaskan perbandingan  # Apa itu diff?
vesi jelaskan riwayat       # Apa itu history?
```

---

## Struktur Repository

```
project/
├── .vesi/                  # Folder internal vesi
│   ├── HEAD                # Pointer ke branch aktif
│   ├── config              # Konfigurasi repository
│   ├── objects/            # Content-addressed storage (SHA-256)
│   ├── refs/               # Branch & tag references
│   ├── stash/              # Stash storage
│   ├── backups/            # Backup sebelum restore
│   ├── locks.json          # File locks
│   ├── aliases.json        # Custom aliases
│   └── autosave.json       # Auto-save config
├── .abaikan                # File yang diabaikan (mirip .gitignore)
├── main.py                 # File project kamu
└── ...
```

---

## Opsi Global

| Opsi | Fungsi |
|------|--------|
| `--version` | Tampilkan versi |
| `--verbose` | Output detail |
| `--debug` | Debug information |
| `--json` | Output dalam format JSON (untuk AI agents) |
| `--no-color` | Tanpa warna |

---

## Kenapa Bahasa Indonesia?

> "Gue udah 3 bulan belajar Git, tapi masih bingung bedanya `git add`, `git commit`, `git push`. Bukannya gitu aja ya?"
>
> — Author vesi, yang masih push & commit pake AI sampe sekarang.. 🤷

**Kami denger.**

`vesi` dirancang untuk:
- 🎓 **Pelajar SMA/Kuliah** yang baru belajar programming
- 👨‍💻 **Programmer pemula** yang trauma sama Git
- 👩‍🏫 **Guru & mentor** yang mau ngajarin VCS tanpa pusing
- 🤖 **AI agents** yang butuh output terstruktur

**Bukan berarti Git jelek.** Git itu powerful. Tapi learning curve-nya curam banget untuk pemula.

`vesi` hadir sebagai **jembatan**: mulai dari yang gampang, tumbuh ke yang advanced.

---

## Testing

```bash
# Jalankan semua test
python -m pytest

# Jalankan test tertentu
python -m pytest tests/unit/test_parser.py -v

# Lihat coverage
python -m pytest --cov=vesi
```

**Status:** 190 tests ✅ (unit + integration + e2e)

---

## Kontribusi

Kontribusi selalu diterima! 🎉

1. Fork repository ini
2. Buat branch baru (`vesi cabang baru fitur-kerenn`)
3. Commit perubahanmu (`vesi simpan "tambah fitur keren"`)
4. Push ke fork kamu
5. Buka Pull Request

Lihat [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan lengkap.

---

## Lisensi

[MIT License](LICENSE) — Bebas dipakai, dimodif, dan didistribusikan.

---

<div align="center">

**Made with 🪶 by [vesi contributors](https://github.com/salzcill-cmd/vesi/graphs/contributors)**

*Easy to learn, serious to use.*

<br/>

[![Star](https://img.shields.io/github/stars/salzcill-cmd/vesi?style=social)](https://github.com/salzcill-cmd/vesi)
[![Fork](https://img.shields.io/github/forks/salzcill-cmd/vesi?style=social)](https://github.com/salzcill-cmd/vesi/fork)
[![Watch](https://img.shields.io/github/watchers/salzcill-cmd/vesi?style=social)](https://github.com/salzcill-cmd/vesi/watchers)

</div>
