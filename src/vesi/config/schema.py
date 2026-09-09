"""Configuration schema - available keys, defaults, and validation."""

from __future__ import annotations

from typing import Any, Callable


# Each entry: name -> (default, type, description)
# type is one of: "string", "bool", "int", "str_list"
CONFIG_SCHEMA: dict[str, tuple[Any, str, str]] = {
    # User identity
    "user.name": ("", "string", "Nama penulis untuk metadata versi"),
    "user.email": ("", "string", "Email penulis untuk metadata versi"),
    # Core behavior
    "core.language": ("id", "string", "Bahasa antarmuka (id/en)"),
    "core.verbose": (False, "bool", "Output verbose secara default"),
    "core.editor": ("", "string", "Editor teks untuk pesan commit (contoh: nano, vim)"),
    "core.default_branch": ("utama", "string", "Nama cabang awal saat mulai proyek"),
    "core.autosave": (False, "bool", "Aktifkan autosave otomatis"),
    "core.autosave_interval": (300, "int", "Interval autosave dalam detik"),
    # Diff / display
    "diff.context_lines": (3, "int", "Jumlah baris konteks pada diff"),
    "diff.ignore_whitespace": (False, "bool", "Abaikan perubahan spasi pada diff"),
    # Merge / conflict
    "merge.keep_backup": (True, "bool", "Simpan salinan file sebelum merge"),
    "merge.driver_enabled": (False, "bool", "Aktifkan custom merge driver"),
    # Remote / git bridge
    "bridge.auto_import": (False, "bool", "Impor otomatis metadata git ke vesi"),
    # Safety
    "safety.require_confirmation": (True, "bool", "Minta konfirmasi sebelum operasi berbahaya"),
    "safety.auto_backup": (True, "bool", "Buat backup sebelum operasi destruktif"),
    # Editor / UX
    "ui.color": (True, "bool", "Aktifkan warna pada output"),
    "ui.show_hints": (True, "bool", "Tampilkan tips dan hint"),
    "ui.diff_viewer": ("side", "string", "Mode diff: side, unified, atau word"),
}


class ConfigSchema:
    """Validates and coerces config values against the declared schema."""

    def __init__(self, schema: dict[str, tuple[Any, str, str]]) -> None:
        self.schema = schema

    def get_default(self, key: str, fallback: Any = None) -> Any:
        entry = self.schema.get(key)
        if entry is None:
            return fallback
        return entry[0]

    def get_type(self, key: str) -> str:
        entry = self.schema.get(key)
        if entry is None:
            return "string"
        return entry[1]

    def describe(self, key: str) -> str:
        """Return human-readable description for a key."""
        entry = self.schema.get(key)
        if entry is None:
            return ""
        return entry[2]

    def defaults(self) -> list[tuple[str, Any]]:
        """Return all (key, default) pairs."""
        return [(key, val[0]) for key, val in self.schema.items()]

    def keys(self) -> list[str]:
        return list(self.schema.keys())

    def validate(self, key: str, value: Any) -> None:
        """Validate a value against the schema; raise ValueError if invalid."""
        type_name = self.get_type(key)
        if type_name == "bool":
            value = _as_bool(value)
            if value is None:
                raise ValueError(f"'{key}' harus berupa boolean (true/false).")
        elif type_name == "int":
            if not isinstance(value, int) and not _is_int_str(value):
                raise ValueError(f"'{key}' harus berupa angka bulat.")
            if isinstance(value, int) and value < 0:
                raise ValueError(f"'{key}' tidak boleh negatif.")
        elif type_name == "string":
            if not isinstance(value, str):
                raise ValueError(f"'{key}' harus berupa teks.")
        elif type_name == "str_list":
            if not isinstance(value, list):
                raise ValueError(f"'{key}' harus berupa daftar teks.")

    def coerce(self, key: str, value: Any) -> Any:
        """Convert a raw string value into the schema's typed value."""
        type_name = self.get_type(key)
        if type_name == "bool":
            return _as_bool(value) or False
        elif type_name == "int":
            try:
                return int(value)
            except (TypeError, ValueError):
                return value
        return value


def _as_bool(value: Any) -> bool | None:
    """Convert common string representations to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "ya", "on", "aktif"):
            return True
        if lowered in ("false", "0", "no", "tidak", "off", "nonaktif"):
            return False
        return None
    if isinstance(value, int):
        return bool(value)
    return None


def _is_int_str(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


__all__ = ["CONFIG_SCHEMA", "ConfigSchema"]