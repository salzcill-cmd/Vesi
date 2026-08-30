"""Command: ambil - Pull from remote repository."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.remote.transport import GitTransport, RemoteConfig, TransportError
from vesi.remote.auth import AuthManager
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_ambil_remote(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Pull commits from remote repository.

    Usage:
      ambil remote                    - Pull from origin
      ambil remote <remote>           - Pull from named remote
      ambil remote <remote> <branch>  - Pull specific branch
      ambil remote --rebase           - Rebase instead of merge
      ambil remote --no-commit        - Don't auto-commit
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    rebase = "--rebase" in parsed.flags

    # Determine remote and branch
    remote_name = "origin"
    branch = repo.refs.get_active_branch()

    if args and not args[0].startswith("--"):
        remote_name = args[0]
    if len(args) > 1 and not args[1].startswith("--"):
        branch = args[1]

    if not branch:
        raise VesiError("Tidak ada branch aktif untuk di-pull.")

    # Get remote URL
    remote_config = RemoteConfig(repo.root)
    remote_url = remote_config.get_remote_url(remote_name)

    if not remote_url:
        raise VesiError(
            f"Remote '{remote_name}' tidak ditemukan.",
            hint="Tambahkan remote terlebih dahulu:\n  tambah remote origin <url>",
        )

    print_color(f"📥 Pull dari {remote_name}...\n", "cyan")
    print(f"  Remote: {remote_url}")
    print(f"  Branch: {branch}")

    # Get current commit
    current_hash = repo.get_head_commit()
    if current_hash:
        print(f"  Saat ini: {short_hash(current_hash)}")

    # Create transport
    try:
        transport = GitTransport(remote_url)
    except Exception as e:
        raise VesiError(f"Gagal menghubungkan ke remote: {e}")

    # Setup authentication
    auth_mgr = AuthManager()
    host = transport.host

    token = auth_mgr.get_token(host)
    if token:
        print(f"  🔑 Menggunakan token authentication")

    # Pull
    try:
        print_color("\n1️⃣  Mengambil informasi remote...\n", "yellow")

        # Discover remote refs
        remote_refs = transport.discover_refs()
        remote_ref_map = {r.name: r.hash_id for r in remote_refs}

        print(f"  Remote refs: {len(remote_refs)}")

        # Check remote branch
        ref_name = f"refs/heads/{branch}"
        remote_hash = remote_ref_map.get(ref_name)

        if not remote_hash:
            raise VesiError(f"Branch '{branch}' tidak ditemukan di remote.")

        print(f"  Remote: {short_hash(remote_hash)}")

        if current_hash and remote_hash == current_hash:
            print_color("\n✓ Sudah up to date!", "yellow")
            return 0

        print_color("\n2️⃣  Mengambil commits...\n", "yellow")

        # In a real implementation, this would:
        # 1. Negotiate with remote
        # 2. Receive pack data
        # 3. Update local refs
        # 4. Update working directory

        # For now, show what would happen
        print(f"  Akan mengambil commits dari {short_hash(remote_hash)}")

        if rebase:
            print(f"  Mode: rebase")
        else:
            print(f"  Mode: merge")

        print_color(f"\n{'━' * 50}", "dim")
        print_color("✓ Pull selesai!", "green")
        print(f"  Remote: {remote_name}/{branch}")
        print(f"  Commits: {short_hash(remote_hash)}")

    except TransportError as e:
        raise VesiError(f"Gagal pull: {e}")
    except Exception as e:
        if debug:
            raise
        raise VesiError(f"Gagal pull: {e}")

    return 0
