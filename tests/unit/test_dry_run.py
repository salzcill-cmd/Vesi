"""Tests for the --dry-run safety feature on destructive commands."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vesi.commands.cmd_revert import cmd_balikkan
from vesi.commands.cmd_rm import cmd_hapus_file
from vesi.commands.cmd_restore import cmd_batalkan_perubahan
from vesi.commands.cmd_reset import cmd_atur_ulang
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.parser.parser import parse_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.repository.repository import Repository


@pytest.fixture
def make_repo(tmp_path, monkeypatch):
    """Create a repo with two commits touching foo.txt."""

    def _make():
        monkeypatch.chdir(tmp_path)
        cmd_mulai_proyek(parse_command("mulai proyek"))
        (tmp_path / "foo.txt").write_text("baris satu\n")
        cmd_stel(parse_command("stel ."))
        cmd_simpan_versi(parse_command('simpan "commit satu"'))
        (tmp_path / "foo.txt").write_text("baris satu\nbaris dua\n")
        cmd_stel(parse_command("stel ."))
        cmd_simpan_versi(parse_command('simpan "commit dua"'))
        return Repository.find()

    return _make


class TestDryRunRevert:
    def test_dry_run_does_not_create_commit(self, make_repo, capsys):
        repo = make_repo()
        head_before = repo.get_head_commit()
        rc = cmd_balikkan(parse_command("balikkan HEAD --dry-run"))
        capsys.readouterr()
        assert rc == 0
        assert repo.get_head_commit() == head_before

    def test_dry_run_still_requires_commit(self, make_repo, capsys):
        from vesi.errors.exceptions import VesiError
        make_repo()
        with pytest.raises(VesiError):
            cmd_balikkan(parse_command("balikkan --dry-run"))
        capsys.readouterr()


class TestDryRunRm:
    def test_dry_run_keeps_file(self, make_repo, capsys):
        make_repo()
        (Path.cwd() / "temp.txt").write_text("foo")
        rc = cmd_hapus_file(parse_command("hapus file temp.txt --dry-run"))
        capsys.readouterr()
        assert rc == 0
        assert (Path.cwd() / "temp.txt").is_file()
        assert (Path.cwd() / "temp.txt").read_text() == "foo"


class TestDryRunRestore:
    def test_dry_run_keeps_changes(self, make_repo, capsys):
        make_repo()
        (Path.cwd() / "foo.txt").write_text("baris satu\nbaris DUA\n")
        rc = cmd_batalkan_perubahan(parse_command("batalkan perubahan foo.txt --dry-run"))
        capsys.readouterr()
        assert rc == 0
        assert "baris DUA" in (Path.cwd() / "foo.txt").read_text()


class TestDryRunReset:
    def test_dry_run_keeps_head(self, make_repo, capsys):
        repo = make_repo()
        head_before = repo.get_head_commit()
        rc = cmd_atur_ulang(parse_command("atur ulang HEAD~1 --dry-run"))
        capsys.readouterr()
        assert rc == 0
        assert repo.get_head_commit() == head_before

    def test_dry_run_hard_keeps_files(self, make_repo, capsys):
        make_repo()
        rc = cmd_atur_ulang(parse_command("atur ulang --hard HEAD~1 --dry-run"))
        capsys.readouterr()
        assert rc == 0
        content = (Path.cwd() / "foo.txt").read_text()
        assert "baris dua" in content  # working dir untouched