"""End-to-end tests that run the CLI as a subprocess."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def vesi_cli():
    """Get the vesi CLI command."""
    # Use PYTHONPATH to ensure the module is found
    return ["python3", "-m", "vesi.cli.app"]


def run_vesi(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run vesi command as subprocess."""
    cmd = ["python3", "-m", "vesi.cli.app"] + args
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent / "src")
    if env:
        test_env.update(env)

    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=test_env,
    )


class TestCLI:
    """Test CLI as subprocess."""

    def test_version(self, temp_dir):
        """Test --version flag."""
        result = run_vesi(["--version"], temp_dir)
        assert result.returncode == 0
        assert "vesi" in result.stdout.lower()
        assert "0.1" in result.stdout  # Check for version 0.1.x

    def test_help(self, temp_dir):
        """Test --help flag."""
        result = run_vesi(["--help"], temp_dir)
        assert result.returncode == 0
        assert "mulai" in result.stdout.lower()

    def test_welcome(self, temp_dir):
        """Test welcome message when no args."""
        result = run_vesi([], temp_dir)
        assert result.returncode == 0
        assert "vesi" in result.stdout.lower()


class TestInitWorkflow:
    """Test initialization workflow."""

    def test_init_repository(self, temp_dir):
        """Test mulai proyek command."""
        result = run_vesi(["mulai"], temp_dir)
        assert result.returncode == 0
        assert (temp_dir / ".vesi").is_dir()
        assert (temp_dir / ".abaikan").is_file()

    def test_init_already_exists(self, temp_dir):
        """Test mulai proyek when repo already exists."""
        run_vesi(["mulai"], temp_dir)
        result = run_vesi(["mulai"], temp_dir)
        assert result.returncode != 0


class TestStatusWorkflow:
    """Test status workflow."""

    def test_status_clean(self, temp_dir):
        """Test status on clean repo."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        result = run_vesi(["status"], temp_dir)
        assert result.returncode == 0

    def test_status_with_changes(self, temp_dir):
        """Test status shows changes."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        # Modify file
        (temp_dir / "test.py").write_text("print('modified')")

        result = run_vesi(["status"], temp_dir)
        assert result.returncode == 0


class TestStageWorkflow:
    """Test staging workflow."""

    def test_stage_single_file(self, temp_dir):
        """Test staging a single file."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")

        result = run_vesi(["stel", "test.py"], temp_dir)
        assert result.returncode == 0

    def test_stage_all_files(self, temp_dir):
        """Test staging all files."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test1.py").write_text("print('test1')")
        (temp_dir / "test2.py").write_text("print('test2')")

        result = run_vesi(["stel", "."], temp_dir)
        assert result.returncode == 0


class TestCommitWorkflow:
    """Test commit workflow."""

    def test_commit_staged_files(self, temp_dir):
        """Test committing staged files."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)

        result = run_vesi(["simpan", "initial commit"], temp_dir)
        assert result.returncode == 0

    def test_commit_without_staged_files(self, temp_dir):
        """Test commit fails without staged files."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")

        result = run_vesi(["simpan", "test"], temp_dir)
        assert result.returncode != 0


class TestLogWorkflow:
    """Test log/history workflow."""

    def test_log_shows_history(self, temp_dir):
        """Test log shows commit history."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        result = run_vesi(["log"], temp_dir)
        assert result.returncode == 0
        assert "initial" in result.stdout


class TestBranchWorkflow:
    """Test branch workflow."""

    def test_create_branch(self, temp_dir):
        """Test creating a branch."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        result = run_vesi(["cabang", "baru", "fitur"], temp_dir)
        assert result.returncode == 0

    def test_list_branches(self, temp_dir):
        """Test listing branches."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)
        run_vesi(["cabang", "baru", "fitur"], temp_dir)

        result = run_vesi(["cabang"], temp_dir)
        assert result.returncode == 0
        assert "fitur" in result.stdout
        assert "utama" in result.stdout

    def test_switch_branch(self, temp_dir):
        """Test switching branches."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)
        run_vesi(["cabang", "baru", "fitur"], temp_dir)

        result = run_vesi(["cabang", "pindah", "fitur"], temp_dir)
        assert result.returncode == 0


class TestDiffWorkflow:
    """Test diff workflow."""

    def test_diff_shows_changes(self, temp_dir):
        """Test diff shows changes."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("line1\nline2\n")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        # Modify file
        (temp_dir / "test.py").write_text("line1\nmodified\n")

        result = run_vesi(["diff"], temp_dir)
        assert result.returncode == 0


class TestExplainWorkflow:
    """Test explain workflow."""

    def test_explain_concept(self, temp_dir):
        """Test explaining a concept."""
        run_vesi(["mulai"], temp_dir)

        result = run_vesi(["jelaskan", "versi"], temp_dir)
        assert result.returncode == 0
        assert "commit" in result.stdout.lower() or "versi" in result.stdout.lower()


class TestNaturalSyntax:
    """Test natural Indonesian syntax."""

    def test_single_word_aliases(self, temp_dir):
        """Test single-word command aliases."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        # Test aliases
        aliases = ["status", "log", "help", "cek"]
        for alias in aliases:
            result = run_vesi([alias], temp_dir)
            assert result.returncode == 0, f"Alias '{alias}' failed"

    def test_branch_natural_syntax(self, temp_dir):
        """Test natural branch syntax."""
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "test.py").write_text("print('test')")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)

        result = run_vesi(["cabang", "baru", "fitur"], temp_dir)
        assert result.returncode == 0

        result = run_vesi(["cabang"], temp_dir)
        assert result.returncode == 0
        assert "fitur" in result.stdout
