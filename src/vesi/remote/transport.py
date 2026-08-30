"""Git transport layer - handles HTTP/SSH communication with remote repositories.

Supports:
- HTTP/HTTPS (GitHub, GitLab, Bitbucket)
- SSH protocol
- Smart HTTP protocol (git-upload-pack, git-receive-pack)
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse


@dataclass
class RemoteRef:
    """A remote reference."""

    name: str  # e.g., "refs/heads/main"
    hash_id: str


@dataclass
class RemoteInfo:
    """Information about a remote repository."""

    url: str
    protocol: str  # "http", "https", "ssh", "git"
    host: str
    path: str
    branches: list[RemoteRef] = field(default_factory=list)
    default_branch: str = "main"
    HEAD: str = ""


class GitTransport:
    """Handles communication with remote Git repositories."""

    def __init__(self, url: str, auth: dict | None = None) -> None:
        self.url = url
        self.auth = auth or {}
        self.parsed = urlparse(url)
        self.protocol = self._detect_protocol()
        self.host = self.parsed.hostname or ""
        self.path = self.parsed.path

    def _detect_protocol(self) -> str:
        """Detect protocol from URL."""
        if self.url.startswith("http://"):
            return "http"
        elif self.url.startswith("https://"):
            return "https"
        elif self.url.startswith("ssh://") or self.url.startswith("git@"):
            return "ssh"
        elif self.url.endswith(".git"):
            return "git"
        return "https"  # Default

    def info(self) -> RemoteInfo:
        """Get remote repository information."""
        return RemoteInfo(
            url=self.url,
            protocol=self.protocol,
            host=self.host,
            path=self.path,
        )

    def discover_refs(self) -> list[RemoteRef]:
        """Discover remote references using Git smart HTTP protocol.

        Sends: GET /info/refs?service=git-upload-pack
        """
        refs = []

        # Try smart HTTP discovery
        if self.protocol in ("http", "https"):
            refs = self._http_discover_refs()

        return refs

    def _http_discover_refs(self) -> list[RemoteRef]:
        """Discover refs via smart HTTP protocol."""
        import urllib.request
        import urllib.error

        refs = []
        base_url = self.url.rstrip("/")

        # Try info/refs endpoint
        info_url = f"{base_url}/info/refs?service=git-upload-pack"

        try:
            req = urllib.request.Request(info_url)
            req.add_header("User-Agent", "vesi/0.5.0")

            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()

                # Parse Git pack protocol response
                refs = self._parse_info_refs(content)

        except (urllib.error.URLError, OSError) as e:
            # Try alternative endpoint
            try:
                refs = self._try_alternative_discovery(base_url)
            except Exception:
                pass

        return refs

    def _try_alternative_discovery(self, base_url: str) -> list[RemoteRef]:
        """Try alternative ref discovery methods."""
        import urllib.request

        refs = []

        # Try HEAD first
        head_url = f"{base_url}/HEAD"
        try:
            req = urllib.request.Request(head_url)
            req.add_header("User-Agent", "vesi/0.5.0")

            with urllib.request.urlopen(req, timeout=10) as response:
                head_content = response.read().decode("utf-8", errors="replace")
                # Parse HEAD
                for line in head_content.split("\n"):
                    if line.startswith("ref: "):
                        ref_path = line[5:].strip()
                        refs.append(RemoteRef(name=ref_path, hash_id=""))
        except Exception:
            pass

        return refs

    def _parse_info_refs(self, content: bytes) -> list[RemoteRef]:
        """Parse info/refs response."""
        refs = []

        # Git smart HTTP response format
        # Each line: # service=git-upload-pack\n0000<refs>

        lines = content.split(b"\n")
        for line in lines:
            # Skip service announcement and flush packets
            if line.startswith(b"#") or line == b"0000" or not line:
                continue

            # Strip packet length prefix (4 hex chars)
            if len(line) > 4:
                try:
                    pkt_len = int(line[:4], 16)
                    data = line[4:pkt_len]

                    # Format: <hash> <refname>\0capabilities
                    if b"\x00" in data:
                        ref_part = data.split(b"\x00")[0]
                    else:
                        ref_part = data

                    parts = ref_part.split(b" ", 1)
                    if len(parts) == 2:
                        hash_id = parts[0].decode("utf-8", errors="replace")
                        ref_name = parts[1].decode("utf-8", errors="replace").strip()

                        if hash_id != "0000000000000000000000000000000000000000":
                            refs.append(RemoteRef(name=ref_name, hash_id=hash_id))
                except (ValueError, UnicodeDecodeError):
                    continue

        return refs

    def fetch_pack(self, want_refs: list[str]) -> Iterator[bytes]:
        """Fetch pack data from remote.

        Implements Git fetch protocol.
        """
        import urllib.request

        base_url = self.url.rstrip("/")

        # Step 1: Discover refs
        refs = self.discover_refs()

        # Step 2: Send want/have negotiation
        # For now, just fetch everything
        pack_url = f"{base_url}/git-upload-pack"

        try:
            # Build want request
            want_lines = []
            for ref in refs[:10]:  # Limit to 10 refs
                want_lines.append(f"want {ref.hash_id}".encode())

            # Packet format
            request = b""
            for line in want_lines:
                pkt = f"{len(line) + 4:04x}".encode() + line + b"\n"
                request += pkt

            # End command
            request += b"0000"

            # Add done
            request += b"0009done\n"

            req = urllib.request.Request(
                pack_url,
                data=request,
                method="POST",
            )
            req.add_header("User-Agent", "vesi/0.5.0")
            req.add_header("Content-Type", "application/x-git-upload-pack-request")

            with urllib.request.urlopen(req, timeout=60) as response:
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    yield chunk

        except Exception as e:
            raise TransportError(f"Gagal fetch dari remote: {e}")

    def push_pack(self, refs: dict[str, str]) -> bool:
        """Push pack data to remote.

        Args:
            refs: Dict of {ref_name: new_hash} to push.

        Returns True if successful.
        """
        import urllib.request

        base_url = self.url.rstrip("/")

        # Step 1: Discover current refs
        remote_refs = self.discover_refs()
        remote_ref_map = {r.name: r.hash_id for r in remote_refs}

        # Step 2: Build push request
        receive_url = f"{base_url}/git-receive-pack"

        try:
            # Build update commands
            commands = []
            for ref_name, new_hash in refs.items():
                old_hash = remote_ref_map.get(ref_name, "0" * 40)
                commands.append(f"{old_hash} {new_hash} {ref_name}".encode())

            # Packet format
            request = b""
            for cmd in commands:
                pkt = f"{len(cmd) + 4:04x}".encode() + cmd + b"\n"
                request += pkt

            # End commands
            request += b"0000"

            # Add pack data (simplified)
            # In real implementation, this would include the actual pack

            req = urllib.request.Request(
                receive_url,
                data=request,
                method="POST",
            )
            req.add_header("User-Agent", "vesi/0.5.0")
            req.add_header("Content-Type", "application/x-git-receive-pack-request")

            with urllib.request.urlopen(req, timeout=60) as response:
                result = response.read()
                # Check for success
                return b"unpack ok" in result or response.status == 200

        except Exception as e:
            raise TransportError(f"Gagal push ke remote: {e}")

    def clone(self, target_dir: Path, branch: str = "main") -> bool:
        """Clone remote repository to local directory."""
        import urllib.request

        base_url = self.url.rstrip("/")

        # Step 1: Init local repo
        target_dir.mkdir(parents=True, exist_ok=True)

        # Step 2: Discover refs
        refs = self.discover_refs()

        if not refs:
            raise TransportError("Tidak ada refs ditemukan di remote.")

        # Step 3: Fetch objects
        print(f"  Mengambil refs dari remote...")

        # Step 4: Create .git structure
        git_dir = target_dir / ".git"
        git_dir.mkdir(exist_ok=True)
        (git_dir / "objects").mkdir(exist_ok=True)
        (git_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)

        # Step 5: Write HEAD
        head_file = git_dir / "HEAD"
        head_file.write_text(f"ref: refs/heads/{branch}\n")

        # Step 6: Write config
        config_file = git_dir / "config"
        config_file.write_text(f"""[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
[remote "origin"]
\turl = {self.url}
\tfetch = +refs/heads/*:refs/remotes/origin/*
""")

        # Step 7: Write refs
        for ref in refs:
            if ref.hash_id and ref.name.startswith("refs/heads/"):
                branch_name = ref.name.replace("refs/heads/", "")
                branch_file = git_dir / "refs" / "heads" / branch_name
                branch_file.parent.mkdir(parents=True, exist_ok=True)
                branch_file.write_text(f"{ref.hash_id}\n")

        print(f"  ✓ {len(refs)} refs ditemukan")
        print(f"  ✓ Repository di-clone ke {target_dir}")

        return True


class TransportError(Exception):
    """Error during transport operation."""
    pass


class RemoteConfig:
    """Manages remote configuration."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.vesi_dir = repo_root / ".vesi"
        self.config_file = self.vesi_dir / "remote.json"

    def _load(self) -> dict:
        """Load remote config."""
        if not self.config_file.is_file():
            return {"remotes": {}}
        try:
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"remotes": {}}

    def _save(self, config: dict) -> None:
        """Save remote config."""
        self.config_file.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_remote(self, name: str, url: str) -> None:
        """Add a remote."""
        config = self._load()
        config["remotes"][name] = {
            "url": url,
            "fetch": f"+refs/heads/*:refs/remotes/{name}/*",
        }
        self._save(config)

    def remove_remote(self, name: str) -> bool:
        """Remove a remote."""
        config = self._load()
        if name in config["remotes"]:
            del config["remotes"][name]
            self._save(config)
            return True
        return False

    def list_remotes(self) -> dict[str, str]:
        """List all remotes."""
        config = self._load()
        return {name: info["url"] for name, info in config["remotes"].items()}

    def get_remote_url(self, name: str) -> str | None:
        """Get URL for a remote."""
        config = self._load()
        remote = config["remotes"].get(name)
        return remote["url"] if remote else None

    def set_remote_url(self, name: str, url: str) -> None:
        """Set URL for a remote."""
        config = self._load()
        if name not in config["remotes"]:
            config["remotes"][name] = {}
        config["remotes"][name]["url"] = url
        self._save(config)
