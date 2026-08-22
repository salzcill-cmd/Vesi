"""Reference management - branches, HEAD, refs."""

from __future__ import annotations

from pathlib import Path


class Refs:
    """Manages branch references and HEAD."""

    def __init__(self, refs_dir: Path) -> None:
        self.refs_dir = refs_dir
        self.heads_dir = refs_dir / "heads"
        self.heads_dir.mkdir(parents=True, exist_ok=True)
        self._head_path = refs_dir.parent / "HEAD"

    def get_head(self) -> str | None:
        """Get the current HEAD reference.

        Returns branch name if HEAD points to a branch,
        or a commit hash if HEAD is detached.
        """
        if not self._head_path.is_file():
            return None
        content = self._head_path.read_text(encoding="utf-8").strip()
        # HEAD format: "ref: refs/heads/<branch>" or "<commit-hash>"
        if content.startswith("ref: "):
            ref_path = content[5:]  # "refs/heads/<branch>"
            branch_name = ref_path.split("/", 2)[-1]
            return branch_name
        return content  # Detached HEAD - return hash

    def set_head(self, target: str) -> None:
        """Set HEAD to point to a branch or commit.

        If target looks like a branch name (no hex chars only),
        set to ref. Otherwise set as detached.
        """
        # Check if it's a valid hex hash (detached)
        try:
            int(target, 16)
            if len(target) >= 7:
                self._head_path.write_text(target, encoding="utf-8")
                return
        except ValueError:
            pass

        # It's a branch name
        self._head_path.write_text(f"ref: refs/heads/{target}", encoding="utf-8")

    def get_branch_hash(self, branch_name: str) -> str | None:
        """Get the commit hash a branch points to."""
        branch_path = self.heads_dir / branch_name
        if not branch_path.is_file():
            return None
        return branch_path.read_text(encoding="utf-8").strip()

    def set_branch_hash(self, branch_name: str, commit_hash: str) -> None:
        """Set a branch to point to a commit hash."""
        branch_path = self.heads_dir / branch_name
        branch_path.parent.mkdir(parents=True, exist_ok=True)
        branch_path.write_text(commit_hash, encoding="utf-8")

    def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch reference. Returns True if deleted."""
        branch_path = self.heads_dir / branch_name
        if branch_path.is_file():
            branch_path.unlink()
            return True
        return False

    def list_branches(self) -> list[str]:
        """List all branch names."""
        if not self.heads_dir.is_dir():
            return []
        return sorted(
            entry.name for entry in self.heads_dir.iterdir() if entry.is_file()
        )

    def get_active_branch(self) -> str | None:
        """Get the name of the currently active branch, or None if detached."""
        head = self.get_head()
        if head is None:
            return None
        # If it's a branch name (not a hash), return it
        try:
            int(head, 16)
            if len(head) >= 7:
                return None  # Detached
        except ValueError:
            return head  # It's a branch name
        return None

    def init(self, initial_branch: str = "utama") -> None:
        """Initialize refs with a default branch."""
        self.set_head(initial_branch)
        self.set_branch_hash(initial_branch, "")
