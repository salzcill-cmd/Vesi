"""Command: beri tag - Tag system for versions."""

from __future__ import annotations

import time
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VersionNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class TagManager:
    """Manages tags in the repository."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.tags_dir = repo.vesi_dir / "refs" / "tags"
        self.tags_dir.mkdir(parents=True, exist_ok=True)

    def create_tag(self, name: str, commit_hash: str, message: str = "") -> None:
        """Create a new tag pointing to a commit."""
        tag_path = self.tags_dir / name
        if tag_path.is_file():
            raise VesiError(
                f"Tag '{name}' sudah ada.",
                hint="Gunakan nama tag yang berbeda atau hapus tag yang ada.",
            )

        tag_data = {
            "commit": commit_hash,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "author": self.repo.get_author(),
        }

        import json
        tag_path.write_text(json.dumps(tag_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get_tag(self, name: str) -> dict | None:
        """Get tag data by name."""
        tag_path = self.tags_dir / name
        if not tag_path.is_file():
            return None

        import json
        return json.loads(tag_path.read_text(encoding="utf-8"))

    def list_tags(self) -> list[dict]:
        """List all tags."""
        tags = []
        for tag_file in sorted(self.tags_dir.iterdir()):
            if tag_file.is_file():
                import json
                data = json.loads(tag_file.read_text(encoding="utf-8"))
                data["name"] = tag_file.name
                tags.append(data)
        return tags

    def delete_tag(self, name: str) -> bool:
        """Delete a tag."""
        tag_path = self.tags_dir / name
        if tag_path.is_file():
            tag_path.unlink()
            return True
        return False

    def tag_exists(self, name: str) -> bool:
        """Check if tag exists."""
        return (self.tags_dir / name).is_file()


def cmd_beri_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a tag for a version."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    tag_mgr = TagManager(repo)

    if not parsed.args:
        # List all tags
        return _list_tags(tag_mgr)

    tag_name = parsed.args[0]
    message = parsed.first_arg if len(parsed.args) > 1 else ""

    # Get commit hash (default to HEAD)
    commit_hash = repo.get_head_commit()
    if not commit_hash:
        raise VesiError("Belum ada versi yang bisa ditag.")

    # Create tag
    tag_mgr.create_tag(tag_name, commit_hash, message)
    print_color(f"✓ Tag '{tag_name}' dibuat untuk versi {short_hash(commit_hash)}", "green")

    return 0


def cmd_lihat_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """List all tags."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    tag_mgr = TagManager(repo)
    return _list_tags(tag_mgr)


def cmd_hapus_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Delete a tag."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama tag yang akan dihapus.",
            hint="Contoh:\n    hapus tag v1.0.0",
        )

    tag_name = parsed.args[0]
    tag_mgr = TagManager(repo)

    if not tag_mgr.delete_tag(tag_name):
        raise VesiError(f"Tag '{tag_name}' tidak ditemukan.")

    print_color(f"✓ Tag '{tag_name}' dihapus.", "green")
    return 0


def _list_tags(tag_mgr: TagManager) -> int:
    """List all tags."""
    tags = tag_mgr.list_tags()

    if not tags:
        print("Belum ada tag.")
        print("\nBuat tag baru:")
        print("  beri tag v1.0.0")
        print('  beri tag v1.0.0 "Rilis pertama"')
        return 0

    print(f"Tag ({len(tags)}):\n")
    for tag in tags:
        commit_short = tag.get("commit", "")[:7]
        message = tag.get("message", "")
        timestamp = tag.get("timestamp", "")[:10]

        print(f"  {tag['name']:<15} {commit_short}  {timestamp}")
        if message:
            print(f"  {'':15} {message}")

    return 0


def format_tags(tags: list[dict]) -> str:
    """Format tags for display."""
    if not tags:
        return "Belum ada tag."

    lines = [f"Tag ({len(tags)}):\n"]
    for tag in tags:
        commit_short = tag.get("commit", "")[:7]
        message = tag.get("message", "")
        timestamp = tag.get("timestamp", "")[:10]

        lines.append(f"  {tag['name']:<15} {commit_short}  {timestamp}")
        if message:
            lines.append(f"  {'':15} {message}")

    return "\n".join(lines)
