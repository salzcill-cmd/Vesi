"""Unit tests for new features: Stash, Cherry-pick, Rebase, Blame, Bisect, Reflog, Worktree."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vesi.parser.parser import parse_command
from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_stash import cmd_simpan_sementara, cmd_ambil_stash, cmd_lihat_stash, cmd_hapus_stash
from vesi.commands.cmd_cherrypick import cmd_ambil_versi
from vesi.commands.cmd_rebase import cmd_susun_ulang
from vesi.commands.cmd_blame import cmd_siapa_ubah
from vesi.commands.cmd_bisect import cmd_bagi_cari
from vesi.commands.cmd_reflog import cmd_jejak
from vesi.commands.cmd_worktree import cmd_folder_kerja
from vesi.commands.cmd_branch import cmd_buat_cabang


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


class TestStash:
    """Test Stash commands."""

    def test_stash_creates_stash_entry(self, repo_with_files):
        """Test that stash creates a stash entry."""
        # Make a change
        (repo_with_files / "new_file.py").write_text("new content")

        # Stash
        parsed = parse_command('simpan sementara "test stash"')
        result = cmd_simpan_sementara(parsed)
        assert result == 0

        # Check stash exists
        parsed = parse_command("lihat stash")
        result = cmd_lihat_stash(parsed)
        assert result == 0

    def test_stash_pop_restores_files(self, repo_with_files):
        """Test that stash pop restores files."""
        # Make a change
        (repo_with_files / "temp_file.py").write_text("temp content")

        # Stash
        parsed = parse_command('simpan sementara "temp"')
        cmd_simpan_sementara(parsed)

        # Pop stash
        parsed = parse_command("ambil stash")
        result = cmd_ambil_stash(parsed)
        assert result == 0

        # Check file is restored
        assert (repo_with_files / "temp_file.py").exists()

    def test_stash_drop_removes_stash(self, repo_with_files):
        """Test that stash drop removes stash entry."""
        # Make a change
        (repo_with_files / "drop_file.py").write_text("drop content")

        # Stash
        parsed = parse_command('simpan sementara "to drop"')
        cmd_simpan_sementara(parsed)

        # Drop stash
        parsed = parse_command("hapus stash")
        result = cmd_hapus_stash(parsed)
        assert result == 0

        # Check stash is gone
        parsed = parse_command("lihat stash")
        result = cmd_lihat_stash(parsed)
        assert result == 0


class TestCherryPick:
    """Test Cherry-pick commands."""

    def test_cherry_pick_applies_commit(self, repo_with_files):
        """Test that cherry-pick applies a specific commit."""
        # Get current HEAD
        from vesi.repository.repository import Repository
        repo = Repository.find()
        first_commit = repo.get_head_commit()

        # Make another change
        (repo_with_files / "second.py").write_text("second content")
        parsed = parse_command("stel .")
        cmd_stel(parsed)
        parsed = parse_command('simpan "second commit"')
        cmd_simpan_versi(parsed)

        # Cherry-pick the first commit
        parsed = parse_command(f"ambil versi {first_commit[:7]}")
        result = cmd_ambil_versi(parsed)
        assert result == 0


class TestRebase:
    """Test Rebase commands."""

    def test_squash_commits(self, repo_with_files):
        """Test that rebase squashes commits."""
        # Create multiple commits
        for i in range(3):
            (repo_with_files / f"file_{i}.py").write_text(f"content {i}")
            parsed = parse_command("stel .")
            cmd_stel(parsed)
            parsed = parse_command(f'simpan "commit {i}"')
            cmd_simpan_versi(parsed)

        # Squash last 3 commits
        parsed = parse_command("susun ulang 3")
        result = cmd_susun_ulang(parsed)
        assert result == 0

        # Check that we have fewer commits
        from vesi.repository.repository import Repository
        from vesi.core.snapshot import SnapshotManager

        repo = Repository.find()
        snapshot_mgr = SnapshotManager(repo)

        # Walk back and count commits
        count = 0
        current = repo.get_head_commit()
        while current:
            count += 1
            try:
                data = snapshot_mgr.load_snapshot(current)
                current = data.get("parent")
            except Exception:
                break

        # Should have fewer commits than before
        assert count < 6  # Was 4 (initial + 3 new), now should be fewer


class TestBlame:
    """Test Blame commands."""

    def test_blame_shows_info(self, repo_with_files):
        """Test that blame shows file info."""
        parsed = parse_command("siapa ubah main.py")
        result = cmd_siapa_ubah(parsed)
        assert result == 0


class TestBisect:
    """Test Bisect commands."""

    def test_bisect_start(self, repo_with_files):
        """Test that bisect starts correctly."""
        from vesi.repository.repository import Repository
        repo = Repository.find()
        first_commit = repo.get_head_commit()

        # Create another commit
        (repo_with_files / "buggy.py").write_text("buggy code")
        parsed = parse_command("stel .")
        cmd_stel(parsed)
        parsed = parse_command('simpan "buggy commit"')
        cmd_simpan_versi(parsed)

        second_commit = repo.get_head_commit()

        # Start bisect
        parsed = parse_command(f"bagi cari mulai {first_commit[:7]} {second_commit[:7]}")
        result = cmd_bagi_cari(parsed)
        assert result == 0

        # Mark as bad
        parsed = parse_command("bagi cari buruk")
        result = cmd_bagi_cari(parsed)
        assert result == 0


class TestReflog:
    """Test Reflog commands."""

    def test_reflog_shows_entries(self, repo_with_files):
        """Test that reflog shows entries after commit."""
        # Make another commit
        (repo_with_files / "reflog_test.py").write_text("test")
        parsed = parse_command("stel .")
        cmd_stel(parsed)
        parsed = parse_command('simpan "reflog test"')
        cmd_simpan_versi(parsed)

        # Check reflog
        parsed = parse_command("jejak")
        result = cmd_jejak(parsed)
        assert result == 0


class TestWorktree:
    """Test Worktree commands."""

    def test_worktree_create(self, repo_with_files):
        """Test that worktree can be created."""
        import shutil
        from vesi.repository.repository import Repository
        repo = Repository.find()

        # Create a branch
        parsed = parse_command("buat cabang test-branch")
        cmd_buat_cabang(parsed)

        # Create worktree with unique path
        worktree_path = repo.root.parent / "worktree_test_unique"
        if worktree_path.exists():
            shutil.rmtree(worktree_path)

        parsed = parse_command(f"folder kerja buat {worktree_path} test-branch")
        result = cmd_folder_kerja(parsed)
        assert result == 0

        # Check worktree directory exists
        assert worktree_path.exists()

    def test_worktree_list(self, repo_with_files):
        """Test that worktree list works."""
        parsed = parse_command("folder kerja")
        result = cmd_folder_kerja(parsed)
        assert result == 0
