"""Command: gabungkan - Merge branches."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.merge.engine import merge_branch, MergeResult
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_gabungkan(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Merge a branch into the current active branch."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    if not parsed.args:
        raise VesiError(
            "Tentukan cabang yang akan digabungkan.",
            hint="Contoh:\n    gabungkan <nama-cabang>",
        )

    source_branch = parsed.args[0]

    result = merge_branch(repo, source_branch, dry_run=False)

    if result.success:
        print_color(f"✓ {result.message}", "green")
        return 0
    elif result.merge_type == "conflict":
        print_color(f"⚠ {result.message}", "yellow")
        print(f"\n  File yang konflik:")
        for f in result.conflicts:
            print(f"    - {f}")
        print(f"\n  Perbaiki file tersebut, lalu jalankan:")
        print(f"    lanjutkan gabungan")
        print(f"\n  Atau batalkan:")
        print(f"    batalkan gabungan")
        return 4
    else:
        print_color(f"✗ {result.message}", "red")
        return 1
