"""Main CLI application entry point."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from vesi import __version__
from vesi.parser.parser import parse_command
from vesi.commands.router import route_command
from vesi.errors.exceptions import VesiError
from vesi.utils.platform import print_color


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

    # Parse and route command
    input_text = " ".join(argv)
    parsed = parse_command(input_text)

    # Check for global flags
    verbose = "--verbose" in argv
    debug = "--debug" in argv
    json_output = "--json" in argv

    try:
        exit_code = route_command(parsed, verbose=verbose, debug=debug)
        return exit_code
    except VesiError as e:
        if json_output:
            print(json.dumps({
                "error": True,
                "message": str(e),
                "hint": e.hint,
                "exit_code": 1,
            }))
        else:
            _print_error(e)
        return 1
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as e:
        if debug:
            raise
        if json_output:
            print(json.dumps({
                "error": True,
                "message": str(e),
                "exit_code": 1,
            }))
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
