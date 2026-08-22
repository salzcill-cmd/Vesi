"""Integration tests for complete workflow scenarios."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vesi.parser.parser import parse_command
from vesi.commands.router import route_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_status import cmd_lihat_perubahan
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_log import cmd_lihat_riwayat
from vesi.commands.cmd_diff import cmd_bandingkan
from vesi.commands.cmd_restore import cmd_pulihkan
from vesi.commands.cmd_branch import (
    cmd_buat_cabang,
    cmd_lihat_cabang,
    cmd_pindah_cabang,
    cmd_hapus_cabang,
)
from vesi.commands.cmd_merge import cmd_gabungkan
from vesi.commands.cmd_check import cmd_cek
from vesi.commands.cmd_config import cmd_konfigurasi
from vesi.commands.cmd_explain import cmd_jelaskan


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


def run_cmd(cmd_str: str, cwd: Path | None = None) -> int:
    """Helper to run a command string."""
    parsed = parse_command(cmd_str)
    return route_command(parsed)


class TestBeginnerWorkflow:
    """Test complete beginner workflow."""

    def test_basic_save_and_history(self, repo):
        """Test basic workflow: create file, save, view history."""
        # Create file
        (repo / "hello.py").write_text('print("hello world")')

        # Stage and commit
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "hello world"') == 0

        # View history
        assert run_cmd("riwayat") == 0

        # Verify file exists
        assert (repo / "hello.py").exists()


    def test_multiple_saves(self, repo):
        """Test multiple saves with history."""
        # First save
        (repo / "main.py").write_text("print('v1')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "v1"') == 0

        # Second save
        (repo / "main.py").write_text("print('v2')")
        assert run_cmd("stel main.py") == 0
        assert run_cmd('simpan "v2"') == 0

        # Third save
        (repo / "main.py").write_text("print('v3')")
        assert run_cmd("stel main.py") == 0
        assert run_cmd('simpan "v3"') == 0

        # View history (should have 3 versions)
        result = cmd_lihat_riwayat(parse_command("riwayat"))
        assert result == 0


    def test_status_shows_changes(self, repo):
        """Test status shows file changes correctly."""
        # Create files
        (repo / "new.py").write_text("print('new')")
        (repo / "tracked.py").write_text("print('tracked')")

        # Stage and commit tracked.py
        assert run_cmd("stel tracked.py") == 0
        assert run_cmd('simpan "add tracked"') == 0

        # Modify tracked.py
        (repo / "tracked.py").write_text("print('modified')")

        # Status should show new and modified
        result = cmd_lihat_perubahan(parse_command("status"))
        assert result == 0


class TestBranchWorkflow:
    """Test branch and merge workflow."""

    def test_create_switch_merge_delete(self, repo):
        """Test full branch lifecycle."""
        # Initial commit
        (repo / "main.py").write_text("print('main')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "initial"') == 0

        # Create branch
        assert run_cmd("cabang baru fitur") == 0

        # List branches
        assert run_cmd("cabang") == 0

        # Switch to branch
        assert run_cmd("cabang pindah fitur") == 0

        # Add commit on branch
        (repo / "feature.py").write_text("print('feature')")
        assert run_cmd("stel feature.py") == 0
        assert run_cmd('simpan "feature"') == 0

        # Switch back to main
        with patch('vesi.commands.cmd_branch.confirm', return_value=True):
            assert run_cmd("cabang pindah utama") == 0

        # Merge
        assert run_cmd("gabung fitur") == 0

        # Delete branch
        assert run_cmd("cabang hapus fitur") == 0

        # Verify feature.py exists after merge
        assert (repo / "feature.py").exists()


    def test_branch_diverged_merge(self, repo):
        """Test merge when branches have diverged."""
        # Initial commit
        (repo / "main.py").write_text("print('main')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "initial"') == 0

        # Create branch
        assert run_cmd("cabang baru fitur") == 0
        assert run_cmd("cabang pindah fitur") == 0

        # Commit on branch
        (repo / "main.py").write_text("print('feature')")
        assert run_cmd("stel main.py") == 0
        assert run_cmd('simpan "feature change"') == 0

        # Switch back and commit on main
        with patch('vesi.commands.cmd_branch.confirm', return_value=True):
            assert run_cmd("cabang pindah utama") == 0

        (repo / "main.py").write_text("print('main change')")
        assert run_cmd("stel main.py") == 0
        assert run_cmd('simpan "main change"') == 0

        # Merge (should be fast-forward or three-way)
        result = run_cmd("gabung fitur")
        # Result depends on merge strategy
        assert result in (0, 4)  # 0 = success, 4 = conflict


class TestRecoveryWorkflow:
    """Test file recovery and undo workflow."""

    def test_restore_file(self, repo):
        """Test restoring a file to previous version."""
        # Create and commit
        (repo / "main.py").write_text("print('original')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "original"') == 0

        # Modify file
        (repo / "main.py").write_text("print('modified')")

        # Restore file
        assert run_cmd("pulihkan main.py") == 0

        # Verify content is restored
        content = (repo / "main.py").read_text()
        assert "original" in content


    def test_diff_shows_changes(self, repo):
        """Test diff shows correct changes."""
        # Create and commit
        (repo / "main.py").write_text("line1\nline2\n")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "initial"') == 0

        # Modify file
        (repo / "main.py").write_text("line1\nmodified\nline3\n")

        # Diff should show changes
        result = cmd_bandingkan(parse_command("diff"))
        assert result == 0


class TestConfigWorkflow:
    """Test configuration workflow."""

    def test_set_and_get_config(self, repo):
        """Test setting and getting configuration."""
        # Set config
        assert run_cmd('konfigurasi user.name "Budi"') == 0
        assert run_cmd('konfigurasi user.email "budi@test.com"') == 0

        # Get config
        assert run_cmd("konfigurasi user.name") == 0

        # Show all config
        assert run_cmd("konfigurasi") == 0


class TestCheckWorkflow:
    """Test repository integrity check."""

    def test_check_clean_repo(self, repo):
        """Test check on clean repository."""
        # Create and commit
        (repo / "main.py").write_text("print('test')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "test"') == 0

        # Check integrity
        assert run_cmd("cek") == 0


class TestExplainWorkflow:
    """Test educational explain feature."""

    def test_explain_all_concepts(self, repo):
        """Test explaining all available concepts."""
        concepts = [
            "versi", "cabang", "gabungan", "staging",
            "riwayat", "perbandingan", "hash", "repository",
            "head", "konflik", "snapshot", "blob", "object",
            "ref", "ignore", "aliran kerja", "konfigurasi"
        ]

        for concept in concepts:
            result = cmd_jelaskan(parse_command(f"jelaskan {concept}"))
            assert result == 0, f"Failed to explain: {concept}"


class TestNaturalSyntax:
    """Test natural Indonesian syntax variations."""

    def test_all_single_word_aliases(self, repo):
        """Test all single-word command aliases."""
        aliases = [
            "status",
            "riwayat",
            "log",
            "cabang",
            "help",
            "cek",
        ]

        for alias in aliases:
            result = run_cmd(alias)
            assert result == 0, f"Failed alias: {alias}"


    def test_branch_natural_syntax(self, repo):
        """Test natural branch command syntax."""
        # Initial commit
        (repo / "main.py").write_text("print('main')")
        assert run_cmd("stel .") == 0
        assert run_cmd('simpan "initial"') == 0

        # Natural syntax
        assert run_cmd("cabang baru fitur") == 0
        assert run_cmd("cabang") == 0
        assert run_cmd("cabang pindah fitur") == 0

        with patch('vesi.commands.cmd_branch.confirm', return_value=True):
            assert run_cmd("cabang pindah utama") == 0

        assert run_cmd("cabang hapus fitur") == 0
