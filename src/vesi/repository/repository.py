"""Repository management - initialization, detection, and status."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from vesi.errors.exceptions import (
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)
from vesi.hashing import hash_file, short_hash
from vesi.repository.staging import Index
from vesi.storage.blob import BlobStore
from vesi.storage.objects import ObjectStore
from vesi.storage.refs import Refs
from vesi.storage.tree import Tree, TreeEntry
from vesi.utils.paths import REPO_DIR, get_repo_root


class Repository:
    """Represents a vesi repository."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.vesi_dir = self.root / REPO_DIR
        self.objects = ObjectStore(self.vesi_dir / "objects")
        self.blobs = BlobStore(self.objects)
        self.refs = Refs(self.vesi_dir / "refs")
        self.index = Index(self.vesi_dir / "index.json")

    @classmethod
    def find(cls, start: Path | None = None) -> Repository:
        """Find repository starting from start directory.

        Raises RepositoryNotFoundError if no repo found.
        """
        root = get_repo_root(start)
        if root is None:
            raise RepositoryNotFoundError()
        return cls(root)

    @classmethod
    def init(cls, path: Path) -> Repository:
        """Initialize a new repository at path.

        Raises RepositoryAlreadyExistsError if already exists.
        """
        path = path.resolve()
        vesi_dir = path / REPO_DIR

        if vesi_dir.is_dir():
            raise RepositoryAlreadyExistsError()

        # Create directory structure
        vesi_dir.mkdir(parents=True, exist_ok=True)
        (vesi_dir / "objects").mkdir(exist_ok=True)
        (vesi_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)
        (vesi_dir / "backups").mkdir(exist_ok=True)

        repo = cls(path)

        # Initialize HEAD and refs
        repo.refs.init(initial_branch="utama")

        # Initialize config
        repo._init_config()

        # Create default .abaikan
        repo._create_default_ignore()

        # Initialize empty index
        repo.index.save({})

        return repo

    def _init_config(self) -> None:
        """Create default config file using the ConfigManager."""
        from vesi.config.manager import ConfigManager

        config_mgr = ConfigManager(self.vesi_dir)
        config_mgr.save_repo(config_mgr.template())

    def _create_default_ignore(self) -> None:
        """Create default .abaikan file."""
        ignore_path = self.root / ".abaikan"
        if ignore_path.exists():
            return
        default_patterns = [
            "# Compiled Python",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            "",
            "# Environment",
            ".env",
            ".env.*",
            "!.env.example",
            "",
            "# Node.js",
            "node_modules/",
            "",
            "# Build output",
            "dist/",
            "build/",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
            "",
            "# Editor",
            ".vscode/",
            ".idea/",
            "*.swp",
            "*.swo",
            "",
            "# Vesi internal",
            ".vesi/",
        ]
        ignore_path.write_text("\n".join(default_patterns) + "\n", encoding="utf-8")

    def get_head_commit(self) -> str | None:
        """Get the commit hash HEAD points to."""
        branch = self.refs.get_active_branch()
        if branch is None:
            head = self.refs.get_head()
            if head and len(head) >= 7:
                return head  # Detached HEAD
            return None
        return self.refs.get_branch_hash(branch)

    def get_config(self) -> dict[str, Any]:
        """Read repository config (flat key -> value format)."""
        from vesi.config.manager import ConfigManager

        config_mgr = ConfigManager(self.vesi_dir)
        return config_mgr.get_all()

    def set_config_value(self, key: str, value: str) -> None:
        """Set a config value. Key format: 'section.key' (e.g., 'user.name')."""
        from vesi.config.manager import ConfigManager

        config_mgr = ConfigManager(self.vesi_dir)
        config_mgr.set(key, value)
        self._migrate_legacy_config_file()

    def _migrate_legacy_config_file(self) -> None:
        """Convert legacy nested .vesi/config into flat config.json and remove old file."""
        legacy_path = self.vesi_dir / "config"
        if legacy_path.is_file():
            try:
                legacy_path.unlink()
            except OSError:
                pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a single config value by key, with schema-aware typing."""
        from vesi.config.manager import ConfigManager

        config_mgr = ConfigManager(self.vesi_dir)
        return config_mgr.get(key, default)

    def get_author(self) -> str:
        """Get author name from config."""
        config = self.get_config()
        name = config.get("user.name", "") or config.get("user", {}).get("name", "")
        if name:
            return name
        return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
