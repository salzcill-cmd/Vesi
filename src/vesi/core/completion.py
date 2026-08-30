"""Shell auto-completion for bash, zsh, and fish.

Provides tab-completion for all vesi commands.
"""

from __future__ import annotations

from pathlib import Path


# All available commands
COMMANDS = [
    "mulai", "status", "stel", "simpan", "riwayat", "bandingkan",
    "pulihkan", "batal", "cabang", "gabungkan", "cek", "konfigurasi",
    "bantuan", "jelaskan", "beri tag", "isi", "cari", "susun ulang",
    "ambil versi", "siapa ubah", "bagi cari", "jejak", "folder kerja",
    "cadangan", "pola commit", "bantu konflik", "statistik", "auto simpan",
    "ekspor", "impor", "alias tambah", "kunci file", "asisten gabung",
    "batalkan versi", "simpan interaktif", "simpan sementara",
    "ambil stash", "lihat stash", "hapus stash",
    "tampilkan versi", "ringkasan", "grafik", "deskripsi",
    "catatan", "remote", "klon", "kirim", "unduh",
    "git impor", "git ekspor",
]

# Command aliases
ALIASES = {
    "status": "lihat perubahan",
    "riwayat": "lihat riwayat",
    "log": "lihat riwayat",
    "cabang": "lihat cabang",
    "branch": "lihat cabang",
    "tag": "lihat tag",
    "help": "bantuan",
    "cek": "cek proyek",
    "add": "stel",
    "stage": "stel",
    "commit": "simpan versi",
    "save": "simpan versi",
    "diff": "bandingkan",
    "restore": "pulihkan",
    "merge": "gabungkan",
    "clone": "klon",
    "push": "kirim",
    "pull": "ambil remote",
    "fetch": "unduh",
    "rebase": "susun ulang",
    "cherry-pick": "ambil versi",
    "blame": "siapa ubah",
    "bisect": "bagi cari",
    "reflog": "jejak",
    "worktree": "folder kerja",
    "stash": "simpan sementara",
    "shortlog": "ringkasan",
    "graph": "grafik",
    "describe": "deskripsi",
    "notes": "catatan",
}

# Subcommands
SUBCOMMANDS = {
    "lihat": ["perubahan", "riwayat", "cabang", "tag", "stash", "file", "cabang detail"],
    "simpan": ["versi", "sementara", "interaktif"],
    "batalkan": ["perubahan", "gabungan", "versi", "semua"],
    "buat": ["cabang"],
    "pindah": ["cabang", "cepat"],
    "hapus": ["cabang", "tag", "stash"],
    "lanjutkan": ["gabungan"],
    "beri": ["tag"],
    "susun": ["ulang", "ke"],
    "ambil": ["stash", "versi"],
    "siapa": ["ubah"],
    "bagi": ["cari", "mulai", "baik", "buruk", "selesai"],
    "cadangan": ["buat", "pulihkan"],
    "pola": ["commit"],
    "bantu": ["konflik"],
    "auto": ["simpan", "aktifkan", "nonaktifkan", "status"],
    "ekspor": ["zip", "git"],
    "impor": ["zip", "git"],
    "alias": ["tambah", "hapus", "list"],
    "kunci": ["file", "buka", "status"],
    "asisten": ["gabung"],
    "kembali": ["ke waktu"],
    "foto": ["otomatis", "lihat", "pulihkan"],
    "pesan": ["pintar"],
    "titik": ["pulih", "buat", "hapus"],
    "tampilkan": ["versi", "commit"],
    "catatan": ["lihat", "list", "hapus", "bersih"],
    "remote": ["tambah", "hapus", "ganti", "lihat", "rename"],
    "git": ["impor", "ekspor", "status"],
}

# Global flags
GLOBAL_FLAGS = [
    "--version", "--help", "--verbose", "--debug", "--json", "--no-color",
]


def generate_bash_completion() -> str:
    """Generate bash completion script."""
    script = """#!/bin/bash
# Vesi bash completion

_vesi_completions() {
    local cur prev commands subcommands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # All commands
    commands="mulai status stel simpan riwayat bandingkan pulihkan batal cabang gabungkan
             cek konfigurasi bantuan jelaskan beri isi cari susun ambil siapa bagi
             jejak folder cadangan pola bantu statistik auto ekspor impor alias kunci
             asisten tampilkan ringkasan grafik deskripsi catatan remote klon kirim unduh git"

    # First word: complete commands
    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
        return 0
    fi

    # Second word: complete subcommands based on first word
    local first="${COMP_WORDS[1]}"
    case "$first" in
        lihat|lhat)
            subcommands="perubahan riwayat cabang tag stash file"
            ;;
        simpan|sv)
            subcommands="versi sementara interaktif"
            ;;
        batalkan|batal)
            subcommands="perubahan gabungan versi semua"
            ;;
        buat)
            subcommands="cabang"
            ;;
        pindah)
            subcommands="cabang cepat"
            ;;
        hapus)
            subcommands="cabang tag stash"
            ;;
        remote)
            subcommands="tambah hapus ganti lihat rename"
            ;;
        git)
            subcommands="impor ekspor status"
            ;;
        *)
            subcommands=""
            ;;
    esac

    if [ -n "$subcommands" ]; then
        COMPREPLY=( $(compgen -W "$subcommands" -- "$cur") )
    fi

    return 0
}

complete -F _vesi_completions vesi
"""
    return script


def generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    script = """#compdef vesi

# Vesi zsh completion

_vesi() {
    local -a commands
    commands=(
        'mulai:Buat repository baru'
        'status:Lihat file yang berubah'
        'stel:Siapkan file untuk commit'
        'simpan:Simpan versi (commit)'
        'riwayat:Lihat daftar versi'
        'bandingkan:Lihat perbedaan'
        'pulihkan:Kembalikan file'
        'batal:Batalkan perubahan'
        'cabang:Lihat cabang'
        'gabungkan:Gabungkan cabang'
        'cek:Periksa integritas'
        'konfigurasi:Kelola pengaturan'
        'bantuan:Tampilkan bantuan'
        'jelaskan: Pelajari konsep'
        'beri:Beri tag'
        'isi:Tampilkan isi file'
        'cari:Cari dalam file'
        'susun:Rebase commits'
        'ambil:Cherry-pick atau stash'
        'siapa:Blame file'
        'bagi:Bisect untuk cari bug'
        'jejak:Lihat reflog'
        'folder:Worktree management'
        'cadangan:Backup system'
        'pola:Pola commit'
        'bantu:Bantuan konflik'
        'statistik:Statistik proyek'
        'auto:Auto-save management'
        'ekspor:Export repository'
        'impor:Import repository'
        'alias:Manage aliases'
        'kunci:File locking'
        'asisten:Merge assistant'
        'tampilkan:Show commit details'
        'ringkasan:Commit summary'
        'grafik:Visual commit graph'
        'deskripsi:Describe current state'
        'catatan:Commit notes'
        'remote:Manage remotes'
        'klon:Clone repository'
        'kirim:Push to remote'
        'unduh:Fetch from remote'
        'git:Git bridge operations'
    )

    _arguments -C \
        '1:command:->command' \
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            local cmd=$words[1]
            case $cmd in
                lihat)
                    _arguments '1:subcommand:(perubahan riwayat cabang tag stash file)'
                    ;;
                simpan)
                    _arguments '1:subcommand:(versi sementara interaktif)'
                    ;;
                batalkan)
                    _arguments '1:subcommand:(perubahan gabungan versi semua)'
                    ;;
                remote)
                    _arguments '1:subcommand:(tambah hapus ganti lihat rename)'
                    ;;
                git)
                    _arguments '1:subcommand:(impor ekspor status)'
                    ;;
            esac
            ;;
    esac
}

_vesi "$@"
"""
    return script


def generate_fish_completion() -> str:
    """Generate fish completion script."""
    script = """# Vesi fish completion

# Commands
complete -c vesi -f -n '__fish_use_subcommand' -a 'mulai' -d 'Buat repository baru'
complete -c vesi -f -n '__fish_use_subcommand' -a 'status' -d 'Lihat file yang berubah'
complete -c vesi -f -n '__fish_use_subcommand' -a 'stel' -d 'Siapkan file'
complete -c vesi -f -n '__fish_use_subcommand' -a 'simpan' -d 'Simpan versi'
complete -c vesi -f -n '__fish_use_subcommand' -a 'riwayat' -d 'Lihat riwayat'
complete -c vesi -f -n '__fish_use_subcommand' -a 'bandingkan' -d 'Lihat perbedaan'
complete -c vesi -f -n '__fish_use_subcommand' -a 'pulihkan' -d 'Kembalikan file'
complete -c vesi -f -n '__fish_use_subcommand' -a 'batal' -d 'Batalkan perubahan'
complete -c vesi -f -n '__fish_use_subcommand' -a 'cabang' -d 'Lihat cabang'
complete -c vesi -f -n '__fish_use_subcommand' -a 'gabungkan' -d 'Gabungkan cabang'
complete -c vesi -f -n '__fish_use_subcommand' -a 'cek' -d 'Periksa integritas'
complete -c vesi -f -n '__fish_use_subcommand' -a 'bantuan' -d 'Tampilkan bantuan'
complete -c vesi -f -n '__fish_use_subcommand' -a 'jelaskan' -d 'Pelajari konsep'
complete -c vesi -f -n '__fish_use_subcommand' -a 'tampilkan' -d 'Tampilkan detail commit'
complete -c vesi -f -n '__fish_use_subcommand' -a 'ringkasan' -d 'Ringkasan commit'
complete -c vesi -f -n '__fish_use_subcommand' -a 'grafik' -d 'Grafik commit'
complete -c vesi -f -n '__fish_use_subcommand' -a 'deskripsi' -d 'Deskripsi state'
complete -c vesi -f -n '__fish_use_subcommand' -a 'catatan' -d 'Catatan commit'
complete -c vesi -f -n '__fish_use_subcommand' -a 'remote' -d 'Manage remotes'
complete -c vesi -f -n '__fish_use_subcommand' -a 'klon' -d 'Clone repository'
complete -c vesi -f -n '__fish_use_subcommand' -a 'kirim' -d 'Push ke remote'
complete -c vesi -f -n '__fish_use_subcommand' -a 'unduh' -d 'Fetch dari remote'
complete -c vesi -f -n '__fish_use_subcommand' -a 'git' -d 'Git bridge'

# Global flags
complete -c vesi -f -l 'version' -d 'Tampilkan versi'
complete -c vesi -f -l 'help' -d 'Tampilkan bantuan'
complete -c vesi -f -l 'verbose' -d 'Output detail'
complete -c vesi -f -l 'debug' -d 'Debug info'
complete -c vesi -f -l 'json' -d 'Output JSON'
complete -c vesi -f -l 'no-color' -d 'Tanpa warna'

# Subcommands for remote
complete -c vesi -f -n '__fish_seen_subcommand_from remote' -a 'tambah' -d 'Tambah remote'
complete -c vesi -f -n '__fish_seen_subcommand_from remote' -a 'hapus' -d 'Hapus remote'
complete -c vesi -f -n '__fish_seen_subcommand_from remote' -a 'ganti' -d 'Ganti URL'
complete -c vesi -f -n '__fish_seen_subcommand_from remote' -a 'lihat' -d 'Lihat detail'

# Subcommands for git
complete -c vesi -f -n '__fish_seen_subcommand_from git' -a 'impor' -d 'Import dari Git'
complete -c vesi -f -n '__fish_seen_subcommand_from git' -a 'ekspor' -d 'Export ke Git'
"""
    return script


def install_completion(shell: str = "bash") -> Path:
    """Install completion script for a shell.

    Args:
        shell: Shell name ("bash", "zsh", or "fish")

    Returns Path to installed script.
    """
    if shell == "bash":
        script = generate_bash_completion()
        config_dir = Path.home() / ".bash_completion.d"
        config_dir.mkdir(exist_ok=True)
        script_path = config_dir / "vesi"
    elif shell == "zsh":
        script = generate_zsh_completion()
        config_dir = Path.home() / ".zsh" / "completions"
        config_dir.mkdir(parents=True, exist_ok=True)
        script_path = config_dir / "_vesi"
    elif shell == "fish":
        script = generate_fish_completion()
        config_dir = Path.home() / ".config" / "fish" / "completions"
        config_dir.mkdir(parents=True, exist_ok=True)
        script_path = config_dir / "vesi.fish"
    else:
        raise ValueError(f"Unsupported shell: {shell}")

    script_path.write_text(script, encoding="utf-8")
    return script_path


def get_completion_help() -> str:
    """Get help text for completion."""
    help_text = """Vesi Shell Completion

Install auto-completion untuk shell kamu:

  Bash:
    source <(vesi --completion bash)
    # Atau install secara permanen:
    vesi --completion install bash

  Zsh:
    source <(vesi --completion zsh)
    # Atau install secara permanen:
    vesi --completion install zsh

  Fish:
    vesi --completion fish > ~/.config/fish/completions/vesi.fish

Setelah install, restart shell atau jalankan:
  bash: source ~/.bash_completion.d/vesi
  zsh: compinit
  fish: . ~/.config/fish/completions/vesi.fish
"""
    return help_text
