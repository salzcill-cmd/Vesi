"""Plugin system - extend vesi with custom functionality.

Allows users to create and use plugins for custom commands and behaviors.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class PluginInfo:
    """Information about a plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    enabled: bool = True
    path: str = ""
    commands: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)


class PluginManager:
    """Manages vesi plugins."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root
        self.vesi_dir = repo_root / ".vesi" if repo_root else None
        self.plugins_dir = Path.home() / ".vesi" / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.plugins_dir / "plugins.json"
        self._plugins: dict[str, Any] = {}
        self._hooks: dict[str, list[Callable]] = {}

    def list_plugins(self) -> list[PluginInfo]:
        """List all installed plugins."""
        plugins = []

        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                info_file = plugin_dir / "plugin.json"
                if info_file.is_file():
                    try:
                        data = json.loads(info_file.read_text(encoding="utf-8"))
                        plugins.append(PluginInfo(
                            name=data.get("name", plugin_dir.name),
                            version=data.get("version", "0.1.0"),
                            description=data.get("description", ""),
                            author=data.get("author", ""),
                            enabled=data.get("enabled", True),
                            path=str(plugin_dir),
                            commands=data.get("commands", []),
                            hooks=data.get("hooks", []),
                        ))
                    except (json.JSONDecodeError, OSError):
                        pass

        return plugins

    def load_plugin(self, name: str) -> bool:
        """Load a plugin by name.

        Returns True if loaded successfully.
        """
        plugin_dir = self.plugins_dir / name
        if not plugin_dir.is_dir():
            return False

        # Check if already loaded
        if name in self._plugins:
            return True

        # Load plugin module
        main_file = plugin_dir / "main.py"
        if not main_file.is_file():
            return False

        try:
            # Add plugin dir to path
            sys.path.insert(0, str(plugin_dir))

            # Import module
            spec = importlib.util.spec_from_file_location(
                f"vesi_plugin_{name}",
                str(main_file),
            )
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"vesi_plugin_{name}"] = module
            spec.loader.exec_module(module)

            # Check for plugin registration
            if hasattr(module, "register"):
                plugin_instance = module.register()
                self._plugins[name] = plugin_instance

                # Register hooks
                if hasattr(module, "hooks"):
                    for hook_name, hook_func in module.hooks.items():
                        if hook_name not in self._hooks:
                            self._hooks[hook_name] = []
                        self._hooks[hook_name].append(hook_func)

                return True

            return False

        except Exception as e:
            print(f"Error loading plugin '{name}': {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        if name in self._plugins:
            plugin = self._plugins[name]
            if hasattr(plugin, "unload"):
                plugin.unload()
            del self._plugins[name]
            return True
        return False

    def install_plugin(self, path: Path) -> PluginInfo | None:
        """Install a plugin from a directory."""
        info_file = path / "plugin.json"
        if not info_file.is_file():
            return None

        try:
            data = json.loads(info_file.read_text(encoding="utf-8"))
            name = data.get("name", path.name)

            # Copy to plugins directory
            import shutil
            target = self.plugins_dir / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(path, target)

            return PluginInfo(
                name=name,
                version=data.get("version", "0.1.0"),
                description=data.get("description", ""),
                author=data.get("author", ""),
                path=str(target),
            )

        except Exception:
            return None

    def uninstall_plugin(self, name: str) -> bool:
        """Uninstall a plugin."""
        self.unload_plugin(name)

        plugin_dir = self.plugins_dir / name
        if plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin_dir)
            return True
        return False

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        plugins = self.list_plugins()
        for p in plugins:
            if p.name == name:
                info_file = Path(p.path) / "plugin.json"
                data = json.loads(info_file.read_text(encoding="utf-8"))
                data["enabled"] = True
                info_file.write_text(json.dumps(data, indent=2))
                return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        plugins = self.list_plugins()
        for p in plugins:
            if p.name == name:
                info_file = Path(p.path) / "plugin.json"
                data = json.loads(info_file.read_text(encoding="utf-8"))
                data["enabled"] = False
                info_file.write_text(json.dumps(data, indent=2))
                return True
        return False

    def run_hook(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Run all registered hooks of a type."""
        results = []

        for hook_func in self._hooks.get(hook_name, []):
            try:
                result = hook_func(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook '{hook_name}' error: {e}")

        return results

    def get_plugin(self, name: str) -> Any | None:
        """Get a loaded plugin instance."""
        return self._plugins.get(name)

    def has_plugin(self, name: str) -> bool:
        """Check if a plugin is loaded."""
        return name in self._plugins

    def get_commands(self) -> dict[str, str]:
        """Get all commands registered by plugins."""
        commands = {}

        plugins = self.list_plugins()
        for plugin in plugins:
            if plugin.enabled:
                for cmd in plugin.commands:
                    commands[cmd] = plugin.name

        return commands


def create_plugin_template(name: str) -> Path:
    """Create a plugin template directory.

    Returns path to created template.
    """
    plugin_dir = Path.home() / ".vesi" / "plugins" / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Create plugin.json
    info = {
        "name": name,
        "version": "0.1.0",
        "description": f"Plugin: {name}",
        "author": "",
        "commands": [],
        "hooks": [],
    }
    (plugin_dir / "plugin.json").write_text(
        json.dumps(info, indent=2),
        encoding="utf-8",
    )

    # Create main.py
    main_py = f'''"""Vesi plugin: {name}"""

from vesi.core.plugin import PluginInfo


class {name.title().replace("-", "")}Plugin:
    """Plugin implementation."""

    def __init__(self):
        self.name = "{name}"
        self.version = "0.1.0"

    def register(self):
        """Called when plugin is loaded."""
        print(f"Plugin {{self.name}} loaded!")
        return self

    def unload(self):
        """Called when plugin is unloaded."""
        print(f"Plugin {{self.name}} unloaded.")

    def execute(self, *args, **kwargs):
        """Main plugin logic."""
        pass


def register():
    """Register the plugin."""
    return {name.title().replace("-", "")}Plugin()


# Hook registration example
def pre_commit_hook():
    """Runs before each commit."""
    print("Custom pre-commit hook!")


hooks = {{
    "pre-commit": pre_commit_hook,
}}
'''
    (plugin_dir / "main.py").write_text(main_py, encoding="utf-8")

    return plugin_dir
