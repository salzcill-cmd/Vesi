"""Command: deskripsi - Describe current state relative to nearest tag."""

from __future__ import annotations

import re

from vesi.commands.cmd_tag import TagManager
from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_deskripsi(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Describe the current state relative to the nearest tag.

    Usage:
      deskripsi                - Describe current HEAD
      deskripsi <hash>         - Describe a specific commit
      deskripsi --tags         - Use lightweight tags only
      deskripsi --always       - Always show short hash if no tag found
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    snapshot_mgr = SnapshotManager(repo)
    tag_mgr = TagManager(repo)

    # Determine commit to describe
    args = parsed.args or []
    if args:
        from vesi.commands.cmd_blame import _resolve_version
        try:
            commit_hash = _resolve_version(repo, args[0])
        except Exception:
            raise VesiError(f"Commit '{args[0]}' tidak ditemukan.")
    else:
        commit_hash = repo.get_head_commit()
        if not commit_hash:
            raise VesiError("Belum ada commit.")

    # Get all tags with their commit hashes
    tags = tag_mgr.list_tags()

    # Find nearest ancestor tag
    nearest_tag = None
    distance = 0
    current = commit_hash
    max_depth = 1000

    tag_commits = {t["commit"]: t for t in tags}

    for _ in range(max_depth):
        if current in tag_commits:
            nearest_tag = tag_commits[current]
            break

        try:
            data = snapshot_mgr.load_snapshot(current)
            parent = data.get("parent")
            if not parent:
                break
            current = parent
            distance += 1
        except (FileNotFoundError, ValueError):
            break

    # Format description
    if nearest_tag:
        tag_name = nearest_tag["name"]
        if distance == 0:
            description = tag_name
        else:
            description = f"{tag_name}-{distance}-g{short_hash(commit_hash)}"

        print(description)

        if verbose:
            print(f"\nTag:    {tag_name}")
            print(f"Jarak:  {distance} commit")
            print(f"Commit: {short_hash(commit_hash)}")
            tag_msg = nearest_tag.get("message", "")
            if tag_msg:
                print(f"Pesan:  {tag_msg}")
    else:
        # No tag found
        always = "--always" in parsed.flags
        if always:
            print(short_hash(commit_hash))
        else:
            # Try to find the root commit
            root_distance = 0
            current = commit_hash
            while current:
                try:
                    data = snapshot_mgr.load_snapshot(current)
                    parent = data.get("parent")
                    if not parent:
                        break
                    current = parent
                    root_distance += 1
                except (FileNotFoundError, ValueError):
                    break

            print(f"v0.0.0-{root_distance + distance}-g{short_hash(commit_hash)}")

            if verbose:
                print(f"\nCommit: {short_hash(commit_hash)}")
                print(f"Jarak dari root: {root_distance + distance} commit")
                print(f"\n💡 Tips: Buat tag untuk versi yang lebih mudah diingat:")
                print(f"  beri tag v1.0.0")

    return 0
