"""Authentication module for Git remote operations.

Supports:
- SSH key authentication
- Personal access tokens (GitHub, GitLab)
- Credential caching
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AuthConfig:
    """Authentication configuration."""

    method: str  # "ssh", "token", "basic"
    username: str = ""
    token: str = ""
    ssh_key_path: str = ""


class AuthManager:
    """Manages authentication for remote operations."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Path.home() / ".vesi"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.auth_file = self.config_dir / "auth.json"
        self.credentials_file = self.config_dir / "credentials"

    def get_auth(self, host: str) -> AuthConfig | None:
        """Get authentication config for a host."""
        configs = self._load_configs()
        return configs.get(host)

    def set_auth(
        self,
        host: str,
        method: str,
        username: str = "",
        token: str = "",
        ssh_key_path: str = "",
    ) -> None:
        """Set authentication config for a host."""
        configs = self._load_configs()

        configs[host] = AuthConfig(
            method=method,
            username=username,
            token=token,
            ssh_key_path=ssh_key_path,
        )

        self._save_configs(configs)

    def detect_ssh_key(self) -> str | None:
        """Auto-detect SSH key."""
        ssh_dir = Path.home() / ".ssh"

        # Check common key locations
        key_names = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]
        for name in key_names:
            key_path = ssh_dir / name
            if key_path.is_file():
                return str(key_path)

        return None

    def get_ssh_key(self, host: str = "") -> str | None:
        """Get SSH key for a host.

        Priority:
        1. Host-specific key
        2. Default key from config
        3. Auto-detected key
        """
        # Check host-specific config
        configs = self._load_configs()
        if host in configs and configs[host].ssh_key_path:
            key_path = Path(configs[host].ssh_key_path)
            if key_path.is_file():
                return str(key_path)

        # Check default
        if "default" in configs and configs["default"].ssh_key_path:
            key_path = Path(configs["default"].ssh_key_path)
            if key_path.is_file():
                return str(key_path)

        # Auto-detect
        return self.detect_ssh_key()

    def get_token(self, host: str) -> str | None:
        """Get personal access token for a host."""
        # Check config
        configs = self._load_configs()
        if host in configs and configs[host].token:
            return configs[host].token

        # Check environment variables
        env_tokens = {
            "github.com": ["GITHUB_TOKEN", "GH_TOKEN"],
            "gitlab.com": ["GITLAB_TOKEN"],
            "bitbucket.org": ["BITBUCKET_TOKEN"],
        }

        for env_var in env_tokens.get(host, []):
            token = os.environ.get(env_var)
            if token:
                return token

        return None

    def store_credential(self, host: str, username: str, password: str) -> None:
        """Store credential securely.

        Note: In production, use system keychain.
        """
        credentials = self._load_credentials()
        credentials[host] = {
            "username": username,
            "password": password,  # In production, encrypt this
        }
        self._save_credentials(credentials)

    def get_credential(self, host: str) -> tuple[str, str] | None:
        """Get stored credential."""
        credentials = self._load_credentials()
        cred = credentials.get(host)
        if cred:
            return (cred["username"], cred["password"])
        return None

    def clear_credential(self, host: str) -> bool:
        """Clear stored credential."""
        credentials = self._load_credentials()
        if host in credentials:
            del credentials[host]
            self._save_credentials(credentials)
            return True
        return False

    def _load_configs(self) -> dict[str, AuthConfig]:
        """Load auth configurations."""
        if not self.auth_file.is_file():
            return {}

        try:
            data = json.loads(self.auth_file.read_text(encoding="utf-8"))
            configs = {}
            for host, info in data.items():
                configs[host] = AuthConfig(
                    method=info.get("method", "token"),
                    username=info.get("username", ""),
                    token=info.get("token", ""),
                    ssh_key_path=info.get("ssh_key_path", ""),
                )
            return configs
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_configs(self, configs: dict[str, AuthConfig]) -> None:
        """Save auth configurations."""
        data = {}
        for host, config in configs.items():
            data[host] = {
                "method": config.method,
                "username": config.username,
                "token": config.token,
                "ssh_key_path": config.ssh_key_path,
            }

        self.auth_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def _load_credentials(self) -> dict:
        """Load credentials."""
        if not self.credentials_file.is_file():
            return {}
        try:
            return json.loads(self.credentials_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_credentials(self, credentials: dict) -> None:
        """Save credentials."""
        self.credentials_file.write_text(
            json.dumps(credentials, indent=2),
            encoding="utf-8",
        )


def setup_github_auth(token: str | None = None) -> AuthManager:
    """Setup GitHub authentication.

    Args:
        token: Personal access token. If None, will try to detect.

    Returns configured AuthManager.
    """
    manager = AuthManager()

    if token:
        manager.set_auth("github.com", method="token", token=token)
    else:
        # Try to detect from environment
        detected_token = manager.get_token("github.com")
        if detected_token:
            manager.set_auth("github.com", method="token", token=detected_token)

    return manager


def setup_gitlab_auth(token: str | None = None) -> AuthManager:
    """Setup GitLab authentication."""
    manager = AuthManager()

    if token:
        manager.set_auth("gitlab.com", method="token", token=token)
    else:
        detected_token = manager.get_token("gitlab.com")
        if detected_token:
            manager.set_auth("gitlab.com", method="token", token=detected_token)

    return manager


def setup_ssh_auth(key_path: str | None = None) -> AuthManager:
    """Setup SSH authentication."""
    manager = AuthManager()

    if key_path:
        manager.set_auth("default", method="ssh", ssh_key_path=key_path)
    else:
        detected_key = manager.detect_ssh_key()
        if detected_key:
            manager.set_auth("default", method="ssh", ssh_key_path=detected_key)

    return manager
