"""Tests for Bagian 2 MVP Phase A polish: exit codes, --json, aliases, status.

Covers PRD sections 53 (exit codes), 54 (--json), 56 (aliases), 16.1/16.2/16.3.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from vesi.errors.exceptions import (
    AbortOperationError,
    ConflictError,
    IntegrityError,
    NoChangesError,
    RepositoryNotFoundError,
    VesiError,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def run_vesi(args, cwd, env=None):
    """Run the vesi CLI as a subprocess."""
    cmd = ["python3", "-m", "vesi.cli.app"] + args
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(
        Path(__file__).parent.parent.parent / "src"
    )
    if env:
        test_env.update(env)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=test_env,
    )


class TestExitCodeTaxonomy:
    """PRD 53: exit code taxonomy."""

    def test_generic_default_is_one(self):
        assert VesiError("x").exit_code == 1

    def test_invalid_usage_codes(self):
        assert NoChangesError().exit_code == 2

    def test_repository_error_code(self):
        assert RepositoryNotFoundError().exit_code == 3

    def test_conflict_code(self):
        assert ConflictError(["a"]).exit_code == 4

    def test_integrity_code(self):
        assert IntegrityError("x").exit_code == 5

    def test_abort_code(self):
        assert AbortOperationError().exit_code == 6

    def test_cli_no_changes_returns_2(self, temp_dir):
        # Init, stage a file, commit, then try to commit again with nothing new.
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)
        result = run_vesi(["simpan", "again"], temp_dir)
        assert result.returncode == 2

    def test_cli_no_changes_json_reports_exit_code(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        run_vesi(["simpan", "initial"], temp_dir)
        result = run_vesi(["simpan", "again", "--json"], temp_dir)
        assert result.returncode == 2
        payload = json.loads(result.stdout)
        assert payload["error"] is True
        assert payload["exit_code"] == 2


class TestJsonOutput:
    """PRD 54: --json produces machine-readable output."""

    def test_json_success_envelope(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        result = run_vesi(["simpan", "versi1", "--json"], temp_dir)
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["success"] is True
        assert payload["exit_code"] == 0
        assert "Versi tersimpan" in payload["output"]

    def test_json_is_pure_json(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        result = run_vesi(["simpan", "versi1", "--json"], temp_dir)
        # Output must be a single valid JSON object with no extra text.
        json.loads(result.stdout)
        assert result.stdout.strip().startswith("{")


class TestCommitSize:
    """Ukuran output on simpan versi."""

    def test_commit_shows_size(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("x" * 2048)
        run_vesi(["stel", "."], temp_dir)
        result = run_vesi(["simpan", "versi1"], temp_dir)
        assert result.returncode == 0
        assert "Ukuran:" in result.stdout


class TestStatusMarker:
    """PRD 16.2: '.' marks staged files that are ready to commit."""

    def test_staged_ready_marker(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        # Newly staged files not committed yet -> ready to commit ('.').
        result = run_vesi(["status"], temp_dir)
        assert ". main.py" in result.stdout


class TestCustomAlias:
    """PRD 56: custom aliases are actually executed."""

    def test_custom_alias_executes(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        # Create an alias 'st' -> 'stel'.
        run_vesi(["alias", "tambah", "st", "stel"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        result = run_vesi(["st", "."], temp_dir)
        assert result.returncode == 0
        assert "disiapkan" in result.stdout

    def test_custom_alias_does_not_override_canonical(self, temp_dir):
        run_vesi(["mulai"], temp_dir)
        # Try to alias an existing canonical command name (rule 1: ignored).
        run_vesi(["alias", "tambah", "simpan", "status"], temp_dir)
        (temp_dir / "main.py").write_text("print('hi')\n")
        run_vesi(["stel", "."], temp_dir)
        # 'simpan' must still behave as commit, not as status.
        result = run_vesi(["simpan", "pesan"], temp_dir)
        assert "Versi tersimpan" in result.stdout
