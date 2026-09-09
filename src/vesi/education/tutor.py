"""Tutor interaktif - memandu pengguna melalui pelajaran.

Menampilkan satu instruksi tiap kali, lalu menunggu pengguna menekan
Enter sebelum memverifikasi hasilnya. Progres disimpan per repository
di bawah kunci 'education.*' pada ConfigManager.
"""

from __future__ import annotations

import json
from pathlib import Path

from vesi.education.lessons import LESSONS, Lesson, Step, get_lesson
from vesi.utils.platform import print_color


PROGRESS_FILE = "progress.json"


class ProgressStore:
    """Menampilkan dan menyimpan progres belajar pengguna."""

    def __init__(self, vesi_dir: Path | None) -> None:
        self.vesi_dir = vesi_dir

    @property
    def path(self) -> Path | None:
        if not self.vesi_dir:
            return None
        return self.vesi_dir / PROGRESS_FILE

    def load(self) -> dict:
        path = self.path
        if not path or not path.is_file():
            return {"completed": [], "current": None}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**{"completed": [], "current": None}, "current": None, **data}
        except (OSError, json.JSONDecodeError):
            return {"completed": [], "current": None}

    def save(self, data: dict) -> None:
        path = self.path
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def completed_lessons(self) -> list[str]:
        return list(self.load().get("completed", []))

    def current_lesson(self) -> str | None:
        return self.load().get("current")

    def mark_step_done(self, lesson_id: str) -> None:
        data = self.load()
        if lesson_id not in data["completed"]:
            data["completed"].append(lesson_id)
        data["current"] = None
        self.save(data)

    def set_current(self, lesson_id: str) -> None:
        data = self.load()
        data["current"] = lesson_id
        self.save(data)

    def reset(self) -> None:
        self.save({"completed": [], "current": None})


class Tutor:
    """Menjalankan pelajaran langkah demi langkah."""

    def __init__(self, repo: object | None) -> None:
        self.repo = repo
        vesi_dir = getattr(repo, "vesi_dir", None) if repo else None
        self.progress = ProgressStore(vesi_dir)

    def list_lessons(self) -> int:
        done = set(self.progress.completed_lessons())
        print("Pelajaran belajar vesi:\n")
        for lesson in LESSONS:
            marker = "✓" if lesson.id in done else " "
            print(f"  [{marker}] {lesson.title}")
            print(f"        {lesson.description}")
        print("\n  Jalankan: vesi belajar <judul>")
        print("  Contoh:   vesi belajar simpan")
        return 0

    def start(self, lesson: Lesson) -> int:
        done = set(self.progress.completed_lessons())
        self.progress.set_current(lesson.id)

        print_color(f"Pelajaran: {lesson.title}", "cyan")
        print_color('─' * min(60, len(lesson.title) + 12), "cyan")
        print(f"{lesson.description}\n")
        if lesson.id in done:
            print_color("⚠ Kamu sudah menyelesaikan pelajaran ini.", "yellow")

        for idx, step in enumerate(lesson.steps, 1):
            print_color(f"\n[Langkah {idx}/{len(lesson.steps)}]", "bold")
            print(step.instruction)
            if step.hint:
                print_color(f"  Tip: {step.hint}", "yellow")

            entered = self._wait_for_enter()
            if entered in ("q", "x", "keluar"):
                print("\nPelajaran dihentikan. Jalankan 'vesi belajar' untuk lanjut.")
                self.progress.set_current(lesson.id)
                return 0

            if step.check:
                ok, message = step.check(self.repo)
                if ok:
                    print_color(f"  ✓ {message}", "green")
                else:
                    print_color(f"  ✗ {message}", "red")
                    print("  Jalankan instruksi di atas, lalu tekan Enter lagi.")

        self.progress.mark_step_done(lesson.id)
        print_color("\n🎉 Pelajaran selesai! Progres tersimpan.", "green")
        print("  Lanjutkan dengan 'vesi belajar' untuk melihat daftar.")
        return 0

    @staticmethod
    def _wait_for_enter() -> str:
        """Menunggu input pengguna. q/x/keluar menghentikan pelajaran."""
        try:
            return input("  [Enter] lanjut · [q] berhenti > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q"


def find_lesson(keyword: str) -> Lesson | None:
    """Menemukan pelajaran dari keyword (id, judul, atau sebagian)."""
    keyword = keyword.lower().strip()

    lesson = get_lesson(keyword)
    if lesson:
        return lesson

    for lesson in LESSONS:
        if keyword in lesson.title.lower():
            return lesson
        if keyword in lesson.description.lower():
            return lesson
    return None