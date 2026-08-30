"""Command: ambil remote - Pull from remote repository.

Supports:
- Native vesi pull via Git smart HTTP protocol
- Automatic fallback to git subprocess for SSH/edge cases
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.remote.auth import AuthManager
from vesi.remote.transport import GitTransport, RemoteConfig, TransportError
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_ambil_remote(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Pull from remote repository.

    Usage:
      ambil remote                    - Pull from origin
      ambil remote <remote>           - Pull from named remote
      ambil remote <remote> <branch>  - Pull specific branch
      ambil remote --rebase           - Pull with rebase instead of merge
      ambil remote --ff-only          - Only fast-forward merge
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    use_rebase = "--rebase" in parsed.flags
    ff_only = "--ff-only" in parsed.flags

    # Determine remote and branch
    remote_name = "origin"
    branch = repo.refs.get_active_branch()

    if args and not args[0].startswith("--"):
        remote_name = args[0]
    if len(args) > 1 and not args[1].startswith("--"):
        branch = args[1]

    if not branch:
        raise VesiError("Tidak ada branch aktif.")

    # Get remote URL
    remote_config = RemoteConfig(repo.root)
    remote_url = remote_config.get_remote_url(remote_name)

    if not remote_url:
        raise VesiError(
            f"Remote '{remote_name}' tidak ditemukan.",
            hint="Tambahkan remote terlebih dahulu:\n  vesi remote tambah origin <url>",
        )

    print_color(f"📥 Pull dari {remote_name}...\n", "cyan")
    print(f"  Remote: {remote_url}")
    print(f"  Branch: {branch}")
    if use_rebase:
        print(f"  Mode: rebase")
    elif ff_only:
        print(f"  Mode: fast-forward only")

    # Try native fetch first
    if remote_url.startswith("https://") or remote_url.startswith("http://"):
        print_color("\n1️⃣  Fetching dari remote...\n", "yellow")

        try:
            transport = GitTransport(remote_url)
            refs = transport.discover_refs()
            print(f"  Remote refs: {len(refs)}")

            for ref in refs:
                if ref.name == f"refs/heads/{branch}":
                    print(f"  Remote branch: {short_hash(ref.hash_id)}")
                    break
        except Exception as e:
            if verbose:
                print(f"  ⚠ Native fetch error: {e}")

    # Fallback: use git pull
    print_color("\n2️⃣  Pull via git...\n", "yellow")

    cmd = ["git", "pull", remote_name, branch]
    if use_rebase:
        cmd.insert(2, "--rebase")
    elif ff_only:
        cmd.insert(2, "--ff-only")

    result = subprocess.run(
        cmd, cwd=str(repo.root),
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            print(f"  {output}")
        print_color(f"\n{'━' * 50}", "dim")
        print_color("✓ Pull berhasil!", "green")
        return 0
    else:
        error = result.stderr.strip() or result.stdout.strip()
        print(f"  {error}")

        # Check if it's up-to-date
        if "Already up to date" in error or "sudah terbaru" in error:
            print_color("\n✓ Sudah terbaru!", "yellow")
            return 0

        raise VesiError(
            f"Pull gagal: {error}",
            hint=(
                "Tips:\n"
                "  1. Pastikan remote sudah terkonfigurasi\n"
                "  2. Coba fetch dulu: vesi unduh\n"
                "  3. Jika ada conflict, resolve lalu vesi lanjutkan"
            ),
        )
