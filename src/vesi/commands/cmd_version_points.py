"""Command: titik pulih - Named restore points for easy rollback."""

from __future__ import annotations

import json
import time
from pathlib import Path

from vesi.core.snapshot import SnapshotManager
from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


class VersionPointsManager:
    """Manages named restore points."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self.points_file = repo.vesi_dir / "version_points.json"

    def _load_points(self) -> list[dict]:
        """Load version points."""
        if not self.points_file.is_file():
            return []
        try:
            return json.loads(self.points_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save_points(self, points: list[dict]) -> None:
        """Save version points."""
        self.points_file.write_text(
            json.dumps(points, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_point(self, name: str, commit_hash: str, description: str = "") -> dict:
        """Create a named restore point."""
        points = self._load_points()

        # Check if name already exists
        for p in points:
            if p.get("name") == name:
                raise VesiError(
                    f"Titik pulih '{name}' sudah ada.",
                    hint="Gunakan nama yang berbeda atau hapus yang lama.",
                )

        point = {
            "name": name,
            "hash": commit_hash,
            "description": description,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        points.append(point)
        self._save_points(points)

        return point

    def get_point(self, name: str) -> dict | None:
        """Get a restore point by name."""
        points = self._load_points()
        for p in points:
            if p.get("name") == name:
                return p
        return None

    def list_points(self) -> list[dict]:
        """List all restore points."""
        return self._load_points()

    def delete_point(self, name: str) -> bool:
        """Delete a restore point."""
        points = self._load_points()
        for i, p in enumerate(points):
            if p.get("name") == name:
                points.pop(i)
                self._save_points(points)
                return True
        return False


def cmd_titik_pulih(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Named restore points.

    Usage:
      titik pulih buat <nama> [desc]  - Create restore point
      titik pulih                      - List all restore points
      titik pulih <nama>               - Restore to named point
      titik pulih hapus <nama>         - Delete restore point
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    vp_mgr = VersionPointsManager(repo)
    snapshot_mgr = SnapshotManager(repo)

    sub = parsed.subcommand or ""
    args = parsed.args or []

    if sub in ("buat", "create", "add"):
        # Create restore point
        if not args:
            raise VesiError("Tentukan nama titik pulih.")

        name = args[0]
        description = " ".join(args[1:]) if len(args) > 1 else ""

        current_hash = repo.get_head_commit()
        if not current_hash:
            raise VesiError("Belum ada commit.")

        try:
            point = vp_mgr.add_point(name, current_hash, description)
            print_color("Titik pulih berhasil dibuat!", "green")
            print(f"  Nama: {point['name']}")
            print(f"  Commit: {short_hash(point['hash'])}")
            if description:
                print(f"  Deskripsi: {description}")
        except VesiError as e:
            print_color(f"Error: {e}", "red")

    elif sub in ("hapus", "delete", "rm"):
        # Delete restore point
        if not args:
            raise VesiError("Tentukan nama titik pulih yang akan dihapus.")

        name = args[0]
        if vp_mgr.delete_point(name):
            print_color("Titik pulih berhasil dihapus.", "yellow")
        else:
            raise VesiError(f"Titik pulih '{name}' tidak ditemukan.")

    elif args:
        # Restore to named point
        name = args[0]
        point = vp_mgr.get_point(name)

        if not point:
            raise VesiError(f"Titik pulih '{name}' tidak ditemukan.")

        target_hash = point.get("hash", "")

        # Get target tree
        try:
            target_tree = snapshot_mgr.get_tree(target_hash)
        except Exception:
            raise VesiError(f"Gagal membaca commit {short_hash(target_hash)}.")

        # Restore files
        restored = []
        for entry in target_tree.get_blob_entries():
            blob_content = repo.objects.load_blob(entry.hash_id)
            file_path = repo.root / entry.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(blob_content)
            restored.append(entry.path)

        # Stage all files
        index = {}
        for entry in target_tree.get_blob_entries():
            index[entry.path] = entry.hash_id
        repo.index.save(index)

        # Update branch
        active_branch = repo.refs.get_active_branch()
        if active_branch:
            repo.refs.set_branch_hash(active_branch, target_hash)

        # Add reflog
        from vesi.commands.cmd_reflog import ReflogManager
        reflog = ReflogManager(repo)
        reflog.add_entry(target_hash, "restore-point", f"Pulih ke: {name}", active_branch or "")

        print_color("Berhasil dipulihkan!", "green")
        print(f"  Titik pulih: {name}")
        print(f"  Commit: {short_hash(target_hash)}")
        print(f"  File: {len(restored)} file dikembalikan")

    else:
        # List all restore points
        points = vp_mgr.list_points()

        if not points:
            print("Belum ada titik pulih.")
            print("\nBuat titik pulih baru:")
            print("  titik pulih buat sebelum-refactor")
            print('  titik pulih buat rilis-v1 "Sebelum rilis v1"')
        else:
            print(f"Titik pulih ({len(points)}):\n")
            for p in points:
                name = p.get("name", "")
                commit = short_hash(p.get("hash", ""))
                timestamp = p.get("timestamp", "")[:10]
                desc = p.get("description", "")

                print(f"  {name:<20} {commit}  {timestamp}")
                if desc:
                    print(f"  {'':20} {desc}")

            print(f"\nGunakan:")
            print(f"  titik pulih <nama>        Pulih ke titik ini")
            print(f"  titik pulih hapus <nama>  Hapus titik ini")

    return 0
