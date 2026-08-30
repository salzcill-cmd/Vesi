"""Command: beri tag - Tag system for versions with lightweight and annotated support."""

from __future__ import annotations

import fnmatch
import json
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

    def create_annotated_tag(
        self,
        name: str,
        commit_hash: str,
        message: str = "",
        author: str = "",
    ) -> dict:
        """Create an annotated tag (with metadata).

        Like 'git tag -a'.
        """
        tag_path = self.tags_dir / name
        if tag_path.is_file():
            raise VesiError(
                f"Tag '{name}' sudah ada.",
                hint="Gunakan nama tag yang berbeda atau hapus tag yang ada:\n    hapus tag <nama>",
            )

        tag_data = {
            "type": "annotated",
            "commit": commit_hash,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "author": author or self.repo.get_author(),
            "tagger": self.repo.get_author(),
        }

        tag_path.write_text(
            json.dumps(tag_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return tag_data

    def create_lightweight_tag(self, name: str, commit_hash: str) -> None:
        """Create a lightweight tag (just a reference).

        Like 'git tag' without -a/-m.
        """
        tag_path = self.tags_dir / name
        if tag_path.is_file():
            raise VesiError(
                f"Tag '{name}' sudah ada.",
                hint="Gunakan nama tag yang berbeda atau hapus tag yang ada.",
            )

        # Write just the commit hash (lightweight)
        tag_path.write_text(commit_hash, encoding="utf-8")

    def get_tag(self, name: str) -> dict | None:
        """Get tag data by name."""
        tag_path = self.tags_dir / name
        if not tag_path.is_file():
            return None

        content = tag_path.read_text(encoding="utf-8").strip()

        # Check if it's a lightweight tag (just a hash)
        if len(content) == 40 and all(c in "0123456789abcdef" for c in content):
            return {
                "type": "lightweight",
                "commit": content,
                "name": name,
            }

        # Annotated tag (JSON)
        try:
            data = json.loads(content)
            data["name"] = name
            return data
        except (json.JSONDecodeError, ValueError):
            return None

    def list_tags(self, pattern: str = "*") -> list[dict]:
        """List all tags, optionally filtered by pattern."""
        tags = []
        for tag_file in sorted(self.tags_dir.iterdir()):
            if tag_file.is_file():
                # Apply pattern filter
                if pattern != "*" and not fnmatch.fnmatch(tag_file.name, pattern):
                    continue

                content = tag_file.read_text(encoding="utf-8").strip()

                # Lightweight tag
                if len(content) == 40 and all(c in "0123456789abcdef" for c in content):
                    tags.append({
                        "name": tag_file.name,
                        "type": "lightweight",
                        "commit": content,
                    })
                else:
                    # Annotated tag
                    try:
                        data = json.loads(content)
                        data["name"] = tag_file.name
                        if "type" not in data:
                            data["type"] = "annotated"
                        tags.append(data)
                    except (json.JSONDecodeError, ValueError):
                        pass

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

    def verify_tag(self, name: str) -> dict:
        """Verify tag integrity.

        Returns verification result.
        """
        tag_data = self.get_tag(name)
        if not tag_data:
            return {"valid": False, "error": f"Tag '{name}' tidak ditemukan."}

        commit_hash = tag_data.get("commit", "")

        # Check if commit exists
        try:
            self.repo.objects.load_json(commit_hash)
            commit_exists = True
        except (FileNotFoundError, ValueError):
            commit_exists = False

        result = {
            "valid": commit_exists,
            "tag": tag_data,
            "commit_exists": commit_exists,
        }

        if not commit_exists:
            result["error"] = f"Commit '{short_hash(commit_hash)}' tidak ditemukan."

        return result

    def get_tag_by_commit(self, commit_hash: str) -> dict | None:
        """Find tag pointing to a specific commit."""
        for tag in self.list_tags():
            if tag.get("commit") == commit_hash:
                return tag
        return None

    def get_annotated_tags(self) -> list[dict]:
        """Get only annotated tags."""
        return [t for t in self.list_tags() if t.get("type") == "annotated"]

    def get_lightweight_tags(self) -> list[dict]:
        """Get only lightweight tags."""
        return [t for t in self.list_tags() if t.get("type") == "lightweight"]


def cmd_beri_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a tag for a version.

    Options:
      -a, --annotated   Create annotated tag (requires -m)
      -m, --message     Tag message (for annotated tags)
      -f, --force       Force tag (overwrite existing)
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    tag_mgr = TagManager(repo)

    if not parsed.args:
        # List all tags
        return _list_tags(tag_mgr)

    tag_name = parsed.args[0]
    force = "--force" in parsed.flags or "-f" in parsed.flags

    # Check if tag exists and force not set
    if tag_mgr.tag_exists(tag_name) and not force:
        raise VesiError(
            f"Tag '{tag_name}' sudah ada.",
            hint="Gunakan --force untuk menimpa tag yang ada.",
        )

    # Get commit hash (default to HEAD)
    commit_hash = repo.get_head_commit()
    if not commit_hash:
        raise VesiError("Belum ada versi yang bisa ditag.")

    # Determine tag type
    is_annotated = "--annotated" in parsed.flags or "-a" in parsed.flags
    message = _get_flag_value(parsed.flags, "--message") or _get_flag_value(parsed.flags, "-m") or ""

    if is_annotated:
        if not message:
            # Use first arg as message if provided
            message = parsed.args[1] if len(parsed.args) > 1 else ""
            if not message:
                raise VesiError(
                    "Tag annotated memerlukan pesan.",
                    hint="Contoh:\n  beri tag -a v1.0.0 -m \"Rilis pertama\"",
                )

        # Create annotated tag
        tag_data = tag_mgr.create_annotated_tag(tag_name, commit_hash, message, repo.get_author())
        print_color(f"✓ Tag annotated '{tag_name}' dibuat!", "green")
        print(f"  Commit: {short_hash(commit_hash)}")
        print(f"  Pesan: {message}")
        print(f"  Tagger: {tag_data.get('tagger', '')}")
    else:
        # Create lightweight tag
        tag_mgr.create_lightweight_tag(tag_name, commit_hash)
        print_color(f"✓ Tag '{tag_name}' dibuat untuk versi {short_hash(commit_hash)}", "green")

    return 0


def cmd_lihat_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """List all tags.

    Options:
      -l, --list        List tags (default)
      --contains <hash> Show tags containing a commit
      -n                Show tag message
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    tag_mgr = TagManager(repo)

    # Filter by pattern from args
    pattern = parsed.args[0] if parsed.args else "*"
    show_message = "-n" in parsed.flags or "--message" in parsed.flags

    tags = tag_mgr.list_tags(pattern)

    if not tags:
        print("Belum ada tag.")
        print("\nBuat tag baru:")
        print("  beri tag v1.0.0")
        print('  beri tag -a v1.0.0 -m "Rilis pertama"')
        return 0

    print(f"Tag ({len(tags)}):\n")
    for tag in tags:
        commit_short = tag.get("commit", "")[:7]
        tag_type = tag.get("type", "lightweight")
        message = tag.get("message", "")
        timestamp = tag.get("timestamp", "")[:10] if tag.get("timestamp") else ""

        # Format type indicator
        type_indicator = " (annotated)" if tag_type == "annotated" else ""

        print(f"  {tag['name']:<20} {commit_short}  {timestamp}{type_indicator}")

        if show_message and message:
            print(f"    {message}")

    return 0


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


def cmd_verify_tag(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Verify tag integrity.

    Usage:
      verifikasi tag <nama>   - Verify tag integrity
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan nama tag yang akan diverifikasi.",
            hint="Contoh:\n    verifikasi tag v1.0.0",
        )

    tag_name = parsed.args[0]
    tag_mgr = TagManager(repo)

    result = tag_mgr.verify_tag(tag_name)

    if result["valid"]:
        print_color(f"✓ Tag '{tag_name}' valid.", "green")
        tag_data = result["tag"]
        print(f"  Commit: {short_hash(tag_data.get('commit', ''))}")
        if tag_data.get("type") == "annotated":
            print(f"  Tagger: {tag_data.get('tagger', '')}")
            print(f"  Message: {tag_data.get('message', '')}")
    else:
        print_color(f"✗ Tag '{tag_name}' tidak valid!", "red")
        print(f"  Error: {result.get('error', 'Unknown')}")

    return 0


def _list_tags(tag_mgr: TagManager) -> int:
    """List all tags."""
    tags = tag_mgr.list_tags()

    if not tags:
        print("Belum ada tag.")
        print("\nBuat tag baru:")
        print("  beri tag v1.0.0")
        print('  beri tag -a v1.0.0 -m "Rilis pertama"')
        return 0

    print(f"Tag ({len(tags)}):\n")
    for tag in tags:
        commit_short = tag.get("commit", "")[:7]
        tag_type = tag.get("type", "lightweight")
        message = tag.get("message", "")

        type_indicator = " *" if tag_type == "annotated" else ""

        print(f"  {tag['name']:<15} {commit_short}  {message[:40]}{type_indicator}")

    print("\n  * = annotated tag")

    return 0


def _get_flag_value(flags: list[str], flag_name: str) -> str | None:
    """Extract value from --flag=value or --flag value."""
    for i, flag in enumerate(flags):
        if flag.startswith(f"{flag_name}="):
            return flag[len(flag_name) + 1:]
        if flag == flag_name and i + 1 < len(flags):
            return flags[i + 1]
    return None


def format_tags(tags: list[dict]) -> str:
    """Format tags for display."""
    if not tags:
        return "Belum ada tag."

    lines = [f"Tag ({len(tags)}):\n"]
    for tag in tags:
        commit_short = tag.get("commit", "")[:7]
        message = tag.get("message", "")
        timestamp = tag.get("timestamp", "")[:10] if tag.get("timestamp") else ""

        lines.append(f"  {tag['name']:<15} {commit_short}  {timestamp}")
        if message:
            lines.append(f"  {'':15} {message}")

    return "\n".join(lines)
