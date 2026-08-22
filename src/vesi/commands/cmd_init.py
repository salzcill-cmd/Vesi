"""Command: mulai proyek - Initialize a new repository."""

from __future__ import annotations

from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryAlreadyExistsError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_mulai_proyek(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Initialize a new repository."""
    # Get target path
    if parsed.args:
        target = Path.cwd() / parsed.args[0]
    else:
        target = Path.cwd()

    try:
        repo = Repository.init(target)
        root = repo.root
        vesi_dir = repo.vesi_dir

        print_color(f"✓ Repository berhasil dibuat!", "green")
        print(f"  Lokasi: {root}")
        print(f"  Struktur: {vesi_dir.relative_to(root)}")
        print(f"  File awal: .abaikan")

        if verbose:
            print(f"\n  Config: {vesi_dir / 'config'}")
            print(f"  Objects: {vesi_dir / 'objects'}")
            print(f"  Refs: {vesi_dir / 'refs'}")

        return 0

    except RepositoryAlreadyExistsError:
        raise
    except PermissionError:
        raise VesiError(
            f"Tidak bisa membuat folder di {target}",
            hint="Periksa permissions folder.",
        )
    except OSError as e:
        raise VesiError(f"Gagal membuat repository: {e}")
