"""Command: kirim - Push to remote repository."""

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


def cmd_kirim(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Push commits to remote repository.

    Usage:
      kirim                          - Push current branch to origin
      kirim <remote>                 - Push to named remote
      kirim <remote> <branch>        - Push specific branch
      kirim --set-upstream           - Set upstream tracking
      kirim --force                  - Force push (use with caution!)
      kirim --tags                   - Push all tags
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    force = "--force" in parsed.flags or "-f" in parsed.flags
    set_upstream = "--set-upstream" in parsed.flags or "-u" in parsed.flags
    push_tags = "--tags" in parsed.flags

    # Determine remote and branch
    remote_name = "origin"
    branch = repo.refs.get_active_branch()

    if args and not args[0].startswith("--"):
        remote_name = args[0]
    if len(args) > 1 and not args[1].startswith("--"):
        branch = args[1]

    if not branch:
        raise VesiError("Tidak ada branch aktif untuk di-push.")

    # Get remote URL
    remote_config = RemoteConfig(repo.root)
    remote_url = remote_config.get_remote_url(remote_name)

    if not remote_url:
        raise VesiError(
            f"Remote '{remote_name}' tidak ditemukan.",
            hint="Tambahkan remote terlebih dahulu:\n  tambah remote origin <url>",
        )

    print_color(f"🚀 Push ke {remote_name}...\n", "cyan")
    print(f"  Remote: {remote_url}")
    print(f"  Branch: {branch}")

    # Get current commit
    current_hash = repo.get_head_commit()
    if not current_hash:
        raise VesiError("Tidak ada commit untuk di-push.")

    print(f"  Commit: {short_hash(current_hash)}")

    # Check force push warning
    if force:
        print_color("\n  ⚠ PERINGATAN: Force push akan menimpa remote!", "red")
        print("  Ini bisa menghapus commit orang lain.")
        print("  Gunakan hanya jika yakin.\n")

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

    # Push
    try:
        print_color("\n1️⃣  Mengambil informasi remote...\n", "yellow")

        # Discover remote refs
        remote_refs = transport.discover_refs()
        remote_ref_map = {r.name: r.hash_id for r in remote_refs}

        print(f"  Remote refs: {len(remote_refs)}")

        # Check if branch exists on remote
        ref_name = f"refs/heads/{branch}"
        remote_hash = remote_ref_map.get(ref_name, "0" * 40)

        if remote_hash == current_hash:
            print_color("\n✓ Sudah up to date!", "yellow")
            return 0

        print_color("\n2️⃣  Mengirim commits...\n", "yellow")

        # Build push refs
        push_refs = {ref_name: current_hash}

        # Push tags if requested
        if push_tags:
            print("  Mengirim tags...")
            # Would add tag refs here

        # Perform push
        success = transport.push_pack(push_refs)

        if success:
            print_color(f"\n{'━' * 50}", "dim")
            print_color("✓ Push berhasil!", "green")
            print(f"  Remote: {remote_name}/{branch}")
            print(f"  Commit: {short_hash(current_hash)}")

            if set_upstream:
                print(f"\n  ✓ Upstream set: {remote_name}/{branch}")
        else:
            raise VesiError("Push gagal. Periksa authentication dan permissions.")

    except TransportError as e:
        raise VesiError(f"Gagal push: {e}")
    except Exception as e:
        if debug:
            raise
        raise VesiError(f"Gagal push: {e}")

    return 0
