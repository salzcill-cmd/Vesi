"""Main CLI application entry point."""

from __future__ import annotations

import json
import logging
import platform
import sys
from pathlib import Path

from vesi import __version__
from vesi.parser.parser import parse_command
from vesi.commands.router import route_command
from vesi.errors.exceptions import VesiError
from vesi.utils.logging_setup import setup_logging
from vesi.utils.platform import print_color

logger = logging.getLogger("vesi")

# Custom alias expansion (PRD 56).
def _expand_custom_alias(input_text: str) -> str:
    """Replace a leading custom alias with its command expansion.

    Custom aliases never override canonical commands or built-in aliases.
    Returns the (possibly unchanged) input string.
    """
    if not input_text:
        return input_text

    first = input_text.split(None, 1)[0].lower()

    # Canonical verbs and single-word aliases take precedence (rule 1).
    from vesi.parser.parser import VERB_ALIASES, SINGLE_WORD_ALIASES
    if first in VERB_ALIASES or first in SINGLE_WORD_ALIASES:
        return input_text

    from vesi.utils.paths import get_repo_root
    root = get_repo_root()
    if root is None:
        return input_text

    alias_file = root / ".vesi" / "aliases.json"
    if not alias_file.is_file():
        return input_text

    try:
        aliases = json.loads(alias_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return input_text

    if first not in aliases:
        return input_text

    expansion = str(aliases[first]).strip()
    if not expansion:
        return input_text

    rest = input_text.split(None, 1)[1] if " " in input_text else ""
    return " ".join(part for part in [expansion, rest] if part)



def main(argv: list[str] | None = None) -> int:
    """Main entry point for the vesi CLI.

    Returns exit code.
    """
    if argv is None:
        argv = sys.argv[1:]

    # Handle --version
    if "--version" in argv:
        if "--json" in argv:
            print(json.dumps({"version": __version__, "name": "vesi"}))
        else:
            print(f"vesi {__version__}")
        return 0

    # Handle --help at top level
    if "--help" in argv or "-h" in argv:
        _print_general_help()
        return 0

    # No command = show help
    if not argv:
        _print_welcome()
        return 0

    # Expand custom aliases from the repository before parsing (PRD 56: rule 1 —
    # custom aliases never override canonical commands).
    input_text = _expand_custom_alias(" ".join(argv))

    # Parse and route command
    parsed = parse_command(input_text)

    # Check for global flags
    verbose = "--verbose" in argv
    debug = "--debug" in argv
    json_output = "--json" in argv

    setup_logging(debug=debug)

    try:
        if json_output:
            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = route_command(parsed, verbose=verbose, debug=debug)
            # Deterministic, machine-readable envelope on success (PRD 54).
            print(json.dumps({
                "success": exit_code == 0,
                "command": parsed.full_command or parsed.raw,
                "exit_code": exit_code,
                "output": buf.getvalue().rstrip("\n"),
            }, ensure_ascii=False))
            return exit_code
        exit_code = route_command(parsed, verbose=verbose, debug=debug)
        return exit_code
    except VesiError as e:
        exit_code = getattr(e, "exit_code", 1)
        if json_output:
            print(json.dumps({
                "error": True,
                "message": str(e),
                "hint": e.hint,
                "exit_code": exit_code,
            }, ensure_ascii=False))
        else:
            _print_error(e)
        return exit_code
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as e:
        logger.exception("Unhandled exception")
        if debug:
            raise
        if json_output:
            print(json.dumps({
                "error": True,
                "message": str(e),
                "exit_code": 1,
            }, ensure_ascii=False))
        else:
            print_color(f"✗ Terjadi kesalahan tak terduga: {e}", "red")
        return 1


def _print_welcome() -> None:
    """Print welcome message when no command is given."""
    print("vesi — Version control yang gampang dipelajari\n")
    print("Cara pakai:")
    print()
    print("  vesi mulai               Buat repository baru")
    print("  vesi stel .              Siapkan semua file")
    print('  vesi simpan "pesan"      Simpan versi')
    print("  vesi lihat riwayat       Lihat daftar versi")
    print("  vesi bandingkan          Lihat perbedaan")
    print()
    print("Tip: Gunakan shortcut!")
    print("  vesi status              = lihat perubahan")
    print("  vesi riwayat             = lihat riwayat")
    print("  vesi cabang              = lihat cabang")
    print("  vesi batal <file>        = batalkan perubahan")
    print()
    print("Pelajari lebih lanjut:")
    print("  vesi bantuan             Lihat semua command")
    print("  vesi jelaskan versi      Pelajari konsep")


def _print_general_help() -> None:
    """Print general help."""
    print("vesi — Version control yang gampang dipelajari\n")
    print("Penggunaan:")
    print("    vesi <command> [arguments] [options]\n")
    print("Cepat mulai:")
    print("    vesi mulai              Buat repository baru")
    print("    vesi stel .             Siapkan semua file")
    print('    vesi simpan "pesan"     Simpan versi')
    print("    vesi lihat riwayat      Lihat daftar versi\n")
    print("Command lengkap:")
    print("    ── Repository ──")
    print("    mulai [proyek]          Buat repository baru")
    print("    status                  Lihat file yang berubah")
    print("    cek                     Periksa integritas repository")
    print("    konfigurasi             Kelola pengaturan\n")
    print("    ── Menyimpan ──")
    print("    stel <file>             Siapkan file (= siap, add)")
    print('    simpan "pesan"          Simpan versi (= save, commit)')
    print("    riwayat                 Lihat daftar versi (= log)")
    print("    bandingkan              Lihat perbedaan (= diff)\n")
    print("    ── Memulihkan ──")
    print("    pulihkan <file>         Kembalikan file (= restore)")
    print("    batal <file>            Batalkan perubahan (= undo)\n")
    print("    ── Cabang ──")
    print("    cabang baru <nama>      Buat cabang baru")
    print("    cabang                  Lihat semua cabang")
    print("    cabang pindah <nama>    Pindah ke cabang lain")
    print("    cabang hapus <nama>     Hapus cabang")
    print("    gabung <nama>           Gabungkan cabang\n")
    print("    ── Lainnya ──")
    print("    bantuan                 Tampilkan bantuan (= help)")
    print("    jelaskan <konsep>       Pelajari konsep (= explain)")
    print("\nOpsi:")
    print("    --version               Tampilkan versi")
    print("    --verbose               Output detail")
    print("    --debug                 Debug information")
    print("    --json                  Output dalam format JSON")
    print("    --no-color              Tanpa warna")


def _print_error(error: VesiError) -> None:
    """Print error with helpful hint."""
    print_color(f"✗ {error}", "red")
    if error.hint:
        print(f"\n{error.hint}")


def get_diagnostics() -> dict:
    """Get diagnostic information about the current environment."""
    from vesi.repository.repository import Repository
    from vesi.utils.paths import get_repo_root

    info = {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.system(),
        "arch": platform.machine(),
        "cwd": str(Path.cwd()),
    }

    # Check for repository
    repo_root = get_repo_root()
    if repo_root:
        repo = Repository(repo_root)
        info["repository"] = {
            "root": str(repo_root),
            "objects": repo.objects.count_objects(),
            "size": repo.objects.total_size(),
            "branches": len(repo.refs.list_branches()),
            "active_branch": repo.refs.get_active_branch(),
            "head": repo.refs.get_head(),
        }
    else:
        info["repository"] = None

    return info


if __name__ == "__main__":
    sys.exit(main())
