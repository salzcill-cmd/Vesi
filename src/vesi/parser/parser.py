"""Command parser - parse tokens into structured command representation."""

from __future__ import annotations

from dataclasses import dataclass, field

from vesi.parser.lexer import Token, tokenize


@dataclass
class ParsedCommand:
    """A parsed command with verb, subcommand, args, and options."""

    verb: str = ""
    subcommand: str = ""
    args: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def full_command(self) -> str:
        """Get the full command string (verb + subcommand)."""
        parts = [self.verb, self.subcommand]
        return " ".join(p for p in parts if p)

    @property
    def first_arg(self) -> str | None:
        """Get the first argument, or None."""
        return self.args[0] if self.args else None


# ═══════════════════════════════════════════════════════════════════
# ALIAS SYSTEM
# ═══════════════════════════════════════════════════════════════════

# Single-word aliases: word -> (verb, subcommand)
SINGLE_WORD_ALIASES: dict[str, tuple[str, str]] = {
    "status": ("lihat", "perubahan"),
    "changes": ("lihat", "perubahan"),
    "riwayat": ("lihat", "riwayat"),
    "log": ("lihat", "riwayat"),
    "history": ("lihat", "riwayat"),
    "cabang": ("lihat", "cabang"),
    "branch": ("lihat", "cabang"),
    "branches": ("lihat", "cabang"),
    "tag": ("lihat", "tag"),
    "tags": ("lihat", "tag"),
    "bantuan": ("bantuan", ""),
    "help": ("bantuan", ""),
    "?": ("bantuan", ""),
    "cek": ("cek", "proyek"),
    "check": ("cek", "proyek"),
    "verify": ("cek", "proyek"),
    "fsck": ("cek", "proyek"),
}

# Multi-word verb aliases: verb -> canonical verb
VERB_ALIASES: dict[str, str] = {
    "stel": "stel",
    "siap": "stel",
    "persiap": "stel",
    "add": "stel",
    "stage": "stel",
    "simpan": "simpan",
    "save": "simpan",
    "commit": "simpan",
    "bandingkan": "bandingkan",
    "diff": "bandingkan",
    "perbedaan": "bandingkan",
    "pulihkan": "pulihkan",
    "restore": "pulihkan",
    "batalkan": "batalkan",
    "batal": "batalkan",
    "undo": "batalkan",
    "buat": "buat",
    "create": "buat",
    "new": "buat",
    "baru": "buat",
    "pindah": "pindah",
    "switch": "pindah",
    "goto": "pindah",
    "hapus": "hapus",
    "delete": "hapus",
    "remove": "hapus",
    "del": "hapus",
    "gabungkan": "gabungkan",
    "gabung": "gabungkan",
    "merge": "gabungkan",
    "konfigurasi": "konfigurasi",
    "config": "konfigurasi",
    "set": "konfigurasi",
    "jelaskan": "jelaskan",
    "explain": "jelaskan",
    "apa": "jelaskan",
    "beri": "beri",
    "tag": "beri",
    "label": "beri",
    "isi": "isi",
    "show": "isi",
    "cat": "isi",
    "tampilkan": "isi",
    "cari": "cari",
    "search": "cari",
    "grep": "cari",
    "find": "cari",
    # Stash commands
    "sementara": "simpan sementara",
    "stash": "simpan sementara",
    "pop": "ambil",
    # Rebase commands
    "susun": "susun",
    "rebase": "susun",
    "squash": "susun",
    # Cherry-pick
    "cherry": "ambil",
    "pick": "ambil",
    # Blame
    "siapa": "siapa",
    "blame": "siapa",
    "annotate": "siapa",
    # Bisect
    "bagi": "bagi",
    "bisect": "bagi",
    # Reflog
    "jejak": "jejak",
    "reflog": "jejak",
    # Worktree
    "folder": "folder",
    "worktree": "folder",
    # New commands
    "undo": "batalkan versi",
    "cadangan": "cadangan",
    "backup": "cadangan",
    "pola": "pola",
    "template": "pola",
    "insights": "lihat file",
    "pintar": "bandingkan pintar",
    "smart": "bandingkan pintar",
    "bantu": "bantu",
    "help": "bantu",
}

# Subcommand aliases: (verb, sub) -> canonical (verb, sub)
SUBCOMMAND_ALIASES: dict[tuple[str, str], tuple[str, str]] = {
    # Stash subcommands
    ("simpan", "sementara"): ("simpan", "sementara"),
    ("simpan", "stash"): ("simpan", "sementara"),
    ("ambil", "stash"): ("ambil", "stash"),
    ("lihat", "stash"): ("lihat", "stash"),
    # Rebase subcommands
    ("susun", "ulang"): ("susun", "ulang"),
    ("susun", "rebase"): ("susun", "ulang"),
    # Cherry-pick subcommands
    ("ambil", "versi"): ("ambil", "versi"),
    ("ambil", "commit"): ("ambil", "versi"),
    ("cherry", "pick"): ("ambil", "versi"),
    ("lihat", "riwayat"): ("lihat", "riwayat"),
    ("lihat", "history"): ("lihat", "riwayat"),
    ("lihat", "log"): ("lihat", "riwayat"),
    ("lihat", "perubahan"): ("lihat", "perubahan"),
    ("lihat", "status"): ("lihat", "perubahan"),
    ("lihat", "changes"): ("lihat", "perubahan"),
    ("lihat", "cabang"): ("lihat", "cabang"),
    ("lihat", "branch"): ("lihat", "cabang"),
    ("lihat", "branches"): ("lihat", "cabang"),
    ("batalkan", "perubahan"): ("batalkan", "perubahan"),
    ("batalkan", "changes"): ("batalkan", "perubahan"),
    ("batalkan", "gabungan"): ("batalkan", "gabungan"),
    ("batalkan", "merge"): ("batalkan", "gabungan"),
    ("lanjutkan", "gabungan"): ("lanjutkan", "gabungan"),
    ("lanjutkan", "merge"): ("lanjutkan", "gabungan"),
    # New commands
    ("batalkan", "versi"): ("batalkan", "versi"),
    ("batalkan", "commit"): ("batalkan", "versi"),
    ("cadangan", "buat"): ("cadangan", "buat"),
    ("cadangan", "create"): ("cadangan", "buat"),
    ("cadangan", "pulihkan"): ("cadangan", "pulihkan"),
    ("cadangan", "restore"): ("cadangan", "pulihkan"),
    ("pola", "commit"): ("pola", "commit"),
    ("lihat", "file"): ("lihat", "file"),
    ("lihat", "insights"): ("lihat", "file"),
    ("bandingkan", "pintar"): ("bandingkan", "pintar"),
    ("bandingkan", "smart"): ("bandingkan", "pintar"),
    ("bantu", "konflik"): ("bantu", "konflik"),
    # Bisect subcommands
    ("bagi", "cari"): ("bagi", "cari"),
    ("bagi", "mulai"): ("bagi", "mulai"),
    ("bagi", "baik"): ("bagi", "baik"),
    ("bagi", "buruk"): ("bagi", "buruk"),
    ("bagi", "selesai"): ("bagi", "selesai"),
    # Siapa (blame)
    ("siapa", "ubah"): ("siapa", "ubah"),
}

# Branch operation patterns: "cabang <action>" -> (verb, subcommand)
CABANG_OPERATIONS: dict[str, tuple[str, str]] = {
    "baru": ("buat", "cabang"),
    "new": ("buat", "cabang"),
    "create": ("buat", "cabang"),
    "buat": ("buat", "cabang"),
    "pindah": ("pindah", "cabang"),
    "switch": ("pindah", "cabang"),
    "goto": ("pindah", "cabang"),
    "hapus": ("hapus", "cabang"),
    "delete": ("hapus", "cabang"),
    "remove": ("hapus", "cabang"),
    "del": ("hapus", "cabang"),
    "gabung": ("gabungkan", ""),
    "merge": ("gabungkan", ""),
}


def parse_command(input_text: str) -> ParsedCommand:
    """Parse a command string into a ParsedCommand.

    Natural Indonesian syntax with shortcuts:

    Single word:
        status          = lihat perubahan
        riwayat         = lihat riwayat
        log             = lihat riwayat
        cabang          = lihat cabang
        help            = bantuan
        cek             = cek proyek

    Multi word:
        mulai [proyek]           Init repository
        stel <file>              Stage file (= siap, add)
        simpan "pesan"           Commit (= save, commit)
        bandingkan               Diff (= diff)
        pulihkan <file>          Restore
        batal <file>             = batalkan perubahan
        cabang baru <nama>       Create branch
        cabang pindah <nama>     Switch branch
        cabang hapus <nama>      Delete branch
        gabung <nama>            = gabungkan
    """
    tokens = tokenize(input_text)

    if not tokens:
        return ParsedCommand(raw=input_text)

    cmd = ParsedCommand(raw=input_text)

    # Extract flags
    regular_tokens: list[Token] = []
    for t in tokens:
        if t.token_type == "flag":
            cmd.flags.append(t.value)
        else:
            regular_tokens.append(t)

    if not regular_tokens:
        return cmd

    first_word = regular_tokens[0].value.lower()

    # Check single-word aliases first
    if len(regular_tokens) == 1 and first_word in SINGLE_WORD_ALIASES:
        verb, sub = SINGLE_WORD_ALIASES[first_word]
        cmd.verb = verb
        cmd.subcommand = sub
        return cmd

    # ── Special handling for "cabang <action>" pattern ──
    if first_word == "cabang" and len(regular_tokens) >= 2:
        action = regular_tokens[1].value.lower()
        if action in CABANG_OPERATIONS:
            verb, sub = CABANG_OPERATIONS[action]
            cmd.verb = verb
            cmd.subcommand = sub
            cmd.args = [t.value for t in regular_tokens[2:]]
            return cmd

    # Apply verb alias
    verb = VERB_ALIASES.get(first_word, first_word)
    cmd.verb = verb

    if len(regular_tokens) < 2:
        return cmd

    # Get subcommand candidate
    sub_raw = regular_tokens[1].value.lower()

    # Check for subcommand alias
    alias_key = (verb, sub_raw)
    if alias_key in SUBCOMMAND_ALIASES:
        new_verb, new_sub = SUBCOMMAND_ALIASES[alias_key]
        cmd.verb = new_verb
        cmd.subcommand = new_sub
        remaining = regular_tokens[2:]

        if new_verb == "simpan":
            if remaining:
                cmd.args = [" ".join(t.value for t in remaining)]
        elif new_verb == "pulihkan":
            _parse_pulihkan(cmd, remaining)
        elif new_verb == "gabungkan":
            cmd.args = [t.value for t in remaining]
        elif new_verb in ("buat", "pindah", "hapus"):
            cmd.args = [t.value for t in remaining]
        else:
            cmd.args = [t.value for t in remaining]

        return cmd

    # Standard parsing based on verb
    if verb == "mulai":
        _parse_mulai(cmd, regular_tokens[1:])
    elif verb == "lihat":
        _parse_lihat(cmd, regular_tokens[1:])
    elif verb == "simpan":
        _parse_simpan(cmd, regular_tokens[1:])
    elif verb == "bandingkan":
        _parse_bandingkan(cmd, regular_tokens[1:])
    elif verb == "pulihkan":
        _parse_pulihkan(cmd, regular_tokens[1:])
    elif verb == "batalkan":
        _parse_batalkan(cmd, regular_tokens[1:])
    elif verb == "buat":
        _parse_buat(cmd, regular_tokens[1:])
    elif verb == "pindah":
        _parse_pindah(cmd, regular_tokens[1:])
    elif verb == "hapus":
        _parse_hapus(cmd, regular_tokens[1:])
    elif verb == "gabungkan":
        _parse_gabungkan(cmd, regular_tokens[1:])
    elif verb == "stel":
        _parse_stel(cmd, regular_tokens[1:])
    elif verb == "bantuan":
        _parse_bantuan(cmd, regular_tokens[1:])
    elif verb == "jelaskan":
        _parse_jelaskan(cmd, regular_tokens[1:])
    elif verb == "cek":
        _parse_cek(cmd, regular_tokens[1:])
    elif verb == "konfigurasi":
        _parse_konfigurasi(cmd, regular_tokens[1:])
    elif verb == "lanjutkan":
        _parse_lanjutkan(cmd, regular_tokens[1:])
    elif verb == "beri":
        _parse_beri(cmd, regular_tokens[1:])
    elif verb == "isi":
        _parse_isi(cmd, regular_tokens[1:])
    elif verb == "cari":
        _parse_cari(cmd, regular_tokens[1:])
    elif verb == "susun":
        _parse_susun(cmd, regular_tokens[1:])
    elif verb == "ambil":
        _parse_ambil(cmd, regular_tokens[1:])
    elif verb == "siapa":
        _parse_siapa(cmd, regular_tokens[1:])
    elif verb == "bagi":
        _parse_bagi(cmd, regular_tokens[1:])
    elif verb == "jejak":
        _parse_jejak(cmd, regular_tokens[1:])
    elif verb == "folder":
        _parse_folder(cmd, regular_tokens[1:])
    else:
        cmd.args = [t.value for t in regular_tokens[1:]]

    return cmd


# ═══════════════════════════════════════════════════════════════════
# PARSER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════


def _parse_mulai(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: mulai [proyek] [nama]"""
    cmd.subcommand = "proyek"
    if tokens and tokens[0].value.lower() in ("proyek", "repo", "repository"):
        cmd.args = [t.value for t in tokens[1:]]
    else:
        cmd.args = [t.value for t in tokens]


def _parse_lihat(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: lihat perubahan | lihat riwayat [n] | lihat cabang"""
    if not tokens:
        cmd.subcommand = ""
        return

    sub = tokens[0].value.lower()

    sub_map = {
        "riwayat": "riwayat",
        "history": "riwayat",
        "log": "riwayat",
        "perubahan": "perubahan",
        "status": "perubahan",
        "changes": "perubahan",
        "cabang": "cabang",
        "branch": "cabang",
        "branches": "cabang",
    }

    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_simpan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: simpan [versi] "message" | simpan "message" """
    if not tokens:
        return

    cmd.subcommand = "versi"

    start = 0
    if tokens[0].value.lower() in ("versi", "version", "commit"):
        start = 1

    if start < len(tokens):
        msg_parts = [t.value for t in tokens[start:]]
        cmd.args = [" ".join(msg_parts)]


def _parse_bandingkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: bandingkan [versi1] [versi2]"""
    cmd.args = [t.value for t in tokens]


def _parse_pulihkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: pulihkan <file> [dari <versi>]"""
    i = 0
    while i < len(tokens):
        val = tokens[i].value.lower()
        if val in ("dari", "from", "ke"):
            i += 1
            if i < len(tokens):
                cmd.options["from"] = tokens[i].value
            i += 1
        else:
            cmd.args.append(tokens[i].value)
            i += 1


def _parse_batalkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: batalkan [perubahan] <file> | batalkan gabungan"""
    if not tokens:
        return

    first = tokens[0].value.lower()

    if first in ("perubahan", "changes"):
        cmd.subcommand = "perubahan"
        cmd.args = [t.value for t in tokens[1:]]
    elif first in ("gabungan", "merge"):
        cmd.subcommand = "gabungan"
    else:
        cmd.subcommand = "perubahan"
        cmd.args = [t.value for t in tokens]


def _parse_buat(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: buat cabang <nama>"""
    if tokens:
        sub = tokens[0].value.lower()
        if sub in ("cabang", "branch"):
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens[1:]]
        else:
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens]


def _parse_pindah(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: pindah cabang <nama>"""
    if tokens:
        sub = tokens[0].value.lower()
        if sub in ("cabang", "branch"):
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens[1:]]
        else:
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens]


def _parse_hapus(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: hapus cabang <nama> | hapus tag <nama> | hapus stash"""
    if tokens:
        sub = tokens[0].value.lower()
        if sub in ("cabang", "branch"):
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens[1:]]
        elif sub in ("tag", "label"):
            cmd.subcommand = "tag"
            cmd.args = [t.value for t in tokens[1:]]
        elif sub in ("stash",):
            cmd.subcommand = "stash"
            cmd.args = [t.value for t in tokens[1:]]
        else:
            # Default: treat as cabang with the first token as the branch name
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens]


def _parse_gabungkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: gabungkan <cabang>"""
    cmd.args = [t.value for t in tokens]


def _parse_stel(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: stel <file> | stel ."""
    cmd.args = [t.value for t in tokens]


def _parse_bantuan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: bantuan [command]"""
    cmd.args = [t.value for t in tokens]


def _parse_jelaskan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: jelaskan <konsep>"""
    cmd.args = [t.value for t in tokens]


def _parse_cek(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: cek [proyek]"""
    cmd.subcommand = "proyek"


def _parse_konfigurasi(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: konfigurasi [key] [value]"""
    cmd.args = [t.value for t in tokens]


def _parse_lanjutkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: lanjutkan gabungan"""
    if tokens:
        cmd.subcommand = tokens[0].value.lower()


def _parse_beri(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: beri tag <nama> [pesan]"""
    if tokens:
        sub = tokens[0].value.lower()
        if sub in ("tag", "label"):
            cmd.subcommand = "tag"
            cmd.args = [t.value for t in tokens[1:]]
        else:
            cmd.subcommand = "tag"
            cmd.args = [t.value for t in tokens]


def _parse_isi(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: isi <file> [dari <versi>]"""
    i = 0
    while i < len(tokens):
        val = tokens[i].value.lower()
        if val in ("dari", "from"):
            i += 1
            if i < len(tokens):
                cmd.options["from"] = tokens[i].value
            i += 1
        else:
            cmd.args.append(tokens[i].value)
            i += 1


def _parse_cari(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: cari <pola> [di <folder>]"""
    i = 0
    while i < len(tokens):
        val = tokens[i].value.lower()
        if val in ("di", "in"):
            i += 1
            if i < len(tokens):
                cmd.options["di"] = tokens[i].value
            i += 1
        else:
            cmd.args.append(tokens[i].value)
            i += 1


def _parse_susun(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: susun ulang [jumlah] | susun ulang ke <base>"""
    if not tokens:
        cmd.subcommand = "ulang"
        return

    sub = tokens[0].value.lower()
    if sub in ("ulang", "rebase"):
        cmd.subcommand = "ulang"
        remaining = tokens[1:]
        if remaining:
            # Check for 'ke' (to) pattern
            if remaining[0].value.lower() == "ke":
                cmd.subcommand = "ke"
                cmd.args = [t.value for t in remaining[1:]]
            else:
                cmd.args = [t.value for t in remaining]
    else:
        cmd.subcommand = "ulang"
        cmd.args = [t.value for t in tokens]


def _parse_ambil(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: ambil stash [index] | ambil versi <commit>"""
    if not tokens:
        cmd.subcommand = "versi"
        return

    sub = tokens[0].value.lower()
    if sub in ("stash", "stashing"):
        cmd.subcommand = "stash"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("versi", "commit", "pick", "cherry"):
        cmd.subcommand = "versi"
        cmd.args = [t.value for t in tokens[1:]]
    else:
        # Default: assume it's a commit hash for cherry-pick
        cmd.subcommand = "versi"
        cmd.args = [t.value for t in tokens]


def _parse_siapa(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: siapa ubah <file> [dari <versi>]"""
    if not tokens:
        return

    sub = tokens[0].value.lower()
    if sub in ("ubah", "change"):
        cmd.subcommand = "ubah"
        remaining = tokens[1:]
    else:
        cmd.subcommand = "ubah"
        remaining = tokens

    # Parse 'dari' (from) pattern
    i = 0
    while i < len(remaining):
        val = remaining[i].value.lower()
        if val in ("dari", "from"):
            i += 1
            if i < len(remaining):
                cmd.options["from"] = remaining[i].value
            i += 1
        else:
            cmd.args.append(remaining[i].value)
            i += 1


def _parse_bagi(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: bagi cari [mulai|baik|buruk|selesai]"""
    if not tokens:
        cmd.subcommand = "cari"
        return

    sub = tokens[0].value.lower()
    sub_map = {
        "cari": "cari",
        "mulai": "mulai",
        "start": "mulai",
        "baik": "baik",
        "good": "baik",
        "buruk": "buruk",
        "bad": "buruk",
        "selesai": "selesai",
        "reset": "selesai",
        "clear": "selesai",
    }
    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_jejak(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: jejak [count]"""
    cmd.args = [t.value for t in tokens]


def _parse_folder(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: folder kerja [buat|hapus|list]"""
    if not tokens:
        cmd.subcommand = "kerja"
        return

    sub = tokens[0].value.lower()
    
    # Handle 'folder kerja buat' pattern
    if sub == "kerja":
        # Check if there's another token after 'kerja'
        if len(tokens) > 1:
            action = tokens[1].value.lower()
            action_map = {
                "buat": "buat",
                "create": "buat",
                "add": "buat",
                "hapus": "hapus",
                "remove": "hapus",
                "rm": "hapus",
                "list": "list",
                "ls": "list",
            }
            cmd.subcommand = action_map.get(action, action)
            cmd.args = [t.value for t in tokens[2:]]
        else:
            cmd.subcommand = "kerja"
    else:
        # Direct action without 'kerja'
        action_map = {
            "buat": "buat",
            "create": "buat",
            "add": "buat",
            "hapus": "hapus",
            "remove": "hapus",
            "rm": "hapus",
            "list": "list",
            "ls": "list",
        }
        cmd.subcommand = action_map.get(sub, sub)
        cmd.args = [t.value for t in tokens[1:]]
