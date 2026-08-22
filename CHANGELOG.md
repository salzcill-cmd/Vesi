# Changelog

Semua perubahan penting pada vesi akan didokumentasikan di file ini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [Unreleased]

## [0.1.1] - 2026-08-22

### Fixed
- Remove unused imports in `cmd_diff.py`
- Remove duplicate `_resolve_version` function in `cmd_restore.py`
- Clean up `__import__("pathlib")` usage in diff command
- Fix import organization in `cmd_diff.py`

### Changed
- Improved code cleanliness and maintainability

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
0.2.0  →  1.0.0  (major: breaking changes)
```

---

## Links

- [GitHub Releases](https://github.com/username/vesi/releases)
- [PyPI Package](https://pypi.org/project/vesi-vcs/) (coming soon)
