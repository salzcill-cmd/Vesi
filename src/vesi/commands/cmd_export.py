"""Command: ekspor/impor - Export and import repositories."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


def cmd_ekspor(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Export repository to zip file.

    Usage:
      ekspor [filename]           - Export to vesi-backup.zip
      ekspor --ke <path>          - Export to specific path
    """
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    args = parsed.args or []
    flags = parsed.flags

    # Determine output filename
    if "--ke" in flags:
        idx = flags.index("--ke")
        output_path = Path(args[idx]) if idx < len(args) else Path("vesi-backup.zip")
    elif args:
        output_path = Path(args[0])
    else:
        output_path = Path("vesi-backup.zip")

    # Add .zip extension if missing
    if not str(output_path).endswith(".zip"):
        output_path = Path(str(output_path) + ".zip")

    print_color("📦 Mengekspor repository...\n", "cyan")

    # Create zip file
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add all files except .vesi directory internals (keep structure)
        for root, dirs, files in os.walk(repo.root):
            # Skip .vesi directory but include its metadata
            if ".vesi" in root:
                # Only include config and refs, not objects
                if "objects" in root:
                    continue
                dirs.clear()
                continue

            dirs[:] = [d for d in dirs if d != ".vesi"]

            for filename in files:
                filepath = Path(root) / filename
                arcname = filepath.relative_to(repo.root)
                zf.write(filepath, arcname)
                if verbose:
                    print(f"  + {arcname}")

        # Add vesi metadata
        vesi_dir = repo.vesi_dir
        for metadata_file in ["config", "HEAD"]:
            src = vesi_dir / metadata_file
            if src.is_file():
                zf.write(src, f".vesi/{metadata_file}")

        # Add refs
        refs_dir = vesi_dir / "refs"
        if refs_dir.is_dir():
            for ref_file in refs_dir.rglob("*"):
                if ref_file.is_file():
                    arcname = f".vesi/refs/{ref_file.relative_to(refs_dir)}"
                    zf.write(ref_file, arcname)

    # Get file size
    size = output_path.stat().st_size
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size / (1024 * 1024):.1f} MB"

    print_color("✓ Export berhasil!", "green")
    print(f"  File: {output_path}")
    print(f"  Ukuran: {size_str}")

    return 0


def cmd_impor(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Import repository from zip file or Git repository.

    Usage:
      impor <filename>            - Import from vesi backup zip
      impor --dari <path>         - Import from specific path
    """
    args = parsed.args or []
    flags = parsed.flags

    # Determine input file
    if "--dari" in flags:
        idx = flags.index("--dari")
        input_path = Path(args[idx]) if idx < len(args) else None
    elif args:
        input_path = Path(args[0])
    else:
        raise VesiError(
            "Tentukan file yang akan diimpor.",
            hint="Contoh:\n  impor vesi-backup.zip\n  impor --dari backup.zip",
        )

    if not input_path or not input_path.is_file():
        raise VesiError(f"File '{input_path}' tidak ditemukan.")

    print_color("📦 Mengimpor repository...\n", "cyan")

    # Check if it's a zip file
    if str(input_path).endswith(".zip"):
        # Import from vesi backup
        with zipfile.ZipFile(input_path, "r") as zf:
            zf.extractall(".")

        print_color("✓ Import berhasil!", "green")
        print(f"  File: {input_path}")
        print(f"  Repository sudah bisa digunakan.")

    elif str(input_path).endswith((".tar.gz", ".tgz")):
        # Import from tar.gz (could be git archive)
        import tarfile
        with tarfile.open(input_path, "r:gz") as tar:
            tar.extractall(".")

        print_color("✓ Import berhasil!", "green")
        print(f"  File: {input_path}")

    else:
        raise VesiError(
            f"Format file '{input_path.suffix}' tidak didukung.",
            hint="Gunakan file .zip atau .tar.gz",
        )

    return 0


# Need to import os for walk
import os
