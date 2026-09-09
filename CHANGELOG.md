# Changelog

Semua perubahan penting pada vesi akan didokumentasikan di file ini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [Unreleased]

### Added
- **Exit code taxonomy** (PRD 53) - Setiap kesalahan dipetakan ke kode keluar yang bermakna:
  - `0` sukses, `1` kesalahan umum, `2` penggunaan tidak valid
  - `3` kesalahan repository, `4` konflik, `5` integritas, `6` pembatalan pengguna
- **`--json` fungsional** (PRD 54) - Output terstruktur dan dapat dibaca mesin
  - Keberhasilan: `{"success": true, "command": ..., "exit_code": 0, "output": ...}`
  - Kesalahan: `{"error": true, "message": ..., "hint": ..., "exit_code": N}`
- **Custom alias benar-benar dieksekusi** (PRD 56) - Alias yang dibuat via `alias tambah` kini dipakai saat mengetik perintah; alias tidak pernah menimpa perintah baku
- **`alias tambah|hapus|list` di-parse sebagai subcommand** - Memperbaiki pemanggilan `alias tambah <nama> <cmd>`
- **`simpan versi` menampilkan `Ukuran: X KB`**
- **16 test baru** untuk tag, show, revert, mv, rm, show_commit (`test_untested_commands.py`)

### Changed
- `mulai proyek` pada repository yang sudah ada kini **warning** (bukan error), sesuai PRD 16.1
- Status staging (PRD 16.2): file siap di-commit ditandai `.`, file yang masih punya perubahan unstaged ditandai `S`

### Fixed
- `--json` tidak lagi no-op; kini menghasilkan output JSON murni
- Custom alias (ditulis ke `aliases.json`) sebelumnya tidak pernah dibaca oleh parser
- **Parser bug: `hapus file` dan `pindah file`** — subcommand `file` tidak dikenali, routing salah ke `cabang`
- **Parser bug: `verifikasi tag`** — routing ke `cmd_catatan` (catatan) bukan `cmd_verify_tag`
- **Router bug: duplikat key `pindah`** — `cmd_pindah_cepat_handler` adalah dead code
- **Parser bug: `tampilkan versi`** — mapped ke `isi` bukan `tampilkan` (menyebabkan routing salah)
- **Parser bug: `beri tag -a -m`** — flag `-a`/`-m` tidak diekstrak dari args (lexer hanya handle `--`)
- `commands/__init__.py` diekspor lengkap (60+ command, sebelumnya hanya 18)
- Hapus slang aliases (`gas`, `gaskeun`, `udah`, `done`, `slesai`, `batalin`, `urungkan`, `gak jadi`, `liat`) sesuai PRD §104
- Bersihkan duplikat entry di `_fix_typos` dan self-mapping di `VERB_ALIASES`
- `isi` command: `_resolve_version` sekarang handle `HEAD` dan `HEAD~N`


## [0.5.0] - 2026-09-09

### Added
- **Sistem Konfigurasi** (`konfigurasi`) - Atur preferensi tersimpan
  - Lapisan prioritas: default → global → repository → environment (`VESI_*`)
  - `vesi konfigurasi` - Lihat konfigurasi aktif
  - `vesi konfigurasi --global` - Lihat/lakukan ulang konfigurasi global
  - `vesi konfigurasi <kunci> <nilai>` - Tetapkan nilai
  - `vesi konfigurasi hapus <kunci>` - Hapus nilai (kembali ke default)
  - Kunci flat (misal `user.nama`) dengan validasi schema
  - Migrasi otomatis file konfigurasi lama (`.vesi/config`) ke `.vesi/config.json`

- **Tutorial Interaktif** (`belajar`) - Belajar vesi dengan melakukan
  - `vesi belajar` - Lihat daftar pelajaran + progres
  - `vesi belajar <judul>` - Mulai pelajaran interaktif
  - `vesi belajar --reset` - Hapus progres belajar
  - Alias: `learn`, `tutorial`, `bimbingan`
  - 6 pelajaran: mulai, simpan, riwayat, cabang, gabungan, tags
  - Sepenuhnya offline, tanpa dependensi eksternal

- **Mode `--dry-run`** untuk perintah destruktif
  - `balikkan <commit> --dry-run` - Preview commit pembalikan
  - `hapus file <file> --dry-run` - Preview penghapusan file
  - `batalkan perubahan <file> --dry-run` - Preview pembatalan perubahan
  - `atur ulang <commit> --dry-run` - Preview reset (soft/mixed/hard)

- **Unit Test Lapisan Penyimpanan** - Coverage storage layer (44 test baru)

### Fixed
- **Delta apply bug** - Semua operasi insert diabaikan karena salah cek bit (`cmd & OPS_DELTA_INSERT` selalu 0); offset copy juga salah baca. Sekarang `apply_delta` berfungsi benar.
- **Pack index hash truncation** - Index pack menulis hash 32-byte (SHA-256) tetapi pembaca hanya mengambil 20-byte, menyebabkan lookup gagal.
- **Pack header size mismatch** - `PACK_HEADER_SIZE` dideklarasikan 12 byte padahal aktual 16 (8 sig + 4 version + 4 count); offset pertama objek molor 4 byte.
- **Pack offset calculation order** - Offset dihitung dalam urutan sorted, padahal objek ditulis dalam urutan insertion.

### Changed
- Perintah `konfigurasi` menggunakan format kunci flat dengan validasi schema
- Output verbose command `balikkan` menampilkan daftar file yang dipulihkan/dihapus
- **Logging terpusat** via `utils/logging_setup.py`; `--debug` mengaktifkan DEBUG level ke stderr
- Plugin error dan hook error dicatat via `logging` bukan `print()`, menjaga log tetap bersih di mode normal

## [0.3.0] - 2026-08-22

### Added
- **Show Command** (`isi`) - Tampilkan isi file dari versi tertentu
  - `vesi isi <file>` - Tampilkan isi file dari versi terakhir
  - `vesi isi <file> dari v1.0.0` - Tampilkan isi file dari versi tertentu
  - `vesi isi --verbose <file>` - Tampilkan dengan nomor baris

- **Search Command** (`cari`) - Cari pola di dalam file
  - `vesi cari <pola>` - Cari di semua file
  - `vesi cari <pola> di src/` - Cari di folder tertentu
  - Support regex patterns
  - Highlight kecocokan

- **Amend Command** - Ubah commit terakhir
  - `vesi simpan --amend "pesan baru"` - Ubah pesan commit terakhir
  - `vesi simpan --amend` - Tambah file staged ke commit terakhir

### Changed
- Parser extended to support new commands
- Router updated with new command handlers

## [0.2.0] - 2026-08-22

### Added
- **Tag System** - Tandai versi penting dengan tag
  - `beri tag v1.0.0 "Rilis pertama"` - Buat tag
  - `lihat tag` atau `tag` - Lihat semua tag
  - `hapus tag v1.0.0` - Hapus tag

## [0.1.1] - 2026-08-22

### Fixed
- Remove unused imports in `cmd_diff.py`
- Remove duplicate `_resolve_version` function in `cmd_restore.py`
- Clean up `__import__("pathlib")` usage in diff command

## [0.1.0] - 2026-08-22

### Added

#### Core Features
- `mulai proyek` - Inisialisasi repository baru
- `lihat perubahan` - Status working directory
- `stel` - Stage files untuk commit
- `simpan versi` - Buat snapshot/commit
- `lihat riwayat` - Tampilkan commit history
- `bandingkan` - Diff antara versi
- `pulihkan` - Restore file dari versi
- `batalkan perubahan` - Discard working changes

#### Branch Management
- `buat cabang` - Buat branch baru
- `lihat cabang` - List branches
- `pindah cabang` - Switch branch
- `hapus cabang` - Delete branch
- `gabungkan` - Merge branches (fast-forward + three-way)

#### Repository Management
- `cek` - Integrity check
- `konfigurasi` - Config management
- `bantuan` - Help system
- `jelaskan` - Educational explanations (22 concepts)

#### Infrastructure
- Content-addressed object storage
- SHA-256 hashing
- Git-like repository structure (.vesi/)
- Ignore system (.abaikan)
- Cross-platform support

#### CLI Features
- `--version` - Version info
- `--verbose` - Detailed output
- `--debug` - Debug information
- `--json` - JSON output for AI agents
- Color support with `--no-color` fallback

#### Natural Syntax
- `vesi status` = `lihat perubahan`
- `vesi riwayat` = `lihat riwayat`
- `vesi log` = `lihat riwayat`
- `vesi cabang baru <nama>` = `buat cabang <nama>`
- `vesi cabang pindah <nama>` = `pindah cabang <nama>`
- `vesi cabang hapus <nama>` = `hapus cabang <nama>`
- `vesi batal <file>` = `batalkan perubahan`
- English shortcuts: `add`, `save`, `commit`, `diff`, `restore`

#### Testing
- Unit tests (90 parser + 33 commands)
- Integration tests (12 workflows)
- E2E tests (24 CLI subprocess)

### Documentation
- README.md dengan dokumentasi lengkap
- CONTRIBUTING.md untuk kontributor
- CHANGELOG.md ini
- Issue templates (bug report, feature request)
- PR template
- GitHub Actions CI/CD workflows

---

## Versioning

Kami menggunakan [Semantic Versioning](https://semver.org/lang/id/):

- **MAJOR** (x.0.0): Perubahan breaking, tidak backward compatible
- **MINOR** (0.x.0): Fitur baru, backward compatible
- **PATCH** (0.0.x): Bug fixes, backward compatible

### Contoh

```
0.1.0  →  0.1.1  (patch: bug fix)
0.1.1  →  0.2.0  (minor: fitur baru)
0.2.0  →  0.3.0  (minor: fitur baru)
0.3.0  →  1.0.0  (major: breaking changes)
```

---

## Links

- [GitHub Releases](https://github.com/username/vesi/releases)
- [PyPI Package](https://pypi.org/project/vesi-vcs/) (coming soon)
