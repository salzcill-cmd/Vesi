"""Unit tests for command handlers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

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
from vesi.commands.cmd_help import cmd_bantuan
from vesi.commands.cmd_explain import cmd_jelaskan
from vesi.errors.exceptions import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repo(temp_dir, monkeypatch):
    """Create a new repository in temp directory."""
    # Change to temp directory
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


class TestCmdInit:
    """Test mulai proyek command."""

    def test_init_creates_repository(self, repo):
        vesi_dir = repo / ".vesi"
        assert vesi_dir.is_dir()
        assert (vesi_dir / "objects").is_dir()
        assert (vesi_dir / "refs").is_dir()
        assert (vesi_dir / "config").is_file()
        assert (repo / ".abaikan").is_file()

    def test_init_creates_head(self, repo):
        head_path = repo / ".vesi" / "HEAD"
        assert head_path.is_file()
        content = head_path.read_text()
        assert "refs/heads/utama" in content

    def test_init_creates_default_branch(self, repo):
        branch_path = repo / ".vesi" / "refs" / "heads" / "utama"
        assert branch_path.is_file()

    def test_init_already_exists(self, repo):
        with pytest.raises(RepositoryAlreadyExistsError):
            parsed = parse_command("mulai proyek")
            cmd_mulai_proyek(parsed)


class TestCmdStatus:
    """Test lihat perubahan command."""

    def test_status_shows_new_files(self, repo_with_files):
        # Create a new file
        (repo_with_files / "new.py").write_text("print('new')")

        parsed = parse_command("status")
        result = cmd_lihat_perubahan(parsed)
        assert result == 0

    def test_status_shows_modified_files(self, repo_with_files):
        # Modify existing file
        (repo_with_files / "main.py").write_text('print("modified")')

        parsed = parse_command("status")
        result = cmd_lihat_perubahan(parsed)
        assert result == 0

    def test_status_clean(self, repo_with_files):
        parsed = parse_command("status")
        result = cmd_lihat_perubahan(parsed)
        assert result == 0


class TestCmdStage:
    """Test stel command."""

    def test_stage_single_file(self, repo_with_files):
        (repo_with_files / "new.py").write_text("print('new')")

        parsed = parse_command("stel new.py")
        result = cmd_stel(parsed)
        assert result == 0

        # Verify file is staged
        index_path = repo_with_files / ".vesi" / "index.json"
        assert index_path.is_file()
        data = json.loads(index_path.read_text())
        assert "new.py" in data

    def test_stage_all_files(self, repo_with_files):
        (repo_with_files / "new.py").write_text("print('new')")

        parsed = parse_command("stel .")
        result = cmd_stel(parsed)
        assert result == 0


class TestCmdCommit:
    """Test simpan versi command."""

    def test_commit_staged_files(self, repo_with_files):
        (repo_with_files / "new.py").write_text("print('new')")
        parsed = parse_command("stel new.py")
        cmd_stel(parsed)

        parsed = parse_command('simpan "add new file"')
        result = cmd_simpan_versi(parsed)
        assert result == 0


class TestCmdLog:
    """Test lihat riwayat command."""

    def test_log_shows_history(self, repo_with_files):
        parsed = parse_command("riwayat")
        result = cmd_lihat_riwayat(parsed)
        assert result == 0

    def test_log_with_limit(self, repo_with_files):
        parsed = parse_command("riwayat 5")
        result = cmd_lihat_riwayat(parsed)
        assert result == 0

    def test_log_alias(self, repo_with_files):
        parsed = parse_command("log")
        result = cmd_lihat_riwayat(parsed)
        assert result == 0


class TestCmdDiff:
    """Test bandingkan command."""

    def test_diff_shows_changes(self, repo_with_files):
        # Modify a file
        (repo_with_files / "main.py").write_text('print("modified")')

        parsed = parse_command("diff")
        result = cmd_bandingkan(parsed)
        assert result == 0

    def test_diff_no_changes(self, repo_with_files):
        parsed = parse_command("diff")
        result = cmd_bandingkan(parsed)
        assert result == 0


class TestCmdBranch:
    """Test branch commands."""

    def test_create_branch(self, repo_with_files):
        parsed = parse_command("cabang baru fitur")
        result = cmd_buat_cabang(parsed)
        assert result == 0

        # Verify branch exists
        branch_path = repo_with_files / ".vesi" / "refs" / "heads" / "fitur"
        assert branch_path.is_file()

    def test_list_branches(self, repo_with_files):
        parsed = parse_command("cabang baru fitur")
        cmd_buat_cabang(parsed)

        parsed = parse_command("cabang")
        result = cmd_lihat_cabang(parsed)
        assert result == 0

    def test_switch_branch(self, repo_with_files):
        parsed = parse_command("cabang baru fitur")
        cmd_buat_cabang(parsed)

        parsed = parse_command("cabang pindah fitur")
        result = cmd_pindah_cabang(parsed)
        assert result == 0

        # Verify HEAD points to fitur
        head_path = repo_with_files / ".vesi" / "HEAD"
        content = head_path.read_text()
        assert "refs/heads/fitur" in content

    def test_delete_branch(self, repo_with_files):
        parsed = parse_command("cabang baru fitur")
        cmd_buat_cabang(parsed)

        # Switch to utama first
        parsed = parse_command("cabang pindah utama")
        cmd_pindah_cabang(parsed)

        parsed = parse_command("cabang hapus fitur")
        result = cmd_hapus_cabang(parsed)
        assert result == 0

        # Verify branch doesn't exist
        branch_path = repo_with_files / ".vesi" / "refs" / "heads" / "fitur"
        assert not branch_path.exists()


class TestCmdMerge:
    """Test gabungkan command."""

    def test_fast_forward_merge(self, repo_with_files):
        # Create branch, add commit, switch back, merge
        parsed = parse_command("cabang baru fitur")
        cmd_buat_cabang(parsed)

        parsed = parse_command("cabang pindah fitur")
        cmd_pindah_cabang(parsed)

        # Add commit on branch
        (repo_with_files / "feature.py").write_text("print('feature')")
        parsed = parse_command("stel feature.py")
        cmd_stel(parsed)

        parsed = parse_command('simpan "feature commit"')
        cmd_simpan_versi(parsed)

        # Clean working directory before switching
        # (no uncommitted changes)
        
        # Switch back to utama
        parsed = parse_command("cabang pindah utama")
        # Force switch by mocking confirm to return True
        with patch('vesi.commands.cmd_branch.confirm', return_value=True):
            result = cmd_pindah_cabang(parsed)
        assert result == 0

        # Merge
        parsed = parse_command("gabung fitur")
        result = cmd_gabungkan(parsed)
        assert result == 0


class TestCmdCheck:
    """Test cek command."""

    def test_check_integrity(self, repo_with_files):
        parsed = parse_command("cek")
        result = cmd_cek(parsed)
        assert result == 0

    def test_check_alias(self, repo_with_files):
        parsed = parse_command("check")
        result = cmd_cek(parsed)
        assert result == 0


class TestCmdConfig:
    """Test konfigurasi command."""

    def test_show_config(self, repo_with_files):
        parsed = parse_command("konfigurasi")
        result = cmd_konfigurasi(parsed)
        assert result == 0

    def test_set_config(self, repo_with_files):
        parsed = parse_command('konfigurasi user.name "Budi"')
        result = cmd_konfigurasi(parsed)
        assert result == 0

    def test_get_config(self, repo_with_files):
        parsed = parse_command('konfigurasi user.name "Budi"')
        cmd_konfigurasi(parsed)

        parsed = parse_command("konfigurasi user.name")
        result = cmd_konfigurasi(parsed)
        assert result == 0

    def test_config_alias(self, repo_with_files):
        parsed = parse_command('config user.email "test@test.com"')
        result = cmd_konfigurasi(parsed)
        assert result == 0


class TestCmdHelp:
    """Test bantuan command."""

    def test_help(self):
        parsed = parse_command("bantuan")
        result = cmd_bantuan(parsed)
        assert result == 0

    def test_help_command(self):
        parsed = parse_command("bantuan simpan")
        result = cmd_bantuan(parsed)
        assert result == 0

    def test_help_alias(self):
        parsed = parse_command("help")
        result = cmd_bantuan(parsed)
        assert result == 0


class TestCmdExplain:
    """Test jelaskan command."""

    def test_explain_concept(self):
        parsed = parse_command("jelaskan versi")
        result = cmd_jelaskan(parsed)
        assert result == 0

    def test_explain_list(self):
        parsed = parse_command("jelaskan")
        result = cmd_jelaskan(parsed)
        assert result == 0

    def test_explain_alias(self):
        parsed = parse_command("explain cabang")
        result = cmd_jelaskan(parsed)
        assert result == 0


class TestCmdRestore:
    """Test pulihkan command."""

    def test_restore_file(self, repo_with_files):
        # Modify file
        (repo_with_files / "main.py").write_text('print("modified")')

        parsed = parse_command("pulihkan main.py")
        result = cmd_pulihkan(parsed)
        assert result == 0

        # Verify file is restored
        content = (repo_with_files / "main.py").read_text()
        assert 'print("hello")' in content
