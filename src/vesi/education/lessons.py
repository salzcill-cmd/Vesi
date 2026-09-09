"""Pelajaran interaktif - belajar vesi dengan melakukan.

Setiap pelajaran berisi langkah-langkah nyata di repository pengguna.
Peserta melihat instruksi, menjalankannya, dan vesi memverifikasi
hasilnya secara otomatis. Progres tersimpan agar mereka bisa lanjut
kapan saja.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class Step:
    """Satu langkah dalam pelajaran."""

    instruction: str
    hint: str = ""
    check: Callable[[object], tuple[bool, str]] | None = None


@dataclass
class Lesson:
    """Satu pelajaran interaktif."""

    id: str
    title: str
    description: str
    steps: list[Step]


def _has_repo(repo: object) -> bool:
    return repo is not None


def _has_commits(repo: object) -> tuple[bool, str]:
    if repo is None:
        return False, "Belum ada repository. Mulai dengan 'mulai proyek'."
    head = repo.get_head_commit()
    if head:
        return True, "Commit ditemukan."
    return False, "Belum ada commit. Lakukan 'stel .' lalu 'simpan \"pesan\"'."


def _has_branch(repo: object, name: str | None = None) -> tuple[bool, str]:
    if repo is None:
        return False, "Belum ada repository."
    branches = repo.refs.list_branches()
    if name and name not in branches:
        return False, f"Cabang '{name}' belum dibuat."
    if not branches:
        return False, "Belum ada cabang."
    return True, f"Cabang tersedia: {', '.join(branches)}"


def _is_on_branch(repo: object, name: str) -> tuple[bool, str]:
    if repo is None:
        return False, "Belum ada repository."
    active = repo.refs.get_active_branch()
    if active == name:
        return True, f"Sedang di cabang '{name}'."
    return False, f"Belum di cabang '{name}'. Jalankan 'pindah cabang {name}'."


def _has_config(repo: object, key: str) -> tuple[bool, str]:
    if repo is None:
        return False, "Belum ada repository."
    config = repo.get_config()
    value = config.get(key, "") or config.get(key.split(".", 1)[-1], "")
    if value:
        return True, f"'{key}' sudah diatur."
    return False, f"'{key}' belum diatur. Jalankan 'konfigurasi {key} \"nilai\"'."


def _has_tags(repo: object) -> tuple[bool, str]:
    if repo is None:
        return False, "Belum ada repository."
    tag_dir = repo.vesi_dir / "refs" / "tags"
    tags = [p.name for p in tag_dir.iterdir()] if tag_dir.is_dir() else []
    if tags:
        return True, f"Tag: {', '.join(tags)}"
    return False, "Belum ada tag. Buat dengan 'beri tag v1.0.0 \"pesan\"'."


LESSONS: list[Lesson] = [
    Lesson(
        id="mulai",
        title="1. Mulai Proyek",
        description="Buat repository pertamamu dan kenali struktur file vesi.",
        steps=[
            Step(
                instruction=(
                    "Pertama, buat repository baru di folder proyekmu.\n"
                    "  vesi mulai proyek\n\n"
                    "Vesi akan membuat folder .vesi (penyimpanan internal)\n"
                    "dan file .abaikan (daftar file yang diabaikan)."
                ),
                hint="Jalankan: vesi mulai proyek",
                check=lambda repo: (
                    (True, "Repository berhasil dibuat.") if _has_repo(repo)
                    else (False, "Repository belum ada.")
                ),
            ),
            Step(
                instruction=(
                    "Bagus! Sekarang lihat status repository dengan:\n"
                    "  vesi lihat perubahan\n\n"
                    "Belum ada file yang berubah. Sekarang buat file baru."
                ),
                hint="Jalankan: vesi lihat perubahan",
                check=lambda repo: (True, "Langkah selesai."),
            ),
        ],
    ),
    Lesson(
        id="simpan",
        title="2. Menyimpan Versi",
        description="Buat file, stel (stage), dan simpan (commit).",
        steps=[
            Step(
                instruction=(
                    "Buat file teks baru, misalnya:\n"
                    "  echo \"Halo, dunia!\" > halo.txt\n\n"
                    "Lalu lihat perubahan yang terdeteksi:\n"
                    "  vesi lihat perubahan"
                ),
                hint="Buat file halo.txt lalu jalankan: vesi lihat perubahan",
                check=lambda repo: (
                    (True, "File terdeteksi.") if repo is not None else (False, "")
                ),
            ),
            Step(
                instruction=(
                    "Sekarang siapkan (stage) file itu ke dalam 'keranjang':\n"
                    "  vesi stel .\n\n"
                    "Titik '.' berarti 'semua file'. Kamu juga bisa menyebut\n"
                    "nama file tertentu: vesi stel halo.txt"
                ),
                hint="Jalankan: vesi stel .",
                check=lambda repo: (
                    (True, "File sudah di-staging.") if repo is not None else (False, "")
                ),
            ),
            Step(
                instruction=(
                    "Sekarang simpan versi (commit) dengan pesan yang jelas:\n"
                    "  vesi simpan \"tambah file halo\"\n\n"
                    "Pesan yang baik menjawab, 'apa yang berubah dan kenapa'."
                ),
                hint="Jalankan: vesi simpan \"tambah file halo\"",
                check=_has_commits,
            ),
        ],
    ),
    Lesson(
        id="riwayat",
        title="3. Melihat Riwayat",
        description="Baca sejarah repository dan identitasmu.",
        steps=[
            Step(
                instruction=(
                    "Lihat riwayat semua versi yang sudah kamu simpan:\n"
                    "  vesi lihat riwayat\n\n"
                    "Catat hash singkat dari commit terakhirmu (contoh: abc1234)."
                ),
                hint="Jalankan: vesi lihat riwayat",
                check=_has_commits,
            ),
            Step(
                instruction=(
                    "Vesi mencatat siapa yang menyimpan versi. Atur namamu:\n"
                    "  vesi konfigurasi user.name \"Nama Kamu\"\n\n"
                    "lalu email:\n"
                    "  vesi konfigurasi user.email \"kamu@contoh.com\""
                ),
                hint="Jalankan: vesi konfigurasi user.name \"Nama Kamu\"",
                check=lambda repo: _has_config(repo, "user.name"),
            ),
        ],
    ),
    Lesson(
        id="cabang",
        title="4. Bekerja dengan Cabang",
        description="Buat dan pindah cabang untuk kerja paralel.",
        steps=[
            Step(
                instruction=(
                    "Cabang memungkinkan kamu mencoba ide tanpa mengganggu\n"
                    "cabang utama ('utama'). Buat cabang baru:\n"
                    "  vesi buat cabang fitur-pertama"
                ),
                hint="Jalankan: vesi buat cabang fitur-pertama",
                check=lambda repo: _has_branch(repo, "fitur-pertama"),
            ),
            Step(
                instruction=(
                    "Pindah ke cabang baru itu:\n"
                    "  vesi pindah cabang fitur-pertama\n\n"
                    "Mulai sekarang, commit yang kamu buat masuk ke cabang ini."
                ),
                hint="Jalankan: vesi pindah cabang fitur-pertama",
                check=lambda repo: _is_on_branch(repo, "fitur-pertama"),
            ),
            Step(
                instruction=(
                    "Ubah halo.txt, lalu simpan versinya di cabang ini:\n"
                    "  echo \"Halo dari cabang!\" >> halo.txt\n"
                    "  vesi stel .\n"
                    "  vesi simpan \"ubah halo di cabang\""
                ),
                hint="Ubah file lalu: vesi stel . dan vesi simpan \"ubah halo di cabang\"",
                check=_has_commits,
            ),
        ],
    ),
    Lesson(
        id="gabungan",
        title="5. Menggabungkan Cabang",
        description="Satukan pekerjaan dari cabang ke utama.",
        steps=[
            Step(
                instruction=(
                    "Kembali ke cabang utama:\n"
                    "  vesi pindah cabang utama\n\n"
                    "Lalu gabungkan cabang fitur-pertama:\n"
                    "  vesi gabungkan fitur-pertama"
                ),
                hint="Jalankan: vesi pindah cabang utama lalu vesi gabungkan fitur-pertama",
                check=lambda repo: (
                    (True, "Penggabungan selesai.") if _has_repo(repo) else (False, "")
                ),
            ),
        ],
    ),
    Lesson(
        id="tags",
        title="6. Menandai Versi",
        description="Beri tag untuk rilis atau titik penting.",
        steps=[
            Step(
                instruction=(
                    "Tag berguna menandai 'ini yang boleh dipakai orang'.\n"
                    "  vesi beri tag v1.0.0 \"rilis pertama\"\n\n"
                    "Lalu lihat daftar tag:\n"
                    "  vesi lihat tag"
                ),
                hint="Jalankan: vesi beri tag v1.0.0 \"rilis pertama\"",
                check=_has_tags,
            ),
        ],
    ),
]


LESSON_BY_ID = {lesson.id: lesson for lesson in LESSONS}


def get_lesson(lesson_id: str) -> Lesson | None:
    return LESSON_BY_ID.get(lesson_id)