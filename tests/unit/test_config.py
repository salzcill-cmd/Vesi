"""Unit tests for the configuration system."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from vesi.config.manager import ConfigManager
from vesi.config.schema import CONFIG_SCHEMA, ConfigSchema


@pytest.fixture
def config_dir(tmp_path):
    """Temporary directory to act as repo .vesi dir."""
    return tmp_path / ".vesi"


@pytest.fixture
def manager(config_dir):
    return ConfigManager(config_dir)


class TestConfigSchema:
    """Test schema validation and coercion."""

    def test_known_keys_have_defaults(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        assert schema.get_default("user.name") == ""
        assert schema.get_default("core.autosave") is False
        assert schema.get_default("diff.context_lines") == 3
        assert schema.get_default("unknown.key", "fallback") == "fallback"

    def test_unknown_type_is_string(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        assert schema.get_type("nonexistent.key") == "string"

    def test_bool_coercion(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        assert schema.coerce("core.autosave", "true") is True
        assert schema.coerce("core.autosave", "1") is True
        assert schema.coerce("core.autosave", "ya") is True
        assert schema.coerce("core.autosave", "false") is False
        assert schema.coerce("core.autosave", "0") is False
        assert schema.coerce("core.autosave", "tidak") is False

    def test_int_coercion(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        assert schema.coerce("diff.context_lines", "5") == 5
        assert schema.coerce("diff.context_lines", 7) == 7

    def test_bool_validation_requires_bool(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        with pytest.raises(ValueError):
            schema.validate("core.autosave", "bukan-bool")

    def test_int_validation_rejects_negative(self):
        schema = ConfigSchema(CONFIG_SCHEMA)
        with pytest.raises(ValueError):
            schema.validate("diff.context_lines", -1)


class TestConfigManager:
    """Test config persistence and layering."""

    def test_defaults_used_when_nothing_stored(self, manager, config_dir):
        assert manager.get("user.name") == ""
        assert manager.get("core.verbose") is False
        assert manager.get("nonexistent", "fallback") == "fallback"

    def test_repo_set_and_get(self, manager):
        manager.set("user.name", "Budi")
        assert manager.get("user.name") == "Budi"

    def test_repo_set_typed_value(self, manager):
        manager.set("core.autosave", "true")
        assert manager.get("core.autosave") is True

    def test_repo_persists_across_instances(self, manager, config_dir):
        manager.set("user.email", "budi@contoh.com")
        fresh = ConfigManager(config_dir)
        assert fresh.get("user.email") == "budi@contoh.com"

    def test_unset_removes_key(self, manager):
        manager.set("user.name", "Budi")
        assert manager.unset("user.name") is True
        assert manager.get("user.name") == ""
        assert manager.unset("user.name") is False

    def test_global_scope(self, manager, monkeypatch, tmp_path):
        # Point global config at a temp dir
        fake_home = tmp_path / "home"
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        other = ConfigManager(None)
        other.set("user.name", "Global User", scope="global")
        assert manager.get("user.name", scope="global") == "Global User"
        assert manager.get("user.name", scope="repo") == ""

    def test_repo_overrides_global(self, manager, monkeypatch, tmp_path, config_dir):
        fake_home = tmp_path / "home2"
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        global_mgr = ConfigManager(None)
        global_mgr.set("user.name", "Global", scope="global")

        manager.set("user.name", "Repo")
        assert manager.get("user.name", scope="all") == "Repo"

    def test_env_override(self, manager, monkeypatch):
        monkeypatch.setenv("VESI_CORE_AUTOSAVE", "true")
        assert manager.get("core.autosave", scope="env") is True

    def test_invalid_key_raises(self, manager):
        with pytest.raises(ValueError):
            manager.set("core.autosave", "bukan-bool")


class TestLegacyMigration:
    """Test loading the old nested config format."""

    def test_load_legacy_nested_config(self, manager, config_dir):
        legacy = {"user": {"name": "Ani", "email": "ani@x.id"}, "core": {"language": "en"}}
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config").write_text(json.dumps(legacy), encoding="utf-8")

        # get_repo_config_path should fall back to the legacy file
        assert manager.get_repo_config_path() == (config_dir / "config")
        # load_repo migrates nested structure into flat keys
        flat = manager.load_repo()
        assert flat.get("user.name") == "Ani"
        assert flat.get("user.email") == "ani@x.id"

    def test_save_always_uses_config_json(self, manager, config_dir):
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config").write_text("{}", encoding="utf-8")
        manager.set("user.name", "Ani")
        assert (config_dir / "config.json").is_file()


class TestAtomicWrite:
    """Config writes survive partial failures."""

    def test_no_tmp_files_left_after_save(self, manager, config_dir):
        manager.set("user.name", "Budi")
        leftovers = list(config_dir.glob(".tmp_*"))
        assert leftovers == []