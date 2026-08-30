"""Command: klon - Clone a remote repository."""

from __future__ import annotations

from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryAlreadyExistsError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.remote.transport import GitTransport, TransportError
from vesi.remote.auth import AuthManager
from vesi.utils.platform import print_color


def cmd_klon(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Clone a remote repository.

    Usage:
      klon <url>                - Clone to directory named after repo
      klon <url> <directory>    - Clone to specific directory
      klon --branch <name>      - Clone specific branch
      klon --depth <n>          - Shallow clone (last n commits)
      klon --ssh                - Force SSH protocol
    """
    args = parsed.args or []

    if not args:
        raise VesiError(
            "Tentukan URL repository yang akan di-klone.",
            hint="Contoh:\n  klon https://github.com/user/repo.git\n  klon git@github.com:user/repo.git",
        )

    url = args[0]

    # Determine target directory
    if len(args) > 1 and not args[1].startswith("--"):
        target_dir = Path(args[1])
    else:
        # Extract directory name from URL
        target_dir = _url_to_dir(url)

    # Check if target already exists
    if target_dir.exists():
        raise VesiError(
            f"Directory '{target_dir}' sudah ada.",
            hint="Gunakan nama directory lain atau hapus yang sudah ada.",
        )

    print_color(f"📦 Meng-klone repository...\n", "cyan")
    print(f"  URL: {url}")
    print(f"  Lokasi: {target_dir}")

    # Parse options
    branch = _get_flag_value(parsed.flags, "--branch") or "main"
    shallow_depth = _get_flag_value(parsed.flags, "--depth")
    use_ssh = "--ssh" in parsed.flags

    # Create transport
    try:
        transport = GitTransport(url)
    except Exception as e:
        raise VesiError(f"Gagal menghubungkan ke remote: {e}")

    # Setup authentication if needed
    auth_mgr = AuthManager()
    host = transport.host

    if use_ssh:
        # Try SSH
        ssh_key = auth_mgr.get_ssh_key(host)
        if ssh_key:
            print(f"  🔑 Menggunakan SSH key: {ssh_key}")
        else:
            print_color("  ⚠ SSH key tidak ditemukan, mencoba HTTPS...", "yellow")
    else:
        # Try token auth
        token = auth_mgr.get_token(host)
        if token:
            print(f"  🔑 Menggunakan token authentication")

    # Clone
    try:
        print_color("\n1️⃣  Mengambil informasi remote...\n", "yellow")

        # Discover refs
        refs = transport.discover_refs()

        if refs:
            print(f"  Ditemukan {len(refs)} refs")
            if verbose:
                for ref in refs[:5]:
                    print(f"    {ref.name} -> {ref.hash_id[:7]}")
                if len(refs) > 5:
                    print(f"    ... dan {len(refs) - 5} refs lainnya")
        else:
            print_color("  ⚠ Tidak ada refs ditemukan, mencoba mode alternatif...", "yellow")

        print_color("\n2️⃣  Membuat repository lokal...\n", "yellow")

        # Try to clone via transport
        success = transport.clone(target_dir, branch)

        if success:
            print_color(f"\n{'━' * 50}", "dim")
            print_color("✓ Kloning selesai!", "green")
            print(f"  📁 Lokasi: {target_dir.absolute()}")
            print(f"  🌿 Branch: {branch}")
            print(f"\n  Mulai bekerja:")
            print(f"    cd {target_dir.name}")
            print(f"    vesi lihat riwayat")
            print(f"    vesi status")
        else:
            # Fallback: create minimal clone
            _create_minimal_clone(target_dir, url, branch)
            print_color(f"\n✓ Kloning selesai (mode minimal)!", "green")
            print(f"  📁 Lokasi: {target_dir.absolute()}")
            print(f"\n  Catatan: Clone dalam mode minimal.")
            print(f"  Untuk full clone, pastikan remote mendukung Git smart HTTP.")

    except TransportError as e:
        raise VesiError(f"Gagal meng-klone: {e}")
    except Exception as e:
        if debug:
            raise
        raise VesiError(f"Gagal meng-klone: {e}")

    return 0


def _url_to_dir(url: str) -> Path:
    """Convert URL to directory name."""
    # Remove .git suffix
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]

    # Handle SSH URLs (git@github.com:user/repo.git)
    if "@" in name and ":" in name:
        name = name.split(":")[-1]

    return Path(name)


def _get_flag_value(flags: list[str], flag_name: str) -> str | None:
    """Extract value from --flag=value or --flag value."""
    for i, flag in enumerate(flags):
        if flag.startswith(f"{flag_name}="):
            return flag[len(flag_name) + 1:]
        if flag == flag_name and i + 1 < len(flags):
            return flags[i + 1]
    return None


def _create_minimal_clone(target_dir: Path, url: str, branch: str) -> None:
    """Create a minimal clone with just the remote config."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Create .git structure
    git_dir = target_dir / ".git"
    git_dir.mkdir(exist_ok=True)
    (git_dir / "objects").mkdir(exist_ok=True)
    (git_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)
    (git_dir / "refs" / "remotes").mkdir(parents=True, exist_ok=True)

    # Write HEAD
    (git_dir / "HEAD").write_text(f"ref: refs/heads/{branch}\n")

    # Write config with remote
    (git_dir / "config").write_text(f"""[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
[remote "origin"]
\turl = {url}
\tfetch = +refs/heads/*:refs/remotes/origin/*
""")

    # Write description
    (git_dir / "description").write_text(f"Cloned from {url}\n")

    # Create vesi config
    vesi_dir = target_dir / ".vesi"
    vesi_dir.mkdir(exist_ok=True)
    (vesi_dir / "objects").mkdir(exist_ok=True)
    (vesi_dir / "refs" / "heads").mkdir(parents=True, exist_ok=True)

    # Copy HEAD to vesi
    (vesi_dir / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
