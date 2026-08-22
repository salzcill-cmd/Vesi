"""Vesi exception hierarchy.

All exceptions inherit from VesiError for easy catching.
"""

from __future__ import annotations


class VesiError(Exception):
    """Base exception for all vesi errors."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class RepositoryNotFoundError(VesiError):
    """Raised when no repository is found in the current directory or parents."""

    def __init__(self) -> None:
        super().__init__(
            "Belum ada repository di direktori ini.",
            hint="Mulai repository baru:\n    mulai proyek",
        )


class RepositoryAlreadyExistsError(VesiError):
    """Raised when trying to init a repo in a directory that already has one."""

    def __init__(self) -> None:
        super().__init__(
            "Sudah ada repository di sini. Tidak perlu dibuat lagi.",
        )


class InvalidCommandError(VesiError):
    """Raised when the user types a command that doesn't exist."""

    def __init__(self, command: str, suggestion: str | None = None) -> None:
        msg = f"Command '{command}' tidak dikenal."
        hint = None
        if suggestion:
            hint = f"Mungkin yang kamu maksud:\n    {suggestion}\n\nGunakan bantuan untuk melihat semua command:\n    bantuan"
        else:
            hint = "Lihat semua command:\n    bantuan"
        super().__init__(msg, hint=hint)


class MissingArgumentError(VesiError):
    """Raised when a required argument is not provided."""

    def __init__(self, command: str, expected: str, example: str | None = None) -> None:
        msg = f"Command '{command}' memerlukan {expected}."
        hint = None
        if example:
            hint = f"Contoh:\n    {example}"
        super().__init__(msg, hint=hint)


class NoChangesError(VesiError):
    """Raised when trying to save but there are no changes."""

    def __init__(self) -> None:
        super().__init__(
            "Tidak ada perubahan yang perlu disimpan. File sudah dalam keadaan terakhir yang tersimpan.",
        )


class NoStagedChangesError(VesiError):
    """Raised when trying to commit but nothing is staged."""

    def __init__(self) -> None:
        super().__init__(
            "Belum ada file yang disiapkan. Stel file terlebih dahulu:\n    stel <file>",
        )


class FileNotFoundError(VesiError):
    """Raised when a referenced file doesn't exist."""

    def __init__(self, filename: str) -> None:
        super().__init__(f"File '{filename}' tidak ditemukan.")


class FileNotTrackedError(VesiError):
    """Raised when operating on a file that isn't tracked by the repository."""

    def __init__(self, filename: str) -> None:
        super().__init__(
            f"File '{filename}' belum dilacak oleh repository.",
        )


class VersionNotFoundError(VesiError):
    """Raised when a version/commit ID is not found."""

    def __init__(self, version_id: str) -> None:
        super().__init__(
            f"Versi '{version_id}' tidak ditemukan.",
            hint="Gunakan 'lihat riwayat' untuk melihat versi yang ada.",
        )


class BranchNotFoundError(VesiError):
    """Raised when a branch doesn't exist."""

    def __init__(self, branch_name: str) -> None:
        super().__init__(f"Cabang '{branch_name}' tidak ditemukan.")


class BranchAlreadyExistsError(VesiError):
    """Raised when trying to create a branch that already exists."""

    def __init__(self, branch_name: str) -> None:
        super().__init__(f"Cabang '{branch_name}' sudah ada.")


class CannotDeleteActiveBranchError(VesiError):
    """Raised when trying to delete the currently active branch."""

    def __init__(self, branch_name: str) -> None:
        super().__init__(
            f"Tidak bisa menghapus cabang '{branch_name}' karena sedang aktif.",
            hint="Pindah ke cabang lain terlebih dahulu:\n    pindah cabang <nama-cabang-lain>",
        )


class UnmergedBranchWarning(VesiError):
    """Raised when deleting a branch that hasn't been merged (non-fatal)."""

    def __init__(self, branch_name: str) -> None:
        super().__init__(
            f"Cabang '{branch_name}' belum digabungkan ke cabang manapun.",
            hint="Gunakan 'lihat riwayat' untuk memeriksa, atau lanjutkan dengan '--force'.",
        )


class ConflictError(VesiError):
    """Raised when a merge has conflicts."""

    def __init__(self, files: list[str]) -> None:
        file_list = "\n    ".join(files)
        super().__init__(
            f"Ada konflik di:\n    {file_list}\n\n"
            "Kedua versi mengubah bagian yang sama.\n\n"
            "Perbaiki file tersebut, lalu jalankan:\n"
            "    lanjutkan gabungan\n\n"
            "Atau batalkan:\n"
            "    batalkan gabungan",
        )


class IntegrityError(VesiError):
    """Raised when repository integrity check fails."""

    def __init__(self, details: str) -> None:
        super().__init__(f"Kerusakan repository terdeteksi!\n\n{details}")


class PermissionDeniedError(VesiError):
    """Raised on filesystem permission errors."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"Tidak bisa mengakses: {path}\nAlasan: permission denied.",
            hint="Periksa permissions file/folder.",
        )


class DiskFullError(VesiError):
    """Raised when disk is full."""

    def __init__(self) -> None:
        super().__init__(
            "Tidak bisa menyimpan. Tidak cukup ruang disk.",
            hint="Bersihkan disk space, lalu coba lagi.",
        )


class LockError(VesiError):
    """Raised when another process holds the repository lock."""

    def __init__(self, lock_info: str) -> None:
        super().__init__(
            f"Repository sedang digunakan oleh proses lain.\n    {lock_info}",
            hint="Jika proses sudah tidak berjalan, tunggu atau hapus lock file.",
        )


class ConfigError(VesiError):
    """Raised on configuration issues."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class AbortOperationError(VesiError):
    """Raised when user aborts an operation (Ctrl+C, answering N)."""

    def __init__(self) -> None:
        super().__init__("Operasi dibatalkan.")
