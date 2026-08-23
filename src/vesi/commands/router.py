"""Command router - dispatch parsed commands to handlers."""

from __future__ import annotations

from vesi.commands.cmd_init import cmd_mulai_proyek
from vesi.commands.cmd_status import cmd_lihat_perubahan
from vesi.commands.cmd_stage import cmd_stel
from vesi.commands.cmd_commit import cmd_simpan_versi
from vesi.commands.cmd_log import cmd_lihat_riwayat
from vesi.commands.cmd_diff import cmd_bandingkan
from vesi.commands.cmd_restore import cmd_pulihkan, cmd_batalkan_perubahan
from vesi.commands.cmd_branch import (
    cmd_buat_cabang,
    cmd_lihat_cabang,
    cmd_pindah_cabang,
    cmd_hapus_cabang,
)
from vesi.commands.cmd_merge import cmd_gabungkan
from vesi.commands.cmd_merge_abort import cmd_lanjutkan_gabungan, cmd_batalkan_gabungan
from vesi.commands.cmd_check import cmd_cek
from vesi.commands.cmd_config import cmd_konfigurasi
from vesi.commands.cmd_help import cmd_bantuan
from vesi.commands.cmd_explain import cmd_jelaskan
from vesi.commands.cmd_tag import cmd_beri_tag, cmd_lihat_tag, cmd_hapus_tag
from vesi.commands.cmd_show import cmd_isi
from vesi.commands.cmd_search import cmd_cari
from vesi.commands.cmd_amend import cmd_simpan_amend
from vesi.commands.cmd_stash import (
    cmd_simpan_sementara,
    cmd_ambil_stash,
    cmd_lihat_stash,
    cmd_hapus_stash,
)
from vesi.commands.cmd_cherrypick import cmd_ambil_versi
from vesi.commands.cmd_rebase import cmd_susun_ulang, cmd_susun_ulang_ke
from vesi.errors.exceptions import InvalidCommandError
from vesi.parser.parser import ParsedCommand


def cmd_beri(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'beri tag' command."""
    if parsed.subcommand == "tag":
        return cmd_beri_tag(parsed, verbose=verbose, debug=debug)
    return cmd_beri_tag(parsed, verbose=verbose, debug=debug)


def cmd_ambil_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'ambil' command - dispatch to stash or cherry-pick."""
    if parsed.subcommand == "stash":
        return cmd_ambil_stash(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "versi":
        return cmd_ambil_versi(parsed, verbose=verbose, debug=debug)
    else:
        # Default to cherry-pick
        return cmd_ambil_versi(parsed, verbose=verbose, debug=debug)


def cmd_simpan_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle simpan command with --amend flag."""
    if "--amend" in parsed.flags:
        return cmd_simpan_amend(parsed, verbose=verbose, debug=debug)
    return cmd_simpan_versi(parsed, verbose=verbose, debug=debug)


# Map of verb -> handler function (for simple commands)
COMMANDS: dict[str, callable] = {
    "mulai": cmd_mulai_proyek,
    "stel": cmd_stel,
    "simpan": cmd_simpan_handler,
    "bandingkan": cmd_bandingkan,
    "pulihkan": cmd_pulihkan,
    "cek": cmd_cek,
    "konfigurasi": cmd_konfigurasi,
    "bantuan": cmd_bantuan,
    "jelaskan": cmd_jelaskan,
    "gabungkan": cmd_gabungkan,
    "beri": cmd_beri,
    "isi": cmd_isi,
    "cari": cmd_cari,
    "susun": cmd_susun_ulang,
    "ambil": cmd_ambil_handler,
}

# Map of verb+subcommand -> handler function
SUBCOMMANDS: dict[tuple[str, str], callable] = {
    ("lihat", "perubahan"): cmd_lihat_perubahan,
    ("lihat", "riwayat"): cmd_lihat_riwayat,
    ("lihat", "cabang"): cmd_lihat_cabang,
    ("lihat", "tag"): cmd_lihat_tag,
    ("lihat", "stash"): cmd_lihat_stash,
    ("buat", "cabang"): cmd_buat_cabang,
    ("pindah", "cabang"): cmd_pindah_cabang,
    ("hapus", "cabang"): cmd_hapus_cabang,
    ("hapus", "tag"): cmd_hapus_tag,
    ("hapus", "stash"): cmd_hapus_stash,
    ("batalkan", "perubahan"): cmd_batalkan_perubahan,
    ("batalkan", "gabungan"): cmd_batalkan_gabungan,
    ("lanjutkan", "gabungan"): cmd_lanjutkan_gabungan,
    ("susun", "ulang"): cmd_susun_ulang,
    ("susun", "ke"): cmd_susun_ulang_ke,
    ("ambil", "stash"): cmd_ambil_stash,
    ("ambil", "versi"): cmd_ambil_versi,
    ("simpan", "sementara"): cmd_simpan_sementara,
}

# Suggestion map for similar commands
SUGGESTIONS: dict[str, str] = {
    "mulai": "mulai proyek",
    "init": "mulai proyek",
    "status": "lihat perubahan",
    "add": "stel",
    "stage": "stel",
    "commit": "simpan versi",
    "save": "simpan versi",
    "log": "lihat riwayat",
    "history": "lihat riwayat",
    "riwayat": "lihat riwayat",
    "diff": "bandingkan",
    "restore": "pulihkan",
    "checkout": "pindah cabang",
    "branch": "lihat cabang",
    "cabang": "lihat cabang",
    "tag": "lihat tag",
    "merge": "gabungkan",
    "gabung": "gabungkan",
    "help": "bantuan",
    "explain": "jelaskan",
    "check": "cek",
    "config": "konfigurasi",
    "show": "isi",
    "cat": "isi",
    "search": "cari",
    "grep": "cari",
    "find": "cari",
    # Stash commands
    "stash": "simpan sementara",
    "sementara": "simpan sementara",
    "pop": "ambil stash",
    # Rebase commands
    "rebase": "susun ulang",
    "squash": "susun ulang",
    # Cherry-pick
    "cherry-pick": "ambil versi",
    "pick": "ambil versi",
}


def route_command(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Route a parsed command to its handler.

    Returns exit code.
    """
    verb = parsed.verb

    if not verb:
        raise InvalidCommandError(parsed.raw or "(empty)")

    # Try subcommand routing first
    if parsed.subcommand:
        subcommand_key = (verb, parsed.subcommand)
        handler = SUBCOMMANDS.get(subcommand_key)
        if handler:
            return handler(parsed, verbose=verbose, debug=debug)

    # Try simple command routing
    handler = COMMANDS.get(verb)
    if handler:
        return handler(parsed, verbose=verbose, debug=debug)

    # Unknown command
    suggestion = SUGGESTIONS.get(verb)
    raise InvalidCommandError(verb, suggestion=suggestion)
