"""Git Smart HTTP Protocol v2 Client.

Implements the Git wire protocol v2 for push/pull via HTTPS.
This is the actual protocol used by GitHub/GitLab/Bitbucket.

Protocol v2 spec:
- https://github.com/git/git/blob/master/Documentation/technical/protocol-v2.txt
"""

from __future__ import annotations

import base64
import io
import struct
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any

from vesi.hashing import short_hash


# ═══════════════════════════════════════════════════════════════════
# Protocol v2 Helpers
# ═══════════════════════════════════════════════════════════════════

def pkt_line(data: bytes) -> bytes:
    """Create a Git packet-line.

    Format: 4-hex-digit length (including the 4 bytes of the length itself) + data.
    For flush packets: b'0000'
    """
    if not data:
        return b"0000"
    pkt_len = len(data) + 4
    return f"{pkt_len:04x}".encode() + data


def flush_pkt() -> bytes:
    """Create a flush packet."""
    return b"0000"


def decode_packets(data: bytes) -> list[bytes]:
    """Decode packet-line format into individual lines/data.

    Returns list of decoded payloads (without packet headers).
    """
    result = []
    pos = 0
    while pos < len(data):
        if pos + 4 > len(data):
            break
        hex_len = data[pos:pos+4]
        if hex_len == b"0000":
            pos += 4
            continue
        try:
            pkt_len = int(hex_len, 16)
        except ValueError:
            break
        if pkt_len < 4:
            break
        payload = data[pos+4:pos+pkt_len]
        result.append(payload)
        pos += pkt_len
    return result


def read_sideband(data: bytes) -> tuple[bytes, bytes, bytes]:
    """Read side-band formatted data.

    Returns (pack_data, progress_data, error_data)
    """
    pack = io.BytesIO()
    progress = io.BytesIO()
    errors = io.BytesIO()

    packets = decode_packets(data)
    for pkt in packets:
        if not pkt:
            continue
        channel = pkt[0]
        payload = pkt[1:]
        if channel == 1:
            pack.write(payload)
        elif channel == 2:
            progress.write(payload)
        elif channel == 3:
            errors.write(payload)

    return pack.getvalue(), progress.getvalue(), errors.getvalue()


# ═══════════════════════════════════════════════════════════════════
# Git Smart HTTP Client
# ═══════════════════════════════════════════════════════════════════

@dataclass
class RemoteRef:
    """A remote reference."""
    name: str
    sha1: str
    peeled: str = ""  # For annotated tags


@dataclass
class PushResult:
    """Result of a push operation."""
    success: bool
    message: str
    refs_updated: dict[str, tuple[str, str]] = field(default_factory=dict)


class GitSmartHTTPClient:
    """Full Git smart HTTP protocol v2 client.

    Supports push to GitHub/GitLab/Bitbucket via HTTPS.
    """

    def __init__(
        self,
        remote_url: str,
        auth_token: str | None = None,
    ) -> None:
        self.remote_url = remote_url.rstrip("/")
        self.auth_token = auth_token
        self._protocol_version: int | None = None
        self._capabilities: list[str] = []

    # ─── HTTP Layer ──────────────────────────────────────────────

    def _request(
        self,
        endpoint: str,
        data: bytes | None = None,
        content_type: str = "",
        method: str = "GET",
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        """Make authenticated HTTP request."""
        url = f"{self.remote_url}/{endpoint}"

        headers: dict[str, str] = {
            "User-Agent": "git/2.43.0",
        }

        if self.auth_token:
            creds = base64.b64encode(
                f"x-access-token:{self.auth_token}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"

        if content_type:
            headers["Content-Type"] = content_type

        if extra_headers:
            headers.update(extra_headers)

        req = urllib.request.Request(url, data=data, method=method)
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            body = e.read() if e.fp else b""
            return e.code, body

    # ─── Protocol v2: Ref Discovery ──────────────────────────────

    def discover_refs(self, service: str = "git-upload-pack") -> tuple[list[RemoteRef], list[str]]:
        """Discover remote references using protocol v2.

        Returns (refs, capabilities)
        """
        # Step 1: version 2 handshake
        status, body = self._request(
            f"info/refs?service={service}",
            content_type=f"application/x-{service}-advertisement",
            extra_headers={"Git-Protocol": "version=2"},
        )

        if status != 200:
            raise RuntimeError(f"Ref discovery failed (HTTP {status})")

        # Parse the v2 advertisement for capabilities
        packets = decode_packets(body)
        capabilities = []
        refs = []
        has_ls_refs = False

        for pkt in packets:
            text = pkt.decode("utf-8", errors="replace").strip()

            if text.startswith("version "):
                self._protocol_version = int(text.split()[1])
            elif text.startswith("ls-refs="):
                has_ls_refs = True
            elif text.startswith("fetch="):
                caps = text.split("=", 1)[1].split()
                capabilities.extend(caps)
            elif text.startswith("object-format="):
                fmt = text.split("=", 1)[1]
                if fmt != "sha1":
                    raise RuntimeError(f"Unsupported object format: {fmt}")

        # Step 2: If server supports ls-refs, use it to get actual refs
        if has_ls_refs:
            refs = self._ls_refs(service)
        else:
            # Fallback: parse refs from advertisement
            for pkt in packets:
                text = pkt.decode("utf-8", errors="replace").strip()
                if " " in text and len(text.split()[0]) == 40:
                    parts = text.split(" ", 1)
                    sha1 = parts[0].strip()
                    refname = parts[1].strip()
                    if "\0" in refname:
                        refname = refname.split("\0")[0]
                    if all(c in "0123456789abcdef" for c in sha1):
                        refs.append(RemoteRef(name=refname, sha1=sha1))

        self._capabilities = capabilities
        return refs, capabilities

    def _ls_refs(self, service: str = "git-upload-pack") -> list[RemoteRef]:
        """Use ls-refs command to list all refs (protocol v2)."""
        refs = []

        # Build request: command=ls-refs
        request = io.BytesIO()
        request.write(pkt_line(b"command=ls-refs"))
        request.write(flush_pkt())
        request.write(pkt_line(b"symrefs"))
        request.write(flush_pkt())

        status, body = self._request(
            service,
            data=request.getvalue(),
            content_type=f"application/x-{service}-request",
            method="POST",
            extra_headers={"Git-Protocol": "version=2"},
        )

        if status != 200:
            return refs

        packets = decode_packets(body)
        for pkt in packets:
            if not pkt:
                continue
            text = pkt.decode("utf-8", errors="replace").strip()
            if " " in text:
                parts = text.split(" ", 1)
                sha1 = parts[0].strip()
                refname = parts[1].strip()
                # Remove peeled suffix
                if "^{}" in refname:
                    refname = refname.replace("^{}", "")
                if len(sha1) == 40 and all(c in "0123456789abcdef" for c in sha1):
                    refs.append(RemoteRef(name=refname, sha1=sha1))

        return refs

    # ─── Protocol v2: Receive Pack (Push) ────────────────────────

    def push(
        self,
        pack_data: bytes,
        ref_updates: dict[str, str],
        remote_refs: list[RemoteRef],
        *,
        force: bool = False,
    ) -> PushResult:
        """Push objects to remote using protocol v2.

        Args:
            pack_data: Generated packfile bytes.
            ref_updates: {ref_name: new_sha1_hex}
            remote_refs: Current remote refs.
            force: Allow force push.

        Returns:
            PushResult
        """
        remote_map = {r.name: r.sha1 for r in remote_refs}

        # Build command batch
        commands = []
        for ref_name, new_sha in ref_updates.items():
            old_sha = remote_map.get(ref_name, "0" * 40)

            if not force and old_sha != "0" * 40:
                # Non-fast-forward check
                pass  # Let server decide

            commands.append(f"{old_sha} {new_sha} {ref_name}")

        if not commands:
            return PushResult(success=True, message="Already up to date")

        # Build the request body
        # Use protocol v1 format for push (v2 info/refs, v1 receive-pack)
        # GitHub requires raw pack data (not side-band wrapped) for push
        request = io.BytesIO()

        # Command batch (with capabilities on first line)
        first_cmd = commands[0]
        caps = "report-status delete-refs"
        request.write(pkt_line(f"{first_cmd} {caps}".encode()))
        for cmd in commands[1:]:
            request.write(pkt_line(cmd.encode()))
        request.write(flush_pkt())

        # Send raw pack data (no side-band wrapping - GitHub requires this)
        request.write(pack_data)

        # Send to git-receive-pack (v1 format - no Git-Protocol header)
        status, body = self._request(
            "git-receive-pack",
            data=request.getvalue(),
            content_type="application/x-git-receive-pack-request",
            method="POST",
        )

        if status == 200:
            # Parse response
            pack_resp, progress_resp, error_resp = read_sideband(body)

            if error_resp:
                error_msg = error_resp.decode("utf-8", errors="replace").strip()
                return PushResult(success=False, message=error_msg)

            # Check for unpack ok
            response_text = body.decode("utf-8", errors="replace")
            if "unpack ok" in response_text or "unpack ok" in pack_resp.decode("utf-8", errors="replace"):
                return PushResult(
                    success=True,
                    message="Push berhasil!",
                    refs_updated={
                        ref: (remote_map.get(ref, "0" * 40), new)
                        for ref, new in ref_updates.items()
                    },
                )

            # Check individual ref status
            ref_packets = decode_packets(pack_resp)
            for pkt in ref_packets:
                text = pkt.decode("utf-8", errors="replace").strip()
                if text.startswith("ok "):
                    return PushResult(
                        success=True,
                        message=f"Push berhasil! {text}",
                        refs_updated={
                            ref: (remote_map.get(ref, "0" * 40), new)
                            for ref, new in ref_updates.items()
                        },
                    )
                elif text.startswith("ng "):
                    return PushResult(success=False, message=text[3:])

            # If we got this far, check the raw body
            if "unpack ok" in str(body):
                return PushResult(success=True, message="Push berhasil!")

            return PushResult(
                success=False,
                message=f"Push response tidak dikenal: {response_text[:200]}",
            )
        elif status == 401:
            return PushResult(success=False, message="Autentikasi gagal (401)")
        elif status == 403:
            return PushResult(success=False, message="Akses ditolak (403)")
        elif status == 400:
            error_msg = body.decode("utf-8", errors="replace")[:200]
            return PushResult(success=False, message=f"Bad request (400): {error_msg}")
        else:
            error_msg = body.decode("utf-8", errors="replace")[:200]
            return PushResult(success=False, message=f"HTTP {status}: {error_msg}")

    # ─── High-level: Fetch Pack ──────────────────────────────────

    def fetch(self, want_refs: list[str]) -> bytes:
        """Fetch pack data from remote (simplified).

        Returns raw pack data.
        """
        # Discover refs first
        refs, _ = self.discover_refs("git-upload-pack")

        ref_map = {r.name: r.sha1 for r in refs}

        # Build fetch request
        request = io.BytesIO()

        # Command: fetch
        request.write(pkt_line(b"command=fetch"))
        request.write(flush_pkt())

        # Want lines
        for ref_name in want_refs:
            sha = ref_map.get(ref_name, "")
            if sha and len(sha) == 40:
                request.write(pkt_line(f"want {sha}".encode()))

        # Done
        request.write(pkt_line(b"done"))
        request.write(flush_pkt())

        status, body = self._request(
            "git-upload-pack",
            data=request.getvalue(),
            content_type="application/x-git-upload-pack-request",
            method="POST",
        )

        if status == 200:
            pack_data, _, errors = read_sideband(body)
            return pack_data
        else:
            raise RuntimeError(f"Fetch failed (HTTP {status})")
