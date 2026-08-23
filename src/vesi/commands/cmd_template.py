"""Command: pola commit - Commit message templates."""

from __future__ import annotations

from vesi.errors.exceptions import (
    RepositoryNotFoundError,
    VesiError,
)
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository
from vesi.utils.platform import print_color


# Commit message templates
TEMPLATES = {
    "feat": {
        "name": "Fitur Baru",
        "template": "feat: <deskripsi fitur>",
        "example": "feat: tambah halaman login",
        "description": "Untuk fitur baru yang ditambahkan",
    },
    "fix": {
        "name": "Perbaikan Bug",
        "template": "fix: <deskripsi fix>",
        "example": "fix: perbaikan error saat login",
        "description": "Untuk perbaikan bug",
    },
    "docs": {
        "name": "Dokumentasi",
        "template": "docs: <deskripsi dokumentasi>",
        "example": "docs: update README",
        "description": "Untuk perubahan dokumentasi",
    },
    "style": {
        "name": "Style/Format",
        "template": "style: <deskripsi style>",
        "example": "style: format kode",
        "description": "Untuk perubahan format/style",
    },
    "refactor": {
        "name": "Refactor",
        "template": "refactor: <deskripsi refactor>",
        "example": "refactor: optimize database query",
        "description": "Untuk refactor kode",
    },
    "test": {
        "name": "Test",
        "template": "test: <deskripsi test>",
        "example": "test: tambah unit test login",
        "description": "Untuk penambahan/pengubahan test",
    },
    "chore": {
        "name": "Maintenance",
        "template": "chore: <deskripsi maintenance>",
        "example": "chore: update dependencies",
        "description": "Untuk maintenance/chores",
    },
    "breaking": {
        "name": "Breaking Change",
        "template": "!: <deskripsi breaking change>",
        "example": "!: ubah format API v2",
        "description": "Untuk perubahan yang tidak backward compatible",
    },
}


def cmd_pola_commit(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Commit templates.

    Usage:
      pola commit              - List all templates
      pola commit <type>       - Show template example
      pola commit <type> <desc> - Generate commit message
    """
    args = parsed.args or []

    if not args:
        # List all templates
        print_color("📋 Pola Commit (Commit Templates):\n", "cyan")
        print("  Gunakan pola ini untuk pesan commit yang konsisten:\n")

        for key, tmpl in TEMPLATES.items():
            print(f"  {key:<12} {tmpl['name']:<20} {tmpl['description']}")
            if verbose:
                print(f"             Contoh: {tmpl['example']}")
                print()

        print("\n  Contoh penggunaan:")
        print("    vesi pola commit feat")
        print('    vesi pola commit feat "tambah halaman login"')
        print('    vesi pola commit fix "perbaikan error 500"')
        return 0

    # Get template type
    template_type = args[0].lower()

    if template_type not in TEMPLATES:
        print_color(f"❌ Pola '{template_type}' tidak ditemukan.\n", "red")
        print("Pola yang tersedia:")
        for key in TEMPLATES:
            print(f"  - {key}")
        return 1

    tmpl = TEMPLATES[template_type]

    if len(args) == 1:
        # Show template example
        print_color(f"📋 Pola: {tmpl['name']}\n", "cyan")
        print(f"  Template:  {tmpl['template']}")
        print(f"  Contoh:    {tmpl['example']}")
        print(f"  Gunakan:   {tmpl['description']}")

        print(f"\n  ✍️  Generate commit message:")
        print(f'    vesi pola commit {template_type} "deskripsi kamu"')
    else:
        # Generate commit message
        description = " ".join(args[1:])
        commit_msg = f"{template_type}: {description}"

        print_color(f"✅ Pesan commit yang dihasilkan:\n", "green")
        print(f"  \"{commit_msg}\"")

        print(f"\n  💡 Langkah selanjutnya:")
        print(f"    1. vesi stel .")
        print(f'    2. vesi simpan "{commit_msg}"')

    return 0
