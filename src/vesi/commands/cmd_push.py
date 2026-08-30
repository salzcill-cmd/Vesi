"""Command: kirim - Push to remote repository.

Supports:
- Native vesi push via Git smart HTTP protocol
- Automatic fallback to git subprocess for SSH/edge cases
"""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.hashing import short_hash
from vesi.parser.parser import ParsedCommand
from vesi.remote.auth import AuthManager
from vesi.remote.git_bridge import push_vesi_to_git, push_via_git_subprocess
from vesi.remote.transport import RemoteConfig, TransportError
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
      kirim --native                 - Force native vesi push
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    force = "--force" in parsed.flags or "-f" in parsed.flags
    set_upstream = "--set-upstream" in parsed.flags or "-u" in parsed.flags
    push_tags = "--tags" in parsed.flags
    force_native = "--native" in parsed.flags

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
            hint="Tambahkan remote terlebih dahulu:\n  vesi remote tambah origin <url>",
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

    # Setup authentication
    auth_mgr = AuthManager()
    parsed_url = remote_url.replace("https://", "").replace("http://", "")
    host = parsed_url.split("/")[0]
    token = auth_mgr.get_token(host)

    if token:
        print("  🔑 Menggunakan token authentication")

    def _on_progress(msg: str, cur: int = 0, total: int = 0) -> None:
        print(f"  {msg}")

    # ═══════════════════════════════════════════════════════════════
    # Method 1: Native vesi push (smart HTTP protocol)
    # ═══════════════════════════════════════════════════════════════
    if remote_url.startswith("https://") or remote_url.startswith("http://"):
        if force_native or token:
            print_color("\n1️⃣  Native vesi push (smart HTTP protocol)...\n", "yellow")

            # Collect all commits to push
            commit_hashes = _collect_commit_chain(repo, current_hash)

            ref_name = f"refs/heads/{branch}"

            result = push_vesi_to_git(
                vesi_objects=repo.objects,
                commit_hashes=commit_hashes,
                ref_name=ref_name,
                remote_url=remote_url,
                auth_token=token,
                on_progress=_on_progress,
            )

            if result.success:
                print_color(f"\n{'━' * 50}", "dim")
                print_color("✓ Push berhasil! (native vesi)", "green")
                print(f"  Remote: {remote_name}/{branch}")
                print(f"  Commit: {short_hash(current_hash)}")
                print(f"  Objects: {len(commit_hashes)} commits dikirim")

                if set_upstream:
                    print(f"\n  ✓ Upstream set: {remote_name}/{branch}")

                return 0
            else:
                if not force_native:
                    print_color(f"\n  ⚠ Native push gagal: {result.message}", "yellow")
                    print_color("  Mencoba fallback ke git...\n", "yellow")
                else:
                    raise VesiError(f"Push gagal: {result.message}")

    # ═══════════════════════════════════════════════════════════════
    # Method 2: Fallback via git subprocess
    # ═══════════════════════════════════════════════════════════════
    print_color("\n2️⃣  Push via git (fallback)...\n", "yellow")

    success, message = push_via_git_subprocess(
        repo_root=repo.root,
        remote=remote_name,
        branch=branch,
        force=force,
        on_progress=lambda msg, *_: print(f"  {msg}"),
    )

    if success:
        print_color(f"\n{'━' * 50}", "dim")
        print_color("✓ Push berhasil!", "green")
        print(f"  Remote: {remote_name}/{branch}")
        print(f"  Commit: {short_hash(current_hash)}")

        if set_upstream:
            print(f"\n  ✓ Upstream set: {remote_name}/{branch}")

        return 0
    else:
        raise VesiError(
            f"Push gagal: {message}",
            hint=(
                "Tips:\n"
                "  1. Pastikan token sudah di-set: export GITHUB_TOKEN=xxx\n"
                "  2. Atau gunakan SSH: ganti URL ke git@github.com:user/repo.git\n"
                "  3. Cek permissions repository"
            ),
        )


def _collect_commit_chain(repo: Repository, head_hash: str, max_count: int = 100) -> list[str]:
    """Walk the commit graph and collect commit hashes.

    Returns list of hashes from newest to oldest.
    """
    hashes = []
    current = head_hash

    for _ in range(max_count):
        if not current or current in hashes:
            break
        hashes.append(current)

        try:
            commit_data = repo.objects.load_json(current)
            parent = commit_data.get("parent")
            parents = commit_data.get("parents", [])
            current = parent or (parents[0] if parents else None)
        except Exception:
            break

    return hashes
