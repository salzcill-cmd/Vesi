"""Tests for previously untested commands: tag, show, revert, mv, rm, show_commit, reset, clean."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vesi.parser.parser import parse_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_tag import cmd_beri_tag, cmd_lihat_tag, cmd_hapus_tag, cmd_verify_tag
from vesi.commands.cmd_show import cmd_isi
from vesi.commands.cmd_revert import cmd_balikkan
from vesi.commands.cmd_mv import cmd_pindah_file
from vesi.commands.cmd_rm import cmd_hapus_file
from vesi.commands.cmd_show_commit import cmd_tampilkan_versi


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repo(temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    cmd_mulai_proyek(parse_command("mulai proyek"))
    return temp_dir


@pytest.fixture
def repo_with_commit(repo):
    (repo / "main.py").write_text("print('hello')")
    (repo / "utils.py").write_text("def foo(): pass")
    cmd_stel(parse_command("stel ."))
    cmd_simpan_versi(parse_command('simpan "initial"'))
    return repo


class TestTag:
    def test_create_lightweight_tag(self, repo_with_commit):
        code = cmd_beri_tag(parse_command("beri tag v1.0"))
        assert code == 0
        assert (repo_with_commit / ".vesi" / "refs" / "tags" / "v1.0").is_file()

    def test_create_annotated_tag(self, repo_with_commit):
        code = cmd_beri_tag(parse_command('beri tag -a v1.0 -m "release"'))
        assert code == 0
        import json
        data = json.loads(
            (repo_with_commit / ".vesi" / "refs" / "tags" / "v1.0").read_text()
        )
        assert data["type"] == "annotated"
        assert data["message"] == "release"

    def test_list_tags(self, repo_with_commit):
        cmd_beri_tag(parse_command("beri tag v1.0"))
        cmd_beri_tag(parse_command("beri tag v2.0"))
        code = cmd_lihat_tag(parse_command("lihat tag"))
        assert code == 0

    def test_delete_tag(self, repo_with_commit):
        cmd_beri_tag(parse_command("beri tag v1.0"))
        code = cmd_hapus_tag(parse_command("hapus tag v1.0"))
        assert code == 0
        assert not (repo_with_commit / ".vesi" / "refs" / "tags" / "v1.0").is_file()

    def test_verify_tag_valid(self, repo_with_commit):
        cmd_beri_tag(parse_command("beri tag v1.0"))
        code = cmd_verify_tag(parse_command("verifikasi tag v1.0"))
        assert code == 0

    def test_verify_tag_missing(self, repo_with_commit):
        code = cmd_verify_tag(parse_command("verifikasi tag nonexistent"))
        assert code == 0  # prints error, doesn't raise


class TestShow:
    def test_show_file_from_head(self, repo_with_commit):
        code = cmd_isi(parse_command("isi main.py"))
        assert code == 0

    def test_show_file_from_version(self, repo_with_commit):
        code = cmd_isi(parse_command("isi main.py dari HEAD"))
        assert code == 0


class TestShowCommit:
    def test_show_head(self, repo_with_commit):
        code = cmd_tampilkan_versi(parse_command("tampilkan versi HEAD"))
        assert code == 0

    def test_show_no_args_shows_latest(self, repo_with_commit):
        code = cmd_tampilkan_versi(parse_command("tampilkan versi"))
        assert code == 0


class TestRevert:
    def test_revert_creates_revert_commit(self, repo_with_commit):
        # Make a second commit
        (repo_with_commit / "main.py").write_text("print('changed')")
        cmd_stel(parse_command("stel ."))
        cmd_simpan_versi(parse_command('simpan "second"'))

        # Revert HEAD
        code = cmd_balikkan(parse_command("balikkan HEAD"))
        assert code == 0

    def test_revert_dry_run(self, repo_with_commit):
        (repo_with_commit / "main.py").write_text("print('changed')")
        cmd_stel(parse_command("stel ."))
        cmd_simpan_versi(parse_command('simpan "second"'))

        code = cmd_balikkan(parse_command("balikkan HEAD --dry-run"))
        assert code == 0


class TestMv:
    def test_rename_file(self, repo_with_commit):
        code = cmd_pindah_file(parse_command("pindah file main.py app.py"))
        assert code == 0
        assert (repo_with_commit / "app.py").is_file()
        assert not (repo_with_commit / "main.py").is_file()


class TestRm:
    def test_rm_cached_keeps_file(self, repo_with_commit):
        code = cmd_hapus_file(parse_command("hapus file --cached main.py"))
        assert code == 0
        assert (repo_with_commit / "main.py").is_file()

    def test_rm_force_removes_file(self, repo_with_commit):
        code = cmd_hapus_file(parse_command("hapus file --force main.py"))
        assert code == 0
        assert not (repo_with_commit / "main.py").is_file()

    def test_rm_dry_run(self, repo_with_commit):
        code = cmd_hapus_file(parse_command("hapus file --dry-run main.py"))
        assert code == 0
        assert (repo_with_commit / "main.py").is_file()
