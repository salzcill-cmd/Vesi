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
    "pp": ("lihat", "perubahan"),
    "riwayat": ("lihat", "riwayat"),
    "log": ("lihat", "riwayat"),
    "history": ("lihat", "riwayat"),
    "brp": ("lihat", "riwayat"),
    "kemana": ("lihat", "riwayat"),
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
    "stats": ("statistik", ""),
    "statistik": ("statistik", ""),
    # Emoji commands
    "💾": ("simpan", ""),
    "📋": ("lihat", "perubahan"),
    "📊": ("statistik", ""),
    "🔍": ("cari", ""),
    "🌿": ("lihat", "cabang"),
    "🏷️": ("lihat", "tag"),
    "↩️": ("lihat", "riwayat"),
    "❓": ("bantuan", ""),
    "🔄": ("batalkan", "versi"),
    "📦": ("cadangan", ""),
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
    # Bahasa gaul / casual
    "gas": "simpan",
    "gaskeun": "simpan",
    "udah": "simpan",
    "done": "simpan",
    "slesai": "simpan",
    "selesai": "simpan",
    "batalin": "batalkan",
    "urungkan": "batalkan",
    "gak jadi": "batalkan",
    "lupa": "lihat riwayat",
    "kemana": "lihat riwayat",
    "terakhir": "lihat riwayat",
    "sebelumnya": "lihat riwayat",
    "liat": "lihat perubahan",
    "cek": "cek",
    "pp": "lihat perubahan",
    "brp": "lihat riwayat",
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
    # Latest features
    "semua": "batalkan semua",
    "travel": "kembali ke waktu",
    "waktu": "kembali ke waktu",
    "cepat": "pindah cepat",
    "quick": "pindah cepat",
    "foto": "foto otomatis",
    "snapshot": "foto otomatis",
    "pesan": "pesan pintar",
    "message": "pesan pintar",
    "detail": "lihat cabang detail",
    "compare": "lihat cabang bandingkan",
    "titik": "titik pulih",
    "point": "titik pulih",
    "help": "bantu",
    # Advanced features
    "wizard": "simpan interaktif",
    "statistik": "statistik",
    "stats": "statistik",
    "auto": "auto",
    "autosave": "auto",
    "ekspor": "ekspor",
    "export": "ekspor",
    "impor": "impor",
    "import": "impor",
    "alias": "alias",
    "aliases": "alias",
    "kunci": "kunci",
    "lock": "kunci",
    "asisten": "asisten",
    "assistant": "asisten",
    # New upgraded commands
    "tampilkan": "tampilkan",
    "show": "tampilkan",
    "ringkasan": "ringkasan",
    "shortlog": "ringkasan",
    "grafik": "grafik",
    "graph": "grafik",
    "deskripsi": "deskripsi",
    "describe": "deskripsi",
    "gabung": "gabungkan",
    "catatan": "catatan",
    "notes": "catatan",
    "verifikasi": "verifikasi",
    "verify": "verifikasi",
    "bersihkan": "bersihkan",
    "gc": "bersihkan",
    "kumpulkan": "bersihkan",
    "pack": "kemas",
    "kemas": "kemas",
    # Git bridge commands
    "git": "git",
    # Remote commands
    "klon": "klon",
    "clone": "klon",
    "kirim": "kirim",
    "push": "kirim",
    "unduh": "unduh",
    "fetch": "unduh",
    "ambil remote": "ambil remote",
    "pull": "ambil remote",
    "remote": "remote",
    # New advanced commands
    "hook": "hook",
    "hooks": "hook",
    "plugin": "plugin",
    "plugins": "plugin",
    "watch": "watch",
    "pelihara": "watch",
    "completion": "completion",
    "selesai": "completion",
    # New vesi-exclusive commands
    "pindah file": "pindah file",
    "mv": "pindah file",
    "move": "pindah file",
    "rename": "pindah file",
    "hapus file": "hapus file",
    "rm": "hapus file",
    "remove": "hapus file",
    "balikkan": "balikkan",
    "revert": "balikkan",
    "atur ulang": "atur ulang",
    "reset": "atur ulang",
    "bersihkan file": "bersihkan file",
    "clean": "bersihkan file",
    "visual": "visual",
    "visual diff": "visual",
    "side-by-side": "visual",
    "suggest": "suggest",
    "saran": "suggest",
    "suggest commit": "suggest",
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
    # New upgraded commands
    ("tampilkan", "versi"): ("tampilkan", "versi"),
    ("tampilkan", "commit"): ("tampilkan", "versi"),
    ("ringkasan", ""): ("ringkasan", ""),
    ("grafik", ""): ("grafik", ""),
    ("deskripsi", ""): ("deskripsi", ""),
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


def _fix_typos(word: str) -> str:
    """Fix common typos in commands."""
    # Common typos and their corrections
    typo_map = {
        "simpann": "simpan",
        "simpann": "simpan",
        "statuss": "status",
        "stauts": "status",
        "stauts": "status",
        "riwayatt": "riwayat",
        "riwayat": "riwayat",
        "cabangg": "cabang",
        "gabungg": "gabung",
        "gabungkan": "gabungkan",
        "bandingkan": "bandingkan",
        "bandingkan": "bandingkan",
        "pulihkan": "pulihkan",
        "batalkan": "batalkan",
        "konfigurasi": "konfigurasi",
        "jelaskan": "jelaskan",
        "mulai": "mulai",
        "mulai": "mulai",
    }
    
    # Check for exact match first
    if word in typo_map:
        return typo_map[word]
    
    # Check for common patterns
    if word.endswith("n") and word[:-1] in VERB_ALIASES:
        return word[:-1]
    if word.endswith("nn") and word[:-2] in VERB_ALIASES:
        return word[:-2]
    
    return word


def _calculate_similarity(s1: str, s2: str) -> float:
    """Calculate similarity between two strings (0-1)."""
    if not s1 or not s2:
        return 0.0
    
    # Simple Levenshtein-like similarity
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # Count matching characters in order
    matches = 0
    j = 0
    for i in range(len1):
        while j < len2 and s2[j] != s1[i]:
            j += 1
        if j < len2:
            matches += 1
            j += 1
    
    return matches / max(len1, len2)


def _find_closest_command(word: str) -> str | None:
    """Find the closest matching command for a typo."""
    all_commands = list(VERB_ALIASES.keys()) + list(SINGLE_WORD_ALIASES.keys())
    
    best_match = None
    best_score = 0.0
    
    for cmd in all_commands:
        score = _calculate_similarity(word, cmd)
        if score > best_score and score > 0.6:  # Threshold for similarity
            best_score = score
            best_match = cmd
    
    return best_match


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
    
    # Apply typo fix
    first_word = _fix_typos(first_word)

    # Check single-word aliases first
    if len(regular_tokens) == 1 and first_word in SINGLE_WORD_ALIASES:
        verb, sub = SINGLE_WORD_ALIASES[first_word]
        cmd.verb = verb
        cmd.subcommand = sub
        return cmd
    
    # If single word not found, try to find similar command
    if len(regular_tokens) == 1 and first_word not in VERB_ALIASES:
        closest = _find_closest_command(first_word)
        if closest:
            # Store suggestion for error handling
            cmd.options["_suggestion"] = closest

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
    elif verb == "kunci":
        _parse_kunci(cmd, regular_tokens[1:])
    elif verb == "bagi":
        _parse_bagi(cmd, regular_tokens[1:])
    elif verb == "jejak":
        _parse_jejak(cmd, regular_tokens[1:])
    elif verb == "folder":
        _parse_folder(cmd, regular_tokens[1:])
    elif verb == "tampilkan":
        _parse_tampilkan(cmd, regular_tokens[1:])
    elif verb == "ringkasan":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "grafik":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "deskripsi":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "catatan":
        _parse_catatan(cmd, regular_tokens[1:])
    elif verb == "verifikasi":
        cmd.subcommand = "tag"
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "bersihkan":
        cmd.flags.append("--gc")
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "kemas":
        cmd.flags.append("--pack")
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "git":
        _parse_git(cmd, regular_tokens[1:])
    elif verb == "klon":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "kirim":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "unduh":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "remote":
        _parse_remote(cmd, regular_tokens[1:])
    elif verb == "hook":
        _parse_hook(cmd, regular_tokens[1:])
    elif verb == "plugin":
        _parse_plugin(cmd, regular_tokens[1:])
    elif verb == "watch":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "completion":
        cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "pindah":
        if regular_tokens[1].value.lower() == "file":
            _parse_pindah_file(cmd, regular_tokens[2:])
        else:
            _parse_pindah(cmd, regular_tokens[1:])
    elif verb == "hapus":
        if regular_tokens[1].value.lower() == "file":
            _parse_hapus_file(cmd, regular_tokens[2:])
        else:
            _parse_hapus(cmd, regular_tokens[1:])
    elif verb == "balikkan":
        _parse_balikkan(cmd, regular_tokens[1:])
    elif verb == "atur":
        if len(regular_tokens) > 1 and regular_tokens[1].value.lower() == "ulang":
            _parse_atur_ulang(cmd, regular_tokens[2:])
        else:
            cmd.args = [t.value for t in regular_tokens[1:]]
    elif verb == "bersihkan":
        if len(regular_tokens) > 1 and regular_tokens[1].value.lower() == "file":
            _parse_bersihkan_file(cmd, regular_tokens[2:])
        else:
            _parse_bersihkan_file(cmd, regular_tokens[1:])
    elif verb == "visual":
        _parse_visual(cmd, regular_tokens[1:])
    elif verb == "suggest":
        _parse_suggest(cmd, regular_tokens[1:])
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


def _parse_kunci(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: kunci file <file> | kunci buka <file> | kunci status <file>"""
    if not tokens:
        cmd.subcommand = "list"
        return

    sub = tokens[0].value.lower()
    sub_map = {
        "file": "file",
        "lock": "file",
        "buka": "buka",
        "unlock": "buka",
        "status": "status",
        "cek": "status",
    }
    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_tampilkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: tampilkan versi [hash] [--stat] [--patch] [--file]"""
    if not tokens:
        cmd.subcommand = "versi"
        return

    sub = tokens[0].value.lower()
    if sub in ("versi", "version", "commit"):
        cmd.subcommand = "versi"
        cmd.args = [t.value for t in tokens[1:]]
    else:
        # Default: assume first arg is hash, rest are flags
        cmd.subcommand = "versi"
        cmd.args = [t.value for t in tokens]


def _parse_catatan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: catatan <commit> [pesan] | catatan lihat/list/hapus/bersih"""
    if not tokens:
        return

    sub = tokens[0].value.lower()
    if sub in ("lihat", "show", "view", "tampilkan"):
        cmd.subcommand = "lihat"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("list", "daftar", "ls"):
        cmd.subcommand = "list"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("hapus", "delete", "remove", "rm"):
        cmd.subcommand = "hapus"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("bersih", "clear", "clean"):
        cmd.subcommand = "bersih"
        cmd.args = [t.value for t in tokens[1:]]
    else:
        # Default: treat as commit hash + message
        cmd.subcommand = "tambah"
        cmd.args = [t.value for t in tokens]


def _parse_git(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: git impor/ekspor [path]"""
    if not tokens:
        cmd.subcommand = "help"
        return

    sub = tokens[0].value.lower()
    if sub in ("impor", "import", "import"):
        cmd.subcommand = "impor"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("ekspor", "export"):
        cmd.subcommand = "ekspor"
        cmd.args = [t.value for t in tokens[1:]]
    elif sub in ("status",):
        cmd.subcommand = "status"
        cmd.args = [t.value for t in tokens[1:]]
    else:
        cmd.subcommand = "help"
        cmd.args = [t.value for t in tokens]


def _parse_remote(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: remote [tambah|hapus|ganti|lihat]"""
    if not tokens:
        return

    sub = tokens[0].value.lower()
    sub_map = {
        "tambah": "tambah",
        "add": "tambah",
        "hapus": "hapus",
        "remove": "hapus",
        "rm": "hapus",
        "ganti": "ganti",
        "set-url": "ganti",
        "update": "ganti",
        "lihat": "lihat",
        "show": "lihat",
        "info": "lihat",
        "rename": "rename",
    }
    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_hook(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: hook [list|install|uninstall|sample]"""
    if not tokens:
        cmd.subcommand = "list"
        return

    sub = tokens[0].value.lower()
    sub_map = {
        "list": "list",
        "ls": "list",
        "install": "install",
        "uninstall": "uninstall",
        "hapus": "uninstall",
        "sample": "sample",
        "contoh": "sample",
    }
    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_plugin(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: plugin [list|install|uninstall|enable|disable]"""
    if not tokens:
        cmd.subcommand = "list"
        return

    sub = tokens[0].value.lower()
    sub_map = {
        "list": "list",
        "ls": "list",
        "install": "install",
        "uninstall": "uninstall",
        "hapus": "uninstall",
        "enable": "enable",
        "aktifkan": "enable",
        "disable": "disable",
        "nonaktifkan": "disable",
        "create": "create",
        "buat": "create",
    }
    cmd.subcommand = sub_map.get(sub, sub)
    cmd.args = [t.value for t in tokens[1:]]


def _parse_pindah_file(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: pindah file <source> <dest>"""
    cmd.args = [t.value for t in tokens]


def _parse_hapus_file(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: hapus file [--cached] <file>"""
    cmd.args = [t.value for t in tokens]


def _parse_balikkan(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: balikkan <commit>"""
    cmd.args = [t.value for t in tokens]


def _parse_atur_ulang(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: atur ulang [--soft|--mixed|--hard] <commit>"""
    cmd.args = [t.value for t in tokens]


def _parse_bersihkan_file(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: bersihkan file [--force]"""
    cmd.args = [t.value for t in tokens]


def _parse_visual(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: visual [file] [--side-by-side]"""
    cmd.args = [t.value for t in tokens]


def _parse_suggest(cmd: ParsedCommand, tokens: list[Token]) -> None:
    """Parse: suggest [commit]"""
    cmd.args = [t.value for t in tokens]
