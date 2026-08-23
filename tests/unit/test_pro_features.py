"""Unit tests for pro features: Interactive, Stats, AutoSave, Export, Aliases, Lock, Merge Assistant."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vesi.parser.parser import parse_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_interactive import cmd_simpan_interaktif
from vesi.commands.cmd_stats import cmd_statistik
from vesi.commands.cmd_autosave import cmd_auto_simpan, AutoSaveManager
from vesi.commands.cmd_export import cmd_ekspor, cmd_impor
from vesi.commands.cmd_aliases import cmd_alias, AliasManager
from vesi.commands.cmd_lock import cmd_kunci_file, LockManager
from vesi.commands.cmd_merge_assistant import cmd_asisten_gabung


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repo(temp_dir, monkeypatch):
    """Create a new repository in temp directory."""
    monkeypatch.chdir(temp_dir)
    parsed = parse_command("mulai proyek")
    cmd_mulai_proyek(parsed)
    return temp_dir


@pytest.fixture
def repo_with_files(repo):
    """Create a repo with some test files."""
    # Create test files
    (repo / "main.py").write_text('print("hello")')
    (repo / "utils.py").write_text("def helper(): pass")

    # Stage and commit
    parsed = parse_command("stel .")
    cmd_stel(parsed)
    parsed = parse_command('simpan "initial commit"')
    cmd_simpan_versi(parsed)

    return repo


class TestInteractiveCommit:
    """Test interactive commit command."""

    def test_interactive_commit_non_interactive(self, repo_with_files):
        """Test interactive commit in non-interactive mode."""
        parsed = parse_command("simpan interaktif")
        result = cmd_simpan_interaktif(parsed)
        assert result == 0


class TestProjectStats:
    """Test project statistics command."""

    def test_stats_show_basic(self, repo_with_files):
        """Test showing basic stats."""
        parsed = parse_command("statistik")
        result = cmd_statistik(parsed)
        assert result == 0

    def test_stats_show_detail(self, repo_with_files):
        """Test showing detailed stats."""
        parsed = parse_command("statistik --detail")
        result = cmd_statistik(parsed)
        assert result == 0


class TestAutoSave:
    """Test auto-save command."""

    def test_autosave_enable(self, repo_with_files):
        """Test enabling auto-save."""
        parsed = parse_command("auto simpan aktifkan 60")
        result = cmd_auto_simpan(parsed)
        assert result == 0

    def test_autosave_disable(self, repo_with_files):
        """Test disabling auto-save."""
        parsed = parse_command("auto simpan nonaktifkan")
        result = cmd_auto_simpan(parsed)
        assert result == 0

    def test_autosave_status(self, repo_with_files):
        """Test showing auto-save status."""
        parsed = parse_command("auto simpan status")
        result = cmd_auto_simpan(parsed)
        assert result == 0


class TestExportImport:
    """Test export/import commands."""

    def test_export_to_zip(self, repo_with_files):
        """Test exporting to zip file."""
        parsed = parse_command("ekspor test-backup.zip")
        result = cmd_ekspor(parsed)
        assert result == 0

        # Check file exists
        assert (repo_with_files / "test-backup.zip").exists()


class TestCustomAliases:
    """Test custom aliases command."""

    def test_add_alias(self, repo_with_files):
        """Test adding an alias."""
        parsed = parse_command("alias tambah s simpan")
        result = cmd_alias(parsed)
        assert result == 0

    def test_list_aliases(self, repo_with_files):
        """Test listing aliases."""
        # Add an alias first
        parsed = parse_command("alias tambah s simpan")
        cmd_alias(parsed)

        # List aliases
        parsed = parse_command("alias list")
        result = cmd_alias(parsed)
        assert result == 0


class TestFileLocking:
    """Test file locking command."""

    def test_lock_file(self, repo_with_files):
        """Test locking a file."""
        parsed = parse_command("kunci file main.py")
        result = cmd_kunci_file(parsed)
        assert result == 0

    def test_list_locks(self, repo_with_files):
        """Test listing locked files."""
        # Lock a file first
        parsed = parse_command("kunci file main.py")
        cmd_kunci_file(parsed)

        # List locks
        parsed = parse_command("kunci")
        result = cmd_kunci_file(parsed)
        assert result == 0


class TestMergeAssistant:
    """Test merge assistant command."""

    def test_show_help(self):
        """Test showing merge assistant help."""
        parsed = parse_command("asisten gabung")
        result = cmd_asisten_gabung(parsed)
        assert result == 0
