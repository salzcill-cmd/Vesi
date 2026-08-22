# Contributing to vesi

Terima kasih sudah tertarik berkontribusi ke vesi! 🎉

## Table of Contents

- [Cara Berkontribusi](#cara-berkontribusi)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Guidelines](#coding-guidelines)
- [Testing](#testing)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [RFC Process](#rfc-process)

## Cara Berkontribusi

### 1. Report Bugs

Jika kamu menemukan bug, buka [GitHub Issue](https://github.com/username/vesi/issues/new?template=bug_report.md) dengan:

- Deskripsi bug yang jelas
- Steps untuk mereproduksi
- Expected vs actual behavior
- Environment (OS, Python version)

### 2. Suggest Features

Untuk feature request, buka [GitHub Issue](https://github.com/username/vesi/issues/new?template=feature_request.md) dengan:

- Masalah yang ingin diselesaikan
- Solusi yang diinginkan
- Alternatif yang sudah dipertimbangkan

### 3. Submit Code

1. Fork repository
2. Buat branch baru: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m "feat: tambah fitur baru"`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buat Pull Request

## Development Setup

### Prerequisites

- Python 3.10 atau lebih baru
- pip atau uv

### Setup

```bash
# Clone repository
git clone https://github.com/username/vesi.git
cd vesi

# Install dalam mode development
pip install -e .

# Install dev dependencies
pip install pytest pytest-cov ruff mypy
```

### Menjalankan Tests

```bash
# Jalankan semua tests
PYTHONPATH=src pytest tests/ -v

# Jalankan tests tertentu
PYTHONPATH=src pytest tests/unit/test_parser.py -v

# Jalankan tests dengan coverage
PYTHONPATH=src pytest tests/ --cov=vesi --cov-report=html
```

### Code Quality

```bash
# Linting
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type checking (opsional)
mypy src/vesi --ignore-missing-imports
```

## Project Structure

```
vesi/
├── src/vesi/              # Source code
│   ├── cli/              # CLI entry point
│   ├── commands/         # Command handlers
│   ├── parser/           # Command parser
│   ├── core/             # Core logic
│   ├── storage/          # Object storage
│   ├── repository/       # Repository management
│   ├── diff/             # Diff engine
│   ├── merge/            # Merge engine
│   ├── errors/           # Exception classes
│   ├── utils/            # Utilities
│   └── education/        # Educational content
├── tests/                # Tests
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/            # End-to-end tests
└── docs/                 # Documentation
```

## Coding Guidelines

### Python Style

- Ikuti PEP 8
- Gunakan type hints
- Docstring untuk semua public functions
- Line length: 100 characters (dapat di-override untuk long strings)

### Naming Convention

- `snake_case` untuk functions dan variables
- `PascalCase` untuk classes
- `UPPER_SNAKE_CASE` untuk constants
- `cmd_<nama_command>` untuk command handlers

### Error Handling

- Gunakan exception classes yang sudah ada di `vesi/errors/exceptions.py`
- Error messages harus dalam Bahasa Indonesia
- Selalu berikan hint/solusi dalam error message

### Imports

```python
# Standard library
from __future__ import annotations
import json
from pathlib import Path

# Third party
import pytest

# Local
from vesi.parser.parser import parse_command
from vesi.commands.router import route_command
```

## Testing

### Unit Tests

Test individual functions/classes:

```python
def test_parse_command():
    cmd = parse_command("status")
    assert cmd.verb == "lihat"
    assert cmd.subcommand == "perubahan"
```

### Integration Tests

Test complete workflows:

```python
def test_basic_workflow(repo):
    (repo / "main.py").write_text("print('hello')")
    assert run_cmd("stel .") == 0
    assert run_cmd('simpan "initial"') == 0
```

### Test Fixtures

Gunakan fixtures yang sudah ada:

```python
@pytest.fixture
def repo(temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    parsed = parse_command("mulai proyek")
    cmd_mulai_proyek(parsed)
    return temp_dir
```

## Commit Messages

Gunakan format [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Deskripsi |
|------|-----------|
| `feat` | Fitur baru |
| `fix` | Bug fix |
| `docs` | Dokumentasi |
| `style` | Formatting, tidak mempengaruhi logic |
| `refactor` | Refactoring tanpa perubahan fitur |
| `test` | Menambahkan tests |
| `chore` | Maintenance tasks |

### Contoh

```
feat(parser): tambah alias untuk command branch
fix(merge): perbaiki fast-forward merge
docs: tambah README dengan contoh penggunaan
test: tambah unit tests untuk parser
```

## Pull Request Process

1. **Buat branch dari main**
   ```bash
   git checkout -b feat/nama-fitur
   ```

2. **Buat perubahan**
   - Ikuti coding guidelines
   - Tambahkan tests jika perlu
   - Update dokumentasi jika perlu

3. **Jalankan tests**
   ```bash
   PYTHONPATH=src pytest tests/ -v
   ```

4. **Commit dengan format yang benar**
   ```bash
   git commit -m "feat: tambah fitur baru"
   ```

5. **Push dan buat PR**
   ```bash
   git push origin feat/nama-fitur
   ```

6. **Isi PR template**
   - Deskripsi perubahan
   - Type of change
   - Checklist

### PR Requirements

- [ ] Tests pass
- [ ] Code linting passes
- [ ] Documentation updated (jika perlu)
- [ ] Commit messages follow convention

## RFC Process

Untuk perubahan besar (command language, repository format, dll), buat RFC:

1. Buat issue dengan label `rfc`
2. Deskripsikan:
   - Masalah yang ingin diselesaikan
   - Proposal solusi
   - Alternatif yang dipertimbangkan
   - Impact ke existing users
3. Diskusi dengan maintainer
4. Setelah disetujui, implementasi

## Questions?

Jika ada pertanyaan, buka [GitHub Discussion](https://github.com/username/vesi/discussions) atau hubungi maintainer.

---

Terima kasih sudah berkontribusi! 🙏
