"""Command: pesan pintar - Auto-generate commit messages from changes."""

from __future__ import annotations

from vesi.core.change import detect_changes
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


# Commit message templates based on change patterns
CHANGE_PATTERNS = {
    "new_file": {
        "keywords": ["baru", "tambah", "create", "new", "add"],
        "template": "tambah {file}",
    },
    "modify": {
        "keywords": ["ubah", "update", "edit", "modify", "fix"],
        "template": "ubah {file}",
    },
    "delete": {
        "keywords": ["hapus", "remove", "delete"],
        "template": "hapus {file}",
    },
}


def cmd_pesan_pintar(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Smart commit message generator.

    Usage:
      pesan pintar                 - Generate message from staged changes
      pesan pintar --apply         - Generate and use as commit message
      pesan pintar --template feat - Use specific template
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    flags = parsed.flags
    args = parsed.args or []
    apply_message = "--apply" in flags

    # Get staged changes
    index = repo.index.load()
    if not index:
        raise VesiError(
            "Tidak ada file yang di-staging.",
            hint="Gunakan 'vesi stel .' terlebih dahulu.",
        )

    # Get current tree
    snapshot_mgr = SnapshotManager(repo)
    current_hash = repo.get_head_commit()
    tree = None
    if current_hash:
        try:
            tree = snapshot_mgr.get_tree(current_hash)
        except Exception:
            pass

    # Detect changes
    changes = detect_changes(repo.root, tree, index)

    # Analyze changes
    new_files = [c.path for c in changes if c.change_type == "new"]
    modified_files = [c.path for c in changes if c.change_type == "modified"]
    deleted_files = [c.path for c in changes if c.change_type == "deleted"]

    # Generate message
    message = _generate_message(new_files, modified_files, deleted_files, args)

    # Show preview
    print_color("pesan pintar:\n", "cyan")
    print(f"  {message}")

    print(f"\nAnalisis perubahan:")
    if new_files:
        print(f"  File baru:    {len(new_files)}")
        for f in new_files[:5]:
            print(f"    + {f}")
    if modified_files:
        print(f"  File diubah:  {len(modified_files)}")
        for f in modified_files[:5]:
            print(f"    ~ {f}")
    if deleted_files:
        print(f"  File dihapus: {len(deleted_files)}")
        for f in deleted_files[:5]:
            print(f"    - {f}")

    # Apply if requested
    if apply_message:
        # Stage all changes first
        for change in changes:
            if change.new_hash:
                repo.index.stage_file(change.path, change.new_hash)

        # Create commit
        new_tree = Tree()
        staged = repo.index.load()
        for filepath, file_hash in (staged or {}).items():
            name = filepath.split("/")[-1]
            new_tree.add_blob(name, file_hash, filepath)

        author = repo.get_author()
        snapshot_hash = snapshot_mgr.create_snapshot(
            tree=new_tree,
            message=message,
            author=author,
            parent=current_hash,
        )

        # Update branch
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, snapshot_hash)

        # Add reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(snapshot_hash, "commit", message, active_branch or "")

        # Clear staging
        repo.index.clear()

        print_color(f"\nCommit berhasil!", "green")
        print(f"  Hash: {short_hash(snapshot_hash)}")
        print(f"  Pesan: {message}")

    return 0


def _generate_message(
    new_files: list[str],
    modified_files: list[str],
    deleted_files: list[str],
    args: list[str],
) -> str:
    """Generate commit message from changes."""
    # Use template if specified
    if args:
        template = args[0]
        if template in ("feat", "fix", "docs", "style", "refactor", "test", "chore"):
            # Count changes
            total = len(new_files) + len(modified_files) + len(deleted_files)
            if total == 1:
                file = (new_files + modified_files + deleted_files)[0]
                return f"{template}: {file}"
            else:
                return f"{template}: perubahan {total} file"

    # Auto-generate based on patterns
    parts = []

    if new_files:
        if len(new_files) == 1:
            parts.append(f"tambah {new_files[0]}")
        else:
            parts.append(f"tambah {len(new_files)} file baru")

    if modified_files:
        if len(modified_files) == 1:
            parts.append(f"ubah {modified_files[0]}")
        else:
            parts.append(f"ubah {len(modified_files)} file")

    if deleted_files:
        if len(deleted_files) == 1:
            parts.append(f"hapus {deleted_files[0]}")
        else:
            parts.append(f"hapus {len(deleted_files)} file")

    if not parts:
        return "update perubahan"

    # Combine parts
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} dan {parts[1]}"
    else:
        return f"{parts[0]}, {parts[1]}, dan {parts[2]}"


# Need to import Tree
from vesi.storage.tree import Tree
