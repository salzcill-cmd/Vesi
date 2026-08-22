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
}

# Subcommand aliases: (verb, sub) -> canonical (verb, sub)
SUBCOMMAND_ALIASES: dict[tuple[str, str], tuple[str, str]] = {
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
    """Parse: hapus cabang <nama>"""
    if tokens:
        sub = tokens[0].value.lower()
        if sub in ("cabang", "branch"):
            cmd.subcommand = "cabang"
            cmd.args = [t.value for t in tokens[1:]]
        else:
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
