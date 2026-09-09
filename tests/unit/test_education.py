"""Unit tests for the education/tutorial system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from vesi.education.lessons import LESSONS, get_lesson
from vesi.education.tutor import ProgressStore, Tutor, find_lesson
from vesi.parser.parser import parse_command
from vesi.commands.cmd_belajar import cmd_belajar
from vesi.commands.cmd_init import cmd_mulai_proyek


@pytest.fixture
def progress_dir(tmp_path):
    return tmp_path / ".vesi"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    parsed = parse_command("mulai proyek")
    cmd_mulai_proyek(parsed)
    from vesi.repository.repository import Repository
    return Repository.find()


class TestLessonsData:
    """The lesson curriculum is well-formed."""

    def test_lessons_have_unique_ids(self):
        ids = [l.id for l in LESSONS]
        assert len(ids) == len(set(ids))

    def test_lessons_start_with_beginner_topics(self):
        first = LESSONS[0]
        assert first.id == "mulai"

    def test_every_lesson_has_steps(self):
        for lesson in LESSONS:
            assert lesson.steps, f"Lesson '{lesson.id}' has no steps"

    def test_get_lesson_finds_by_id(self):
        assert get_lesson("simpan").id == "simpan"
        assert get_lesson("tidak-ada") is None


class TestFindLesson:
    def test_exact_id(self):
        assert find_lesson("cabang").id == "cabang"

    def test_title_keyword(self):
        lesson = find_lesson("menyimpan")
        assert lesson is not None
        assert lesson.id == "simpan"


class TestProgressStore:
    """Progress persists between sessions."""

    def test_start_empty(self, progress_dir):
        store = ProgressStore(progress_dir)
        assert store.completed_lessons() == []
        assert store.current_lesson() is None

    def test_mark_done_persists(self, progress_dir):
        store = ProgressStore(progress_dir)
        store.mark_step_done("mulai")
        fresh = ProgressStore(progress_dir)
        assert fresh.completed_lessons() == ["mulai"]

    def test_marks_only_once(self, progress_dir):
        store = ProgressStore(progress_dir)
        store.mark_step_done("mulai")
        store.mark_step_done("mulai")
        assert store.completed_lessons() == ["mulai"]

    def test_set_current(self, progress_dir):
        store = ProgressStore(progress_dir)
        store.set_current("simpan")
        assert store.current_lesson() == "simpan"

    def test_reset_clears(self, progress_dir):
        store = ProgressStore(progress_dir)
        store.mark_step_done("mulai")
        store.set_current("simpan")
        store.reset()
        assert store.completed_lessons() == []
        assert store.current_lesson() is None

    def test_corrupt_file_is_safe(self, progress_dir):
        progress_dir.mkdir(parents=True, exist_ok=True)
        (progress_dir / "progress.json").write_text("{corrupt", encoding="utf-8")
        store = ProgressStore(progress_dir)
        assert store.completed_lessons() == []

    def test_no_dir_returns_empty(self):
        store = ProgressStore(None)
        assert store.completed_lessons() == []
        assert store.current_lesson() is None


class TestLessonChecks:
    """The verification callbacks actually verify repo state."""

    def test_has_commits_fail_without_commits(self, repo):
        from vesi.education.lessons import _has_commits
        ok, _ = _has_commits(repo)
        assert ok is False

    def test_has_commits_ok_after_commit(self, repo, capsys):
        from vesi.commands.cmd_stage import cmd_stel
        from vesi.commands.cmd_commit import cmd_simpan_versi
        from vesi.education.lessons import _has_commits

        (repo.root / "a.txt").write_text("hello")
        cmd_stel(parse_command("stel ."))
        cmd_simpan_versi(parse_command('simpan "awal"'))
        capsys.readouterr()

        ok, message = _has_commits(repo)
        assert ok is True

    def test_has_branch_ok(self, repo, capsys):
        from vesi.commands.cmd_branch import cmd_buat_cabang
        from vesi.education.lessons import _has_branch, _is_on_branch

        cmd_buat_cabang(parse_command("buat cabang fitur-x"))
        capsys.readouterr()
        ok, _ = _has_branch(repo, "fitur-x")
        assert ok is True

        # Not currently on it
        ok, _ = _is_on_branch(repo, "fitur-x")
        assert ok is False


class TestCmdBelajar:
    """The belajar command routes to the tutor."""

    def test_list_lessons_exit_zero(self, repo, capsys):
        rc = cmd_belajar(parse_command("belajar"))
        capsys.readouterr()
        assert rc == 0

    def test_unknown_lesson_returns_one(self, repo, capsys):
        rc = cmd_belajar(parse_command("belajar tidak-ada"))
        capsys.readouterr()
        assert rc == 1

    def test_reset_progress(self, repo, capsys):
        from vesi.repository.repository import Repository
        from vesi.education.tutor import ProgressStore

        store = ProgressStore(repo.vesi_dir)
        store.mark_step_done("mulai")

        rc = cmd_belajar(parse_command("belajar --reset"))
        capsys.readouterr()
        assert rc == 0
        assert store.completed_lessons() == []

    def test_belajar_parses(self):
        assert parse_command("belajar").verb == "belajar"
        assert parse_command("belajar simpan").args == ["simpan"]