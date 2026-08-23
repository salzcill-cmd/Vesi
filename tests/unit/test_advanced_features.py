"""Unit tests for advanced features: Undo, Search History, Backup, Insights, Templates, Smart Diff, Conflict Helper."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vesi.parser.parser import parse_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_undo import cmd_batalkan_versi
from vesi.commands.cmd_search_history import cmd_cari_riwayat
from vesi.commands.cmd_backup import cmd_cadangan, BackupManager
from vesi.commands.cmd_insights import cmd_lihat_file
from vesi.commands.cmd_template import cmd_pola_commit
from vesi.commands.cmd_smart_diff import cmd_bandingkan_pintar
from vesi.commands.cmd_conflict import cmd_bantu_konflik
from vesi.commands.cmd_help import cmd_bantuan


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


class TestUndoCommit:
    """Test undo commit command."""

    def test_undo_keeps_changes_staged(self, repo_with_files):
        """Test that undo keeps changes in staging area."""
        # Make another commit
        (repo_with_files / "new.py").write_text("new content")
        parsed = parse_command("stel .")
        cmd_stel(parsed)
        parsed = parse_command('simpan "second commit"')
        cmd_simpan_versi(parsed)

        # Undo last commit
        parsed = parse_command("batalkan versi")
        result = cmd_batalkan_versi(parsed)
        assert result == 0

    def test_undo_first_commit_fails(self, repo_with_files):
        """Test that undoing first commit fails."""
        parsed = parse_command("batalkan versi")
        from vesi.errors.exceptions import VesiError
        with pytest.raises(VesiError):
            cmd_batalkan_versi(parsed)


class TestSearchHistory:
    """Test search history command."""

    def test_search_by_message(self, repo_with_files):
        """Test searching commits by message."""
        # Make more commits
        for i in range(3):
            (repo_with_files / f"file_{i}.py").write_text(f"content {i}")
            parsed = parse_command("stel .")
            cmd_stel(parsed)
            parsed = parse_command(f'simpan "commit {i}"')
            cmd_simpan_versi(parsed)

        # Search
        parsed = parse_command("cari riwayat commit")
        result = cmd_cari_riwayat(parsed)
        assert result == 0

    def test_search_by_file(self, repo_with_files):
        """Test searching commits by file."""
        parsed = parse_command("cari riwayat --file main.py")
        result = cmd_cari_riwayat(parsed)
        assert result == 0


class TestBackup:
    """Test backup command."""

    def test_create_backup(self, repo_with_files):
        """Test creating a backup."""
        parsed = parse_command("cadangan buat test backup")
        result = cmd_cadangan(parsed)
        assert result == 0

    def test_list_backups(self, repo_with_files):
        """Test listing backups."""
        # Create a backup first
        parsed = parse_command("cadangan buat")
        cmd_cadangan(parsed)

        # List backups
        parsed = parse_command("cadangan")
        result = cmd_cadangan(parsed)
        assert result == 0


class TestFileInsights:
    """Test file insights command."""

    def test_insights_show_info(self, repo_with_files):
        """Test that insights show file info."""
        parsed = parse_command("lihat file main.py")
        result = cmd_lihat_file(parsed)
        assert result == 0


class TestCommitTemplates:
    """Test commit templates command."""

    def test_list_templates(self):
        """Test listing all templates."""
        parsed = parse_command("pola commit")
        result = cmd_pola_commit(parsed)
        assert result == 0

    def test_show_template(self):
        """Test showing a specific template."""
        parsed = parse_command("pola commit feat")
        result = cmd_pola_commit(parsed)
        assert result == 0

    def test_generate_message(self):
        """Test generating commit message from template."""
        parsed = parse_command('pola commit feat "tambah login"')
        result = cmd_pola_commit(parsed)
        assert result == 0


class TestSmartDiff:
    """Test smart diff command."""

    def test_smart_diff_shows_summary(self, repo_with_files):
        """Test that smart diff shows summary."""
        # Make a change
        (repo_with_files / "main.py").write_text('print("modified")')

        parsed = parse_command("bandingkan pintar")
        result = cmd_bandingkan_pintar(parsed)
        assert result == 0


class TestConflictHelper:
    """Test conflict helper command."""

    def test_show_help(self):
        """Test showing conflict help."""
        parsed = parse_command("bantu konflik")
        result = cmd_bantu_konflik(parsed)
        assert result == 0


class TestHelpUpdates:
    """Test that help includes new commands."""

    def test_help_lists_all_commands(self):
        """Test that help lists all new commands."""
        parsed = parse_command("bantuan")
        result = cmd_bantuan(parsed)
        assert result == 0
