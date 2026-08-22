"""Branch management - create, list, switch, delete branches."""

from __future__ import annotations

from dataclasses import dataclass

from vesi.errors.exceptions import (
    BranchAlreadyExistsError,
    BranchNotFoundError,
    CannotDeleteActiveBranchError,
)
from vesi.repository.repository import Repository


@dataclass
class BranchInfo:
    """Info about a single branch."""

    name: str
    commit_hash: str
    is_active: bool = False


def create_branch(repo: Repository, name: str) -> str:
    """Create a new branch at the current HEAD.

    Returns the commit hash the branch points to.
    """
    branches = repo.refs.list_branches()
    if name in branches:
        raise BranchAlreadyExistsError(name)

    current_hash = repo.get_head_commit() or ""
    repo.refs.set_branch_hash(name, current_hash)
    return current_hash


def list_branches(repo: Repository) -> list[BranchInfo]:
    """List all branches with info."""
    branches = repo.refs.list_branches()
    active = repo.refs.get_active_branch()

    result: list[BranchInfo] = []
    for branch_name in branches:
        commit_hash = repo.refs.get_branch_hash(branch_name) or ""
        result.append(
            BranchInfo(
                name=branch_name,
                commit_hash=commit_hash,
                is_active=(branch_name == active),
            )
        )
    return result


def switch_branch(repo: Repository, name: str) -> str:
    """Switch to another branch.

    Returns the commit hash of the new branch.
    """
    branches = repo.refs.list_branches()
    if name not in branches:
        raise BranchNotFoundError(name)

    commit_hash = repo.refs.get_branch_hash(name) or ""
    repo.refs.set_head(name)
    return commit_hash


def delete_branch(repo: Repository, name: str, *, force: bool = False) -> bool:
    """Delete a branch.

    Raises CannotDeleteActiveBranchError if trying to delete active branch.
    """
    active = repo.refs.get_active_branch()
    if name == active:
        raise CannotDeleteActiveBranchError(name)

    branches = repo.refs.list_branches()
    if name not in branches:
        raise BranchNotFoundError(name)

    repo.refs.delete_branch(name)
    return True


def format_branches(branches: list[BranchInfo]) -> str:
    """Format branch list for display."""
    if not branches:
        return "Tidak ada cabang."

    lines = ["Cabang:"]
    for b in branches:
        prefix = "* " if b.is_active else "  "
        suffix = " (aktif)" if b.is_active else ""
        lines.append(f"  {prefix}{b.name}{suffix}")

    return "\n".join(lines)
