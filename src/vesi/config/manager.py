"""Config system - persistent user settings with validation.

Supports three layers of configuration (later layers override earlier):
  1. Defaults (built-in)
  2. Global config (~/.config/vesi/config.json)
  3. Repository config (.vesi/config)
  4. Environment variables (VESI_ prefix)

Type coercion: booleans ("true"/"1"/"yes"), integers, and strings are
automatically converted based on the value's declared schema.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from vesi.config.schema import CONFIG_SCHEMA, ConfigSchema


class ConfigManager:
    """Reads and writes configuration across scopes."""

    def __init__(self, repo_vesi_dir: Path | None = None) -> None:
        self.repo_vesi_dir = repo_vesi_dir
        self.schema = ConfigSchema(CONFIG_SCHEMA)

    @property
    def global_dir(self) -> Path:
        return Path.home() / ".config" / "vesi"

    @property
    def global_config_path(self) -> Path:
        return self.global_dir / "config.json"

    def get_repo_config_path(self) -> Path | None:
        if not self.repo_vesi_dir:
            return None
        json_path = self.repo_vesi_dir / "config.json"
        legacy_path = self.repo_vesi_dir / "config"
        if json_path.is_file():
            return json_path
        if legacy_path.is_file():
            return legacy_path
        return json_path

    def load_global(self) -> dict[str, Any]:
        """Load global configuration."""
        return _read_json(self.global_config_path)

    def save_global(self, data: dict[str, Any]) -> None:
        """Persist global configuration."""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        _write_json(self.global_config_path, data)

    def load_repo(self) -> dict[str, Any]:
        """Load repository-level configuration."""
        path = self.get_repo_config_path()
        if not path or not path.is_file():
            return {}
        data = _read_json(path)
        self.migrate_legacy_config(data)
        return data

    def migrate_legacy_config(self, data: dict[str, Any]) -> None:
        """Migrate old .vesi/config (nested under 'user') to flat schema.

        Older versions of vesi stored the config as:
          {"user": {"name": "", "email": ""}, "core": {"language": "id"}}
        The schema now expects flat section names like "user.name".
        """
        # Flatten legacy nested structure: {"user": {"name": "X"}} -> {"user.name": "X"}
        flat: dict[str, Any] = {}
        for section, value in list(data.items()):
            if isinstance(value, dict):
                for key, val in value.items():
                    flat[f"{section}.{key}"] = val
            else:
                flat[section] = value
        data.clear()
        data.update(flat)

    def save_repo(self, data: dict[str, Any]) -> None:
        """Persist repository-level configuration.

        Always writes config.json; legacy .vesi/config is left to callers
        to clean up after migration.
        """
        if not self.repo_vesi_dir:
            raise ValueError("ConfigManager created without repository path.")
        path = self.repo_vesi_dir / "config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(path, data)

    def get(
        self,
        key: str,
        default: Any = None,
        *,
        scope: str = "repo",
    ) -> Any:
        """Get a configuration value with type coercion.

        scopes: 'default' (schema only), 'global', 'repo', 'env', 'all'
        """
        schema = self.schema
        default = schema.get_default(key, default)

        repo_data = self.load_repo() if self.repo_vesi_dir else {}
        global_data = self.load_global()

        value = default
        if scope in ("global", "all") and global_data:
            value = global_data.get(key, value)
        if scope in ("repo", "all") and self.repo_vesi_dir:
            value = repo_data.get(key, value)
        if scope in ("env", "all"):
            env_value = os.environ.get(f"VESI_{key.upper().replace('.', '_')}")
            if env_value is not None:
                value = env_value

        return self.schema.coerce(key, value)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        return bool(self.get(key, default))

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        return int(self.get(key, default))

    def get_all(self, *, scope: str = "all") -> dict[str, Any]:
        """Return every configured key as a flat mapping.

        Includes schema defaults plus any stored custom keys.
        """
        result: dict[str, Any] = {}
        for key, default in self.schema.defaults():
            result[key] = self.get(key, default, scope=scope)
        # Merge in custom keys that aren't part of the schema
        repo_data = self.load_repo() if self.repo_vesi_dir else {}
        global_data = self.load_global()
        if scope in ("repo", "all") and self.repo_vesi_dir:
            for key, value in repo_data.items():
                if key not in result:
                    result[key] = value
        if scope in ("global", "all") and global_data:
            for key, value in global_data.items():
                if key not in result:
                    result[key] = value
        return result

    def set(self, key: str, value: Any, *, scope: str = "repo") -> None:
        """Set a configuration value, validating against the schema.

        scopes: 'repo' or 'global'.
        """
        self.schema.validate(key, value)
        if scope == "global":
            data = self.load_global()
            data[key] = value
            self.save_global(data)
        else:
            data = self.load_repo()
            data[key] = value
            self.save_repo(data)

    def unset(self, key: str, *, scope: str = "repo") -> bool:
        """Remove a key. Returns True if it existed and was removed."""
        if scope == "global":
            data = self.load_global()
        else:
            data = self.load_repo()
        if key not in data:
            return False
        del data[key]
        if scope == "global":
            self.save_global(data)
        else:
            self.save_repo(data)
        return True

    def template(self) -> dict[str, Any]:
        """Return a fresh template of all schema defaults."""
        return dict(self.schema.defaults())


def _read_json(path: Path) -> dict[str, Any]:
    """Safely read a JSON file, returning {} on any failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with atomics (temp file + rename)."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


__all__ = ["ConfigManager"]