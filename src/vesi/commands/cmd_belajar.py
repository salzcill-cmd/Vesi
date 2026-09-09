"""Command: belajar - Tutorial interaktif untuk pemula.

Mode panduan yang memandu pengguna langkah demi langkah sambil
mempraktikkan perintah vesi di repository nyata.
"""

from __future__ import annotations

from vesi.education.tutor import Tutor, find_lesson
from vesi.parser.parser import ParsedCommand
from vesi.utils.platform import print_color


def cmd_belajar(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Interactive learning mode.

    Usage:
      belajar                     - Lihat daftar pelajaran + progres
      belajar <judul>             - Mulai pelajaran tertentu
      belajar --reset             - Hapus semua progres belajar
    """
    from vesi.repository.repository import Repository

    repo = None
    try:
        repo = Repository.find()
    except Exception:
        # Lessons about init don't need a repo yet, but guiding them
        # out of a repo is more useful. Show list anyway.
        pass

    tutor = Tutor(repo)

    if "--reset" in parsed.flags:
        tutor.progress.reset()
        print_color("✓ Progres belajar direset.", "green")
        return 0

    if not parsed.args:
        return tutor.list_lessons()

    lesson = find_lesson(parsed.args[0])
    if lesson is None:
        print_color(f"Pelajaran '{parsed.args[0]}' tidak ditemukan.", "red")
        tutor.list_lessons()
        return 1

    return tutor.start(lesson)