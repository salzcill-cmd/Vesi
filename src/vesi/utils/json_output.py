"""JSON output utilities for machine-readable output.

All commands can output JSON with --json flag.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Any
from datetime import datetime


@dataclass
class VesiOutput:
    """Standard output format for vesi commands."""

    success: bool = True
    command: str = ""
    data: Any = None
    error: str | None = None
    hint: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self, indent: int | None = None) -> str:
        """Convert to JSON string."""
        output = {
            "success": self.success,
            "command": self.command,
            "timestamp": self.timestamp,
        }

        if self.data is not None:
            output["data"] = self.data

        if self.error:
            output["error"] = self.error

        if self.hint:
            output["hint"] = self.hint

        return json.dumps(output, indent=indent, ensure_ascii=False, default=str)


@dataclass
class CommitOutput:
    """JSON output for a commit."""

    hash: str
    short_hash: str
    message: str
    author: str
    timestamp: str
    parent: str | None = None
    file_count: int = 0
    branch: str | None = None


@dataclass
class BranchOutput:
    """JSON output for a branch."""

    name: str
    commit_hash: str
    is_active: bool = False


@dataclass
class StatusOutput:
    """JSON output for status."""

    staged: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)


@dataclass
class DiffOutput:
    """JSON output for diff."""

    file: str
    status: str  # "added", "modified", "deleted"
    additions: int = 0
    deletions: int = 0
    hunks: list[dict] = field(default_factory=list)


@dataclass
class MergeOutput:
    """JSON output for merge."""

    success: bool
    merge_type: str
    conflicts: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class RemoteOutput:
    """JSON output for remote."""

    name: str
    url: str


@dataclass
class TagOutput:
    """JSON output for tag."""

    name: str
    commit: str
    type: str  # "lightweight" or "annotated"
    message: str = ""
    timestamp: str = ""


@dataclass
class ReflogOutput:
    """JSON output for reflog entry."""

    hash: str
    action: str
    message: str
    branch: str
    timestamp: str


class JsonFormatter:
    """Formats command output as JSON."""

    def __init__(self, pretty: bool = True) -> None:
        self.pretty = pretty
        self.indent = 2 if pretty else None

    def format(self, output: VesiOutput) -> str:
        """Format output as JSON."""
        return output.to_json(indent=self.indent)

    def format_commit(self, commit: CommitOutput) -> str:
        return self.format(VesiOutput(data=asdict(commit)))

    def format_branches(self, branches: list[BranchOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(b) for b in branches]))

    def format_status(self, status: StatusOutput) -> str:
        return self.format(VesiOutput(data=asdict(status)))

    def format_diff(self, diffs: list[DiffOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(d) for d in diffs]))

    def format_error(self, error: str, hint: str | None = None) -> str:
        return self.format(VesiOutput(
            success=False,
            error=error,
            hint=hint,
        ))

    def format_merge(self, result: MergeOutput) -> str:
        return self.format(VesiOutput(data=asdict(result)))

    def format_remotes(self, remotes: list[RemoteOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(r) for r in remotes]))

    def format_tags(self, tags: list[TagOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(t) for t in tags]))

    def format_reflog(self, entries: list[ReflogOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(e) for e in entries]))

    def format_history(self, commits: list[CommitOutput]) -> str:
        return self.format(VesiOutput(data=[asdict(c) for c in commits]))


def print_json(data: Any, pretty: bool = True) -> None:
    """Print data as JSON to stdout."""
    indent = 2 if pretty else None
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


def format_json_response(
    success: bool = True,
    data: Any = None,
    error: str | None = None,
    hint: str | None = None,
    command: str = "",
) -> str:
    """Format a JSON response."""
    output = VesiOutput(
        success=success,
        command=command,
        data=data,
        error=error,
        hint=hint,
    )
    return output.to_json(indent=2)
