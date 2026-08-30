# 🪶 Tutorial Vesi - Version Control yang Gampang Dipelajari

> **Easy to learn, serious to use.**

---

## 📚 Daftar Isi

1. [Instalasi](#instalasi)
2. [Mulai Cepat](#mulai-cepat)
3. [Command Dasar](#command-dasar)
4. [Branch & Merge](#branch--merge)
5. [Remote Operations](#remote-operations)
6. [Fitur Pro](#fitur-pro)
7. [Tips & Trik](#tips--trik)

---

## Instalasi

### Dari Source

```bash
git clone https://github.com/salzcill-cmd/Vesi.git
cd Vesi
pip install -e .
```

### Verifikasi Instalasi

```bash
vesi --version
```

---

## Mulai Cepat

### 1. Buat Repository Baru

```bash
mkdir my-project
cd my-project
vesi mulai
```

Output:
```
✓ Repository berhasil dibuat!
  Lokasi: ./my-project
  Struktur: .vesi/
  File awal: .abaikan
```

### 2. Siapkan File (Stage)

```bash
vesi stel README.md
# Atau semua file:
vesi stel .
```

### 3. Simpan Versi (Commit)

```bash
vesi simpan "inisialisasi project"
```

### 4. Lihat Riwayat

```bash
vesi lihat riwayat
# Atau gunakan shortcut:
vesi riwayat
```

---

## Command Dasar

### Status Repository

```bash
vesi lihat perubahan
# Shortcut:
vesi status
```

### Simpan Versi

```bash
# Siapkan file dulu
vesi stel main.py
vesi stel src/

# Simpan dengan pesan
vesi simpan "tambah fitur login"

# Simpan semua perubahan
vesi stel .
vesi simpan "update homepage"
```

### Lihat Riwayat

```bash
# Riwayat default (10 terakhir)
vesi lihat riwayat

# Riwayat 20 terakhir
vesi riwayat 20

# Riwayat kompak (one-line)
vesi riwayat --oneline

# Riwayat dengan grafik
vesi riwayat --graph

# Riwayat semua branch
vesi riwayat --all

# Filter per author
vesi riwayat --author=Budi

# Filter per tanggal
vesi riwayat --since=2026-01-01
vesi riwayat --until=2026-12-31
```

### Lihat Perbedaan (Diff)

```bash
# Perbedaan working directory vs commit terakhir
vesi bandingkan

# Perbedaan antara dua versi
vesi bandingkan abc1234 def5678

# Diff dengan statistik
vesi bandingkan pintar

# Diff dengan stat
vesi bandingkan --stat
```

### Pulihkan File

```bash
# Pulihkan dari commit terakhir
vesi pulihkan main.py

# Pulihkan dari versi tertentu
vesi pulihkan main.py dari abc1234

# Batalkan perubahan (discard)
vesi batal main.py
vesi batalkan perubahan main.py
```

---

## Branch & Merge

### Lihat Cabang

```bash
vesi lihat cabang
# Shortcut:
vesi cabang
```

### Buat Cabang Baru

```bash
vesi buat cabang fitur-login
# Atau:
vesi cabang baru fitur-login
```

### Pindah Cabang

```bash
vesi pindah cabang fitur-login
# Atau:
vesi cabang pindah fitur-login
```

### Gabungkan (Merge)

```bash
# Pindah ke cabang target dulu
vesi pindah cabang utama

# Gabungkan
vesi gabungkan fitur-login
# Atau:
vesi gabung fitur-login

# Merge dengan --no-ff (force merge commit)
vesi gabungkan fitur-login --no-ff

# Squash merge (gabung jadi 1 commit)
vesi gabungkan fitur-login --squash
```

### Hapus Cabang

```bash
vesi hapus cabang fitur-login
```

---

## Remote Operations

### Tambah Remote

```bash
vesi remote tambah origin https://github.com/user/repo.git
```

### Lihat Remote

```bash
vesi remote
vesi remote lihat origin
```

### Push ke GitHub/GitLab

```bash
vesi kirim
vesi kirim origin main
vesi kirim --force  # Hati-hati!
```

### Pull dari Remote

```bash
vesi ambil remote
vesi ambil remote origin main
vesi ambil remote --rebase
```

### Fetch dari Remote

```bash
vesi unduh
vesi unduh origin
vesi unduh --prune
```

### Clone Repository

```bash
vesi klon https://github.com/user/repo.git
vesi klon https://github.com/user/repo.git my-folder
```

---

## Fitur Pro

### Interactive Staging (Hunk-level)

```bash
# Stage per hunk
vesi stel -p main.py

# Pilih y/n untuk setiap hunk
Stage this hunk? [y/n/a/s/q]
```

### Stash (Simpan Sementara)

```bash
# Simpan perubahan sementara
vesi simpan sementara
vesi simpan sementara "work in progress"

# Lihat stash
vesi lihat stash
vesi simpan sementara lihat

# Ambil stash
vesi ambil stash
vesi ambil stash 1

# Buat branch dari stash
vesi simpan sementara cabang fix-branch
```

### Tag

```bash
# Buat tag lightweight
vesi beri tag v1.0.0

# Buat tag annotated
vesi beri tag -a v1.0.0 -m "Rilis pertama"

# Lihat tag
vesi lihat tag
vesi tag

# Hapus tag
vesi hapus tag v1.0.0
```

### Reflog (Jejak)

```bash
# Lihat jejak HEAD
vesi jejak
vesi jejak 20

# Jejak dengan filter
vesi jejak --branch=main
vesi jejak --since=2026-01-01
vesi jejak --action=commit

# Expire lama
vesi jejak --expire

# Statistik
vesi jejak --stat
```

### Blame (Siapa Ubah)

```bash
vesi siapa ubah main.py
vesi siapa ubah main.py dari v1.0.0
```

### Bisect (Cari Bug)

```bash
# Mulai bisect
vesi bagi cari mulai v1.0.0 v2.0.0

# Tandai commit
vesi bagi cari baik    # Commit ini baik
vesi bagi cari buruk   # Commit ini ada bug

# Selesai
vesi bagi cari selesai
```

### Commit Notes

```bash
# Tambah catatan
vesi catatan abc1234 "perlu review login flow"

# Lihat catatan
vesi catatan lihat abc1234
vesi catatan list
```

### Hook System

```bash
# Lihat hooks
vesi hook list

# Buat sample hooks
vesi hook sample

# Install hook
vesi hook install pre-commit "python -m pytest tests/"
```

### Plugin System

```bash
# Lihat plugins
vesi plugin

# Buat plugin baru
vesi plugin buat my-plugin

# Install plugin
vesi plugin install ./my-plugin
```

### Shell Completion

```bash
# Generate completion
vesi completion bash > ~/.bash_completion.d/vesi
vesi completion zsh > ~/.zsh/completions/_vesi
vesi completion fish > ~/.config/fish/completions/vesi.fish

# Install completion
vesi completion install bash
```

### Git Bridge

```bash
# Import dari .git
vesi git impor /path/to/.git

# Export ke .git
vesi git ekspor /path/to/output
```

---

## Tips & Trik

### Shortcut yang Sering Dipakai

| Shortcut | Arti |
|----------|------|
| `vesi status` | `lihat perubahan` |
| `vesi riwayat` | `lihat riwayat` |
| `vesi cabang` | `lihat cabang` |
| `vesi batal <file>` | `batalkan perubahan` |
| `vesi gabung <branch>` | `gabungkan <branch>` |

### Emoji Commands

| Emoji | Command |
|-------|---------|
| 💾 | `simpan` |
| 📋 | `lihat perubahan` |
| 📊 | `statistik` |
| 🔍 | `cari` |
| 🌿 | `lihat cabang` |

### Auto-Save

```bash
# Aktifkan auto-save
vesi watch aktifkan 300  # Setiap 5 menit

# Lihat status
vesi watch

# Nonaktifkan
vesi watch nonaktifkan
```

### Statistik Project

```bash
vesi statistik
vesi statistik --detail
vesi statistik --author
```

### Export/Import

```bash
# Export ke zip
vesi ekspor backup.zip

# Import dari zip
vesi impor backup.zip
```

### Integrity Check

```bash
vesi cek
vesi cek --deep      # Verifikasi semua hash
vesi cek --repair    # Coba perbaiki masalah
vesi cek --gc        # Garbage collection
vesi cek --stat      # Statistik repository
```

### JSON Output

```bash
vesi riwayat --json
vesi status --json
vesi branch --json
```

---

## Perbandingan dengan Git

| Fitur | Git | Vesi |
|-------|-----|------|
| Basic VCS | ✅ | ✅ |
| Branch & Merge | ✅ | ✅ |
| Stash | ✅ | ✅ |
| Cherry-pick | ✅ | ✅ |
| Rebase | ✅ | ✅ |
| Bisect | ✅ | ✅ |
| Blame | ✅ | ✅ |
| Reflog | ✅ | ✅ |
| Remote (push/pull) | ✅ | ✅ |
| **Bahasa Indonesia** | ❌ | ✅ |
| **Conflict Auto-resolve** | ❌ | ✅ |
| **Merge Assistant** | ❌ | ✅ |
| **Auto-save** | ❌ | ✅ |
| **Plugin System** | ❌ | ✅ |
| **Shell Completion** | ✅ | ✅ |

---

## FAQ

### Q: Apakah vesi kompatibel dengan Git?

A: Ya! Vesi bisa import/export repository Git. Gunakan:
```bash
vesi git impor /path/to/.git
vesi git ekspor /path/to/output
```

### Q: Bisakah push ke GitHub/GitLab?

A: Ya! Vesi mendukung remote operations:
```bash
vesi remote tambah origin https://github.com/user/repo.git
vesi kirim
```

### Q: Bagaimana cara mengembalikan file yang terhapus?

A: Gunakan `pulihkan` atau `batalkan`:
```bash
vesi pulihkan file.txt
vesi pulihkan file.txt dari v1.0.0
```

### Q: Bagaimana cara melihat perbedaan antara dua commit?

A: Gunakan `bandingkan`:
```bash
vesi bandingkan abc1234 def5678
```

---

## Support

- **GitHub**: https://github.com/salzcill-cmd/Vesi
- **Issues**: https://github.com/salzcill-cmd/Vesi/issues

---

> **Vesi** - Easy to learn, serious to use. 🪶
