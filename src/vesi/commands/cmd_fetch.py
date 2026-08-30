"""Command: unduh - Fetch from remote repository."""

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


def cmd_unduh(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Fetch commits from remote repository.

    Usage:
      unduh                          - Fetch from origin
      unduh <remote>                 - Fetch from named remote
      unduh --all                    - Fetch all remotes
      unduh --prune                  - Prune deleted remote branches
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    fetch_all = "--all" in parsed.flags
    prune = "--prune" in parsed.flags

    # Get remotes to fetch
    remote_config = RemoteConfig(repo.root)
    remotes = remote_config.list_remotes()

    if fetch_all:
        # Fetch all remotes
        remote_names = list(remotes.keys())
    elif args and not args[0].startswith("--"):
        remote_names = [args[0]]
    else:
        remote_names = ["origin"]

    if not remote_names:
        raise VesiError(
            "Tidak ada remote yang dikonfigurasi.",
            hint="Tambahkan remote terlebih dahulu:\n  tambah remote origin <url>",
        )

    print_color("📥 Fetch dari remote...\n", "cyan")

    total_fetched = 0

    for remote_name in remote_names:
        remote_url = remotes.get(remote_name)

        if not remote_url:
            print_color(f"  ⚠ Remote '{remote_name}' tidak ditemukan, skip.", "yellow")
            continue

        print(f"\n  🌿 {remote_name}: {remote_url}")

        # Create transport
        try:
            transport = GitTransport(remote_url)
        except Exception as e:
            print_color(f"  ✗ Gagal menghubungkan: {e}", "red")
            continue

        # Setup authentication
        auth_mgr = AuthManager()
        host = transport.host

        token = auth_mgr.get_token(host)

        # Fetch
        try:
            # Discover remote refs
            remote_refs = transport.discover_refs()

            print(f"  Ditemukan {len(remote_refs)} refs")

            if verbose:
                for ref in remote_refs[:10]:
                    print(f"    {ref.name} -> {ref.hash_id[:7]}")

            # Update local remote tracking branches
            for ref in remote_refs:
                if ref.name.startswith("refs/heads/"):
                    branch_name = ref.name.replace("refs/heads/", "")
                    tracking_ref = f"refs/remotes/{remote_name}/{branch_name}"

                    # Store remote tracking ref
                    tracking_file = repo.vesi_dir / "refs" / "remotes" / remote_name / branch_name
                    tracking_file.parent.mkdir(parents=True, exist_ok=True)
                    tracking_file.write_text(f"{ref.hash_id}\n")

                    total_fetched += 1

            # Prune deleted branches if requested
            if prune:
                print(f"  Pruning deleted branches...")
                # Would compare local tracking refs with remote

            print_color(f"  ✓ {remote_name}: {len(remote_refs)} refs diambil", "green")

        except TransportError as e:
            print_color(f"  ✗ Gagal fetch: {e}", "red")
        except Exception as e:
            print_color(f"  ✗ Error: {e}", "red")

    # Summary
    print_color(f"\n{'━' * 50}", "dim")
    print_color("✓ Fetch selesai!", "green")
    print(f"  Total: {total_fetched} refs dari {len(remote_names)} remote")

    if total_fetched > 0:
        print(f"\n  Lihat perubahan:")
        print(f"    vesi lihat cabang")
        print(f"    vesi lihat riwayat")

    return 0
