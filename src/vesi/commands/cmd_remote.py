"""Command: remote - Manage remote repositories."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.remote.transport import RemoteConfig
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_remote(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Manage remote repositories.

    Usage:
      remote                          - List all remotes
      remote tambah <name> <url>      - Add a remote
      remote hapus <name>             - Remove a remote
      remote ganti <name> <url>       - Change remote URL
      remote lihat <name>             - Show remote details
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    remote_config = RemoteConfig(repo.root)
    args = parsed.args or []
    sub = parsed.subcommand or ""

    if not sub and not args:
        # List all remotes
        return _list_remotes(remote_config)

    # If no subcommand but has args, treat first arg as subcommand
    if not sub and args:
        sub = args[0].lower()
        args = args[1:]

    if sub in ("tambah", "add"):
        return _add_remote(remote_config, args, verbose)
    elif sub in ("hapus", "remove", "rm"):
        return _remove_remote(remote_config, args)
    elif sub in ("ganti", "set-url", "update"):
        return _set_url(remote_config, args)
    elif sub in ("lihat", "show", "info"):
        return _show_remote(remote_config, args, verbose)
    elif sub in ("rename",):
        return _rename_remote(remote_config, args)
    else:
        # If subcommand is actually a remote name, try to show it
        if sub and not sub.startswith("-"):
            return _show_remote(remote_config, [sub], verbose)
        raise VesiError(
            f"Perintah remote '{sub}' tidak dikenal.",
            hint="Perintah yang tersedia:\n  tambah, hapus, ganti, lihat, rename",
        )


def _list_remotes(remote_config: RemoteConfig) -> int:
    """List all remotes."""
    remotes = remote_config.list_remotes()

    if not remotes:
        print("Tidak ada remote yang dikonfigurasi.")
        print("\nTambahkan remote:")
        print("  remote tambah origin https://github.com/user/repo.git")
        return 0

    print(f"Remote ({len(remotes)}):\n")
    for name, url in remotes.items():
        print(f"  {name:<15} {url}")

    return 0


def _add_remote(
    remote_config: RemoteConfig,
    args: list[str],
    verbose: bool,
) -> int:
    """Add a remote."""
    if len(args) < 2:
        raise VesiError(
            "Tentukan nama dan URL remote.",
            hint="Contoh:\n  remote tambah origin https://github.com/user/repo.git",
        )

    name = args[0]
    url = args[1]

    # Check if remote already exists
    existing = remote_config.get_remote_url(name)
    if existing:
        raise VesiError(
            f"Remote '{name}' sudah ada.",
            hint="Gunakan 'remote ganti' untuk mengubah URL.",
        )

    # Add remote
    remote_config.add_remote(name, url)

    print_color(f"✓ Remote '{name}' ditambahkan!", "green")
    print(f"  URL: {url}")

    if verbose:
        print(f"\n  Push ke remote:")
        print(f"    vesi kirim {name}")
        print(f"\n  Pull dari remote:")
        print(f"    vesi ambil remote {name}")

    return 0


def _remove_remote(
    remote_config: RemoteConfig,
    args: list[str],
) -> int:
    """Remove a remote."""
    if not args:
        raise VesiError(
            "Tentukan nama remote yang akan dihapus.",
            hint="Contoh:\n  remote hapus origin",
        )

    name = args[0]

    # Check if remote exists
    url = remote_config.get_remote_url(name)
    if not url:
        raise VesiError(f"Remote '{name}' tidak ditemukan.")

    # Remove remote
    remote_config.remove_remote(name)

    print_color(f"✓ Remote '{name}' dihapus.", "green")
    print(f"  URL sebelumnya: {url}")

    return 0


def _set_url(
    remote_config: RemoteConfig,
    args: list[str],
) -> int:
    """Set remote URL."""
    if len(args) < 2:
        raise VesiError(
            "Tentukan nama remote dan URL baru.",
            hint="Contoh:\n  remote ganti origin https://new-url.com/repo.git",
        )

    name = args[0]
    new_url = args[1]

    # Check if remote exists
    old_url = remote_config.get_remote_url(name)
    if not old_url:
        raise VesiError(f"Remote '{name}' tidak ditemukan.")

    # Update URL
    remote_config.set_remote_url(name, new_url)

    print_color(f"✓ URL remote '{name}' diubah!", "green")
    print(f"  Sebelumnya: {old_url}")
    print(f"  Sekarang:   {new_url}")

    return 0


def _show_remote(
    remote_config: RemoteConfig,
    args: list[str],
    verbose: bool,
) -> int:
    """Show remote details."""
    if not args:
        raise VesiError(
            "Tentukan nama remote.",
            hint="Contoh:\n  remote lihat origin",
        )

    name = args[0]
    url = remote_config.get_remote_url(name)

    if not url:
        raise VesiError(f"Remote '{name}' tidak ditemukan.")

    print_color(f"Remote: {name}", "cyan")
    print(f"  URL: {url}")

    # Parse URL info
    from urllib.parse import urlparse
    parsed = urlparse(url)
    print(f"  Protocol: {parsed.scheme}")
    print(f"  Host: {parsed.hostname}")

    if verbose:
        print(f"\n  Commands:")
        print(f"    vesi kirim {name}          Push ke remote")
        print(f"    vesi ambil remote {name}   Pull dari remote")
        print(f"    vesi unduh {name}          Fetch dari remote")

    return 0


def _rename_remote(
    remote_config: RemoteConfig,
    args: list[str],
) -> int:
    """Rename a remote."""
    if len(args) < 2:
        raise VesiError(
            "Tentukan nama lama dan baru.",
            hint="Contoh:\n  remote rename origin upstream",
        )

    old_name = args[0]
    new_name = args[1]

    # Check if old remote exists
    url = remote_config.get_remote_url(old_name)
    if not url:
        raise VesiError(f"Remote '{old_name}' tidak ditemukan.")

    # Check if new name already exists
    if remote_config.get_remote_url(new_name):
        raise VesiError(f"Remote '{new_name}' sudah ada.")

    # Rename (add new, remove old)
    remote_config.add_remote(new_name, url)
    remote_config.remove_remote(old_name)

    print_color(f"✓ Remote '{old_name}' di-rename ke '{new_name}'!", "green")
    print(f"  URL: {url}")

    return 0
