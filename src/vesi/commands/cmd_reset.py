"""Command: atur ulang - Reset to specific state."""

from __future__ import annotations

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import confirm, print_color


def _resolve_version(repo: Repository, version_str: str) -> str:
    """Resolve a version string to a full commit hash."""
    version_str = version_str.strip()

    if version_str.upper().startswith("HEAD"):
        base_hash = repo.get_head_commit()
        if not base_hash:
            raise VersionNotFoundError(version_str)
        if version_str.upper() == "HEAD":
            return base_hash
        if "~" in version_str:
            try:
                n = int(version_str.split("~")[1])
            except (ValueError, IndexError):
                raise VersionNotFoundError(version_str)
            snapshot_mgr = SnapshotManager(repo)
            current = base_hash
            for _ in range(n):
                try:
                    parent = snapshot_mgr.get_parent(current)
                    if not parent:
                        raise VersionNotFoundError(version_str)
                    current = parent
                except Exception:
                    raise VersionNotFoundError(version_str)
            return current

    # Try as branch name
    branches = repo.refs.list_branches()
    if version_str in branches:
        branch_hash = repo.refs.get_branch_hash(version_str)
        if branch_hash:
            return branch_hash

    # Try as short/full hash
    if len(version_str) >= 7:
        objects_dir = repo.vesi_dir / "objects"
        if objects_dir.is_dir():
            for prefix_dir in objects_dir.iterdir():
                if not prefix_dir.is_dir() or len(prefix_dir.name) != 2:
                    continue
                for obj_file in prefix_dir.iterdir():
                    if obj_file.is_file():
                        full_hash = prefix_dir.name + obj_file.name
                        if full_hash.startswith(version_str):
                            return full_hash

    raise VersionNotFoundError(version_str)


def cmd_atur_ulang(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Reset to a specific state.

    Modes:
      --soft    - Keep changes staged (default)
      --mixed   - Keep changes in working directory (unstage)
      --hard    - Discard all changes (DANGEROUS!)

    Usage:
      atur ulang <commit>           - Soft reset to commit
      atur ulang --mixed <commit>   - Mixed reset
      atur ulang --hard <commit>    - Hard reset (discards changes!)
      atur ulang HEAD~1             - Undo last commit (soft)
      atur ulang HEAD~3             - Undo last 3 commits
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Determine mode
    soft = "--soft" in parsed.flags
    mixed = "--mixed" in parsed.flags
    hard = "--hard" in parsed.flags

    # Default to soft if no mode specified
    if not soft and not mixed and not hard:
        soft = True

    args = parsed.args or []
    if not args:
        raise VesiError(
            "Tentukan commit atau jumlah commit.",
            hint="Contoh:\n  atur ulang HEAD~1\n  atur ulang --hard abc1234",
        )

    commit_str = args[0]

    # Resolve commit
    try:
        target_hash = _resolve_version(repo, commit_str)
    except VersionNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()

    if not current_hash:
        raise VesiError("Tidak ada commit.")

    if target_hash == current_hash:
        print_color("✓ Sudah berada di commit yang dituju.", "yellow")
        return 0

    # Get target commit info
    try:
        target_data = snapshot_mgr.load_snapshot(target_hash)
    except (FileNotFoundError, ValueError):
        raise VersionNotFoundError(commit_str)

    target_message = target_data.get("message", "")

    # Get current commit info
    try:
        current_data = snapshot_mgr.load_snapshot(current_hash)
        current_message = current_data.get("message", "")
    except (FileNotFoundError, ValueError):
        current_message = ""

    # Hard reset warning
    if hard:
        print_color("⚠ PERINGATAN: Hard reset akan menghapus semua perubahan!", "red")
        print(f"  Dari: {short_hash(current_hash)} ({current_message})")
        print(f"  Ke:   {short_hash(target_hash)} ({target_message})")
        if not confirm("Lanjutkan?", default=False):
            print("Dibatalkan.")
            return 0

    # Perform reset based on mode
    if soft:
        # Soft reset: move HEAD, keep changes staged
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "reset-soft", f"Reset ke {short_hash(target_hash)}", active_branch or "")

        print_color("✓ Soft reset berhasil!", "green")
        print(f"  Dari: {short_hash(current_hash)}")
        print(f"  Ke:   {short_hash(target_hash)}")
        print(f"  Perubahan tetap di-staging.")

    elif mixed:
        # Mixed reset: move HEAD, unstage changes
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Clear staging
        repo.index.clear()

        # Reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "reset-mixed", f"Reset ke {short_hash(target_hash)}", active_branch or "")

        print_color("✓ Mixed reset berhasil!", "green")
        print(f"  Dari: {short_hash(current_hash)}")
        print(f"  Ke:   {short_hash(target_hash)}")
        print(f"  Perubahan tetap di working directory (unstaged).")

    elif hard:
        # Hard reset: move HEAD, reset working directory
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Restore working directory from target commit
        try:
            target_tree = snapshot_mgr.get_tree(target_hash)
            for entry in target_tree.get_blob_entries():
                content = repo.blobs.load_content(entry.hash_id)
                file_path = repo.root / entry.path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)

            # Remove files not in target tree
            current_tree = snapshot_mgr.get_tree(current_hash)
            current_files = {e.path for e in current_tree.get_blob_entries()}
            target_files = {e.path for e in target_tree.get_blob_entries()}

            for filepath in current_files - target_files:
                file_path = repo.root / filepath
                if file_path.is_file():
                    file_path.unlink()
        except Exception as e:
            print_color(f"⚠ Error restoring files: {e}", "yellow")

        # Clear staging
        repo.index.clear()

        # Reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "reset-hard", f"Reset ke {short_hash(target_hash)}", active_branch or "")

        print_color("✓ Hard reset berhasil!", "green")
        print(f"  Dari: {short_hash(current_hash)}")
        print(f"  Ke:   {short_hash(target_hash)}")
        print(f"  Semua perubahan dibatalkan.")

    return 0
