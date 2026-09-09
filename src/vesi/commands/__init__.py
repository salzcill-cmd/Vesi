"""Commands module - CLI command handlers."""

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
from vesi.commands.cmd_belajar import cmd_belajar
from vesi.commands.cmd_tag import cmd_beri_tag, cmd_lihat_tag, cmd_hapus_tag, cmd_verify_tag
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
from vesi.commands.cmd_blame import cmd_siapa_ubah
from vesi.commands.cmd_bisect import cmd_bagi_cari
from vesi.commands.cmd_reflog import cmd_jejak
from vesi.commands.cmd_worktree import cmd_folder_kerja
from vesi.commands.cmd_undo import cmd_batalkan_versi
from vesi.commands.cmd_interactive import cmd_simpan_interaktif
from vesi.commands.cmd_stats import cmd_statistik
from vesi.commands.cmd_autosave import cmd_auto_simpan
from vesi.commands.cmd_export import cmd_ekspor, cmd_impor
from vesi.commands.cmd_aliases import cmd_alias
from vesi.commands.cmd_lock import cmd_kunci_file
from vesi.commands.cmd_merge_assistant import cmd_asisten_gabung
from vesi.commands.cmd_search_history import cmd_cari_riwayat
from vesi.commands.cmd_backup import cmd_cadangan
from vesi.commands.cmd_insights import cmd_lihat_file
from vesi.commands.cmd_undo_all import cmd_batalkan_semua
from vesi.commands.cmd_timetravel import cmd_kembali_ke_waktu
from vesi.commands.cmd_quick_switch import cmd_pindah_cepat
from vesi.commands.cmd_autosnapshot import cmd_foto_otomatis
from vesi.commands.cmd_smart_message import cmd_pesan_pintar
from vesi.commands.cmd_branch_preview import cmd_lihat_cabang_detail
from vesi.commands.cmd_version_points import cmd_titik_pulih
from vesi.commands.cmd_template import cmd_pola_commit
from vesi.commands.cmd_smart_diff import cmd_bandingkan_pintar
from vesi.commands.cmd_conflict import cmd_bantu_konflik
from vesi.commands.cmd_revert import cmd_balikkan
from vesi.commands.cmd_mv import cmd_pindah_file
from vesi.commands.cmd_rm import cmd_hapus_file
from vesi.commands.cmd_show_commit import cmd_tampilkan_versi
from vesi.commands.cmd_shortlog import cmd_ringkasan
from vesi.commands.cmd_graph import cmd_grafik
from vesi.commands.cmd_describe import cmd_deskripsi
from vesi.commands.cmd_notes import cmd_catatan
from vesi.commands.cmd_git_import import cmd_impor_git
from vesi.commands.cmd_git_export import cmd_ekspor_git
from vesi.commands.cmd_clone import cmd_klon
from vesi.commands.cmd_push import cmd_kirim
from vesi.commands.cmd_pull import cmd_ambil_remote
from vesi.commands.cmd_fetch import cmd_unduh
from vesi.commands.cmd_remote import cmd_remote

__all__ = [
    "cmd_mulai_proyek",
    "cmd_lihat_perubahan",
    "cmd_stel",
    "cmd_simpan_versi",
    "cmd_lihat_riwayat",
    "cmd_bandingkan",
    "cmd_pulihkan",
    "cmd_batalkan_perubahan",
    "cmd_buat_cabang",
    "cmd_lihat_cabang",
    "cmd_pindah_cabang",
    "cmd_hapus_cabang",
    "cmd_gabungkan",
    "cmd_lanjutkan_gabungan",
    "cmd_batalkan_gabungan",
    "cmd_cek",
    "cmd_konfigurasi",
    "cmd_bantuan",
    "cmd_jelaskan",
    "cmd_belajar",
    "cmd_beri_tag",
    "cmd_lihat_tag",
    "cmd_hapus_tag",
    "cmd_verify_tag",
    "cmd_isi",
    "cmd_cari",
    "cmd_simpan_amend",
    "cmd_simpan_sementara",
    "cmd_ambil_stash",
    "cmd_lihat_stash",
    "cmd_hapus_stash",
    "cmd_ambil_versi",
    "cmd_susun_ulang",
    "cmd_susun_ulang_ke",
    "cmd_siapa_ubah",
    "cmd_bagi_cari",
    "cmd_jejak",
    "cmd_folder_kerja",
    "cmd_batalkan_versi",
    "cmd_simpan_interaktif",
    "cmd_statistik",
    "cmd_auto_simpan",
    "cmd_ekspor",
    "cmd_impor",
    "cmd_alias",
    "cmd_kunci_file",
    "cmd_asisten_gabung",
    "cmd_cari_riwayat",
    "cmd_cadangan",
    "cmd_lihat_file",
    "cmd_batalkan_semua",
    "cmd_kembali_ke_waktu",
    "cmd_pindah_cepat",
    "cmd_foto_otomatis",
    "cmd_pesan_pintar",
    "cmd_lihat_cabang_detail",
    "cmd_titik_pulih",
    "cmd_pola_commit",
    "cmd_bandingkan_pintar",
    "cmd_bantu_konflik",
    "cmd_balikkan",
    "cmd_pindah_file",
    "cmd_hapus_file",
    "cmd_tampilkan_versi",
    "cmd_ringkasan",
    "cmd_grafik",
    "cmd_deskripsi",
    "cmd_catatan",
    "cmd_impor_git",
    "cmd_ekspor_git",
    "cmd_klon",
    "cmd_kirim",
    "cmd_ambil_remote",
    "cmd_unduh",
    "cmd_remote",
]
