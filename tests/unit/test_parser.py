"""Unit tests for command parser."""

from __future__ import annotations

import pytest

from vesi.parser.parser import parse_command, ParsedCommand


class TestSingleWordAliases:
    """Test single-word command aliases."""

    def test_status_alias(self):
        cmd = parse_command("status")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "perubahan"

    def test_riwayat_alias(self):
        cmd = parse_command("riwayat")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"

    def test_log_alias(self):
        cmd = parse_command("log")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"

    def test_history_alias(self):
        cmd = parse_command("history")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"

    def test_cabang_alias(self):
        cmd = parse_command("cabang")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "cabang"

    def test_branch_alias(self):
        cmd = parse_command("branch")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "cabang"

    def test_help_alias(self):
        cmd = parse_command("help")
        assert cmd.verb == "bantuan"
        assert cmd.subcommand == ""

    def test_question_mark_alias(self):
        cmd = parse_command("?")
        assert cmd.verb == "bantuan"
        assert cmd.subcommand == ""

    def test_cek_alias(self):
        cmd = parse_command("cek")
        assert cmd.verb == "cek"
        assert cmd.subcommand == "proyek"

    def test_check_alias(self):
        cmd = parse_command("check")
        assert cmd.verb == "cek"
        assert cmd.subcommand == "proyek"


class TestMulaiProyek:
    """Test mulai proyek command."""

    def test_mulai_only(self):
        cmd = parse_command("mulai")
        assert cmd.verb == "mulai"
        # Note: single word 'mulai' doesn't set subcommand automatically
        # The subcommand is set when there are tokens after 'mulai'

    def test_mulai_proyek(self):
        cmd = parse_command("mulai proyek")
        assert cmd.verb == "mulai"
        assert cmd.subcommand == "proyek"
        assert cmd.args == []

    def test_mulai_proyek_nama(self):
        cmd = parse_command("mulai proyek tugas-math")
        assert cmd.verb == "mulai"
        assert cmd.subcommand == "proyek"
        assert cmd.args == ["tugas-math"]

    def test_mulai_nama_without_proyek(self):
        cmd = parse_command("mulai tugas-math")
        assert cmd.verb == "mulai"
        assert cmd.subcommand == "proyek"
        assert cmd.args == ["tugas-math"]


class TestLihatPerubahan:
    """Test lihat perubahan command."""

    def test_lihat_perubahan(self):
        cmd = parse_command("lihat perubahan")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "perubahan"

    def test_lihat_status_alias(self):
        cmd = parse_command("lihat status")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "perubahan"


class TestLihatRiwayat:
    """Test lihat riwayat command."""

    def test_lihat_riwayat(self):
        cmd = parse_command("lihat riwayat")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"
        assert cmd.args == []

    def test_lihat_riwayat_jumlah(self):
        cmd = parse_command("lihat riwayat 20")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"
        assert cmd.args == ["20"]

    def test_lihat_log_alias(self):
        cmd = parse_command("lihat log")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"

    def test_lihat_history_alias(self):
        cmd = parse_command("lihat history")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"


class TestLihatCabang:
    """Test lihat cabang command."""

    def test_lihat_cabang(self):
        cmd = parse_command("lihat cabang")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "cabang"

    def test_lihat_branch_alias(self):
        cmd = parse_command("lihat branch")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "cabang"


class TestStel:
    """Test stel command."""

    def test_stel_file(self):
        cmd = parse_command("stel main.py")
        assert cmd.verb == "stel"
        assert cmd.args == ["main.py"]

    def test_stel_dot(self):
        cmd = parse_command("stel .")
        assert cmd.verb == "stel"
        assert cmd.args == ["."]

    def test_stel_directory(self):
        cmd = parse_command("stel src/")
        assert cmd.verb == "stel"
        assert cmd.args == ["src/"]

    def test_siap_alias(self):
        cmd = parse_command("siap main.py")
        assert cmd.verb == "stel"
        assert cmd.args == ["main.py"]

    def test_add_alias(self):
        cmd = parse_command("add main.py")
        assert cmd.verb == "stel"
        assert cmd.args == ["main.py"]

    def test_stage_alias(self):
        cmd = parse_command("stage main.py")
        assert cmd.verb == "stel"
        assert cmd.args == ["main.py"]


class TestSimpanVersi:
    """Test simpan versi command."""

    def test_simpan_pesan(self):
        cmd = parse_command('simpan "initial commit"')
        assert cmd.verb == "simpan"
        assert cmd.subcommand == "versi"
        assert cmd.args == ["initial commit"]

    def test_simpan_versi_pesan(self):
        cmd = parse_command('simpan versi "update main"')
        assert cmd.verb == "simpan"
        assert cmd.subcommand == "versi"
        assert cmd.args == ["update main"]

    def test_save_alias(self):
        cmd = parse_command('save "test message"')
        assert cmd.verb == "simpan"
        assert cmd.subcommand == "versi"
        assert cmd.args == ["test message"]

    def test_commit_alias(self):
        cmd = parse_command('commit "test message"')
        assert cmd.verb == "simpan"
        assert cmd.subcommand == "versi"
        assert cmd.args == ["test message"]

    def test_simpan_pesan_without_quotes(self):
        cmd = parse_command("simpan halaman login selesai")
        assert cmd.verb == "simpan"
        assert cmd.subcommand == "versi"
        assert cmd.args == ["halaman login selesai"]


class TestBandingkan:
    """Test bandingkan command."""

    def test_bandingkan(self):
        cmd = parse_command("bandingkan")
        assert cmd.verb == "bandingkan"
        assert cmd.args == []

    def test_bandingkan_versi(self):
        cmd = parse_command("bandingkan a1b2c3d")
        assert cmd.verb == "bandingkan"
        assert cmd.args == ["a1b2c3d"]

    def test_bandingkan_dua_versi(self):
        cmd = parse_command("bandingkan a1b2c3d f4e5d6a")
        assert cmd.verb == "bandingkan"
        assert cmd.args == ["a1b2c3d", "f4e5d6a"]

    def test_diff_alias(self):
        cmd = parse_command("diff")
        assert cmd.verb == "bandingkan"
        assert cmd.args == []


class TestPulihkan:
    """Test pulihkan command."""

    def test_pulihkan_file(self):
        cmd = parse_command("pulihkan main.py")
        assert cmd.verb == "pulihkan"
        assert cmd.args == ["main.py"]

    def test_pulihkan_dari_versi(self):
        cmd = parse_command("pulihkan main.py dari a1b2c3d")
        assert cmd.verb == "pulihkan"
        assert cmd.args == ["main.py"]
        assert cmd.options["from"] == "a1b2c3d"

    def test_pulihkan_from_versi(self):
        cmd = parse_command("pulihkan main.py from a1b2c3d")
        assert cmd.verb == "pulihkan"
        assert cmd.args == ["main.py"]
        assert cmd.options["from"] == "a1b2c3d"

    def test_restore_alias(self):
        cmd = parse_command("restore main.py")
        assert cmd.verb == "pulihkan"
        assert cmd.args == ["main.py"]


class TestBatalkanPerubahan:
    """Test batalkan perubahan command."""

    def test_batalkan_perubahan_file(self):
        cmd = parse_command("batalkan perubahan main.py")
        assert cmd.verb == "batalkan"
        assert cmd.subcommand == "perubahan"
        assert cmd.args == ["main.py"]

    def test_batalkan_file(self):
        cmd = parse_command("batalkan main.py")
        assert cmd.verb == "batalkan"
        assert cmd.subcommand == "perubahan"
        assert cmd.args == ["main.py"]

    def test_batal_file(self):
        cmd = parse_command("batal main.py")
        assert cmd.verb == "batalkan"
        assert cmd.subcommand == "perubahan"
        assert cmd.args == ["main.py"]

    def test_batalkan_gabungan(self):
        cmd = parse_command("batalkan gabungan")
        assert cmd.verb == "batalkan"
        assert cmd.subcommand == "gabungan"

    def test_batalkan_merge(self):
        cmd = parse_command("batalkan merge")
        assert cmd.verb == "batalkan"
        assert cmd.subcommand == "gabungan"


class TestCabangCommands:
    """Test cabang commands (cabang baru, cabang pindah, etc)."""

    def test_cabang_baru(self):
        cmd = parse_command("cabang baru fitur")
        assert cmd.verb == "buat"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_new(self):
        cmd = parse_command("cabang new fitur")
        assert cmd.verb == "buat"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_pindah(self):
        cmd = parse_command("cabang pindah fitur")
        assert cmd.verb == "pindah"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_switch(self):
        cmd = parse_command("cabang switch fitur")
        assert cmd.verb == "pindah"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_hapus(self):
        cmd = parse_command("cabang hapus fitur")
        assert cmd.verb == "hapus"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_delete(self):
        cmd = parse_command("cabang delete fitur")
        assert cmd.verb == "hapus"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_cabang_gabung(self):
        cmd = parse_command("cabang gabung fitur")
        assert cmd.verb == "gabungkan"
        assert cmd.args == ["fitur"]

    def test_cabang_merge(self):
        cmd = parse_command("cabang merge fitur")
        assert cmd.verb == "gabungkan"
        assert cmd.args == ["fitur"]


class TestBuatCabang:
    """Test buat cabang command."""

    def test_buat_cabang(self):
        cmd = parse_command("buat cabang fitur")
        assert cmd.verb == "buat"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_buat_nama_without_cabang(self):
        cmd = parse_command("buat fitur")
        assert cmd.verb == "buat"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_create_alias(self):
        cmd = parse_command("create fitur")
        assert cmd.verb == "buat"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]


class TestPindahCabang:
    """Test pindah cabang command."""

    def test_pindah_cabang(self):
        cmd = parse_command("pindah cabang fitur")
        assert cmd.verb == "pindah"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_pindah_nama_without_cabang(self):
        cmd = parse_command("pindah fitur")
        assert cmd.verb == "pindah"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_switch_alias(self):
        cmd = parse_command("switch fitur")
        assert cmd.verb == "pindah"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]


class TestHapusCabang:
    """Test hapus cabang command."""

    def test_hapus_cabang(self):
        cmd = parse_command("hapus cabang fitur")
        assert cmd.verb == "hapus"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_hapus_nama_without_cabang(self):
        cmd = parse_command("hapus fitur")
        assert cmd.verb == "hapus"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]

    def test_delete_alias(self):
        cmd = parse_command("delete fitur")
        assert cmd.verb == "hapus"
        assert cmd.subcommand == "cabang"
        assert cmd.args == ["fitur"]


class TestGabungkan:
    """Test gabungkan command."""

    def test_gabungkan(self):
        cmd = parse_command("gabungkan fitur")
        assert cmd.verb == "gabungkan"
        assert cmd.args == ["fitur"]

    def test_gabung_alias(self):
        cmd = parse_command("gabung fitur")
        assert cmd.verb == "gabungkan"
        assert cmd.args == ["fitur"]

    def test_merge_alias(self):
        cmd = parse_command("merge fitur")
        assert cmd.verb == "gabungkan"
        assert cmd.args == ["fitur"]


class TestLanjutkanGabungan:
    """Test lanjutkan gabungan command."""

    def test_lanjutkan_gabungan(self):
        cmd = parse_command("lanjutkan gabungan")
        assert cmd.verb == "lanjutkan"
        assert cmd.subcommand == "gabungan"

    def test_lanjutkan_merge(self):
        cmd = parse_command("lanjutkan merge")
        assert cmd.verb == "lanjutkan"
        # Note: 'merge' alias maps to 'gabungan'
        assert cmd.subcommand == "gabungan"


class TestBantuan:
    """Test bantuan command."""

    def test_bantuan(self):
        cmd = parse_command("bantuan")
        assert cmd.verb == "bantuan"
        assert cmd.args == []

    def test_bantuan_command(self):
        cmd = parse_command("bantuan simpan")
        assert cmd.verb == "bantuan"
        assert cmd.args == ["simpan"]

    def test_help_alias(self):
        cmd = parse_command("help")
        assert cmd.verb == "bantuan"


class TestJelaskan:
    """Test jelaskan command."""

    def test_jelaskan(self):
        cmd = parse_command("jelaskan versi")
        assert cmd.verb == "jelaskan"
        assert cmd.args == ["versi"]

    def test_explain_alias(self):
        cmd = parse_command("explain cabang")
        assert cmd.verb == "jelaskan"
        assert cmd.args == ["cabang"]

    def test_apa_alias(self):
        cmd = parse_command("apa merge")
        assert cmd.verb == "jelaskan"
        assert cmd.args == ["merge"]


class TestCek:
    """Test cek command."""

    def test_cek(self):
        cmd = parse_command("cek")
        assert cmd.verb == "cek"
        assert cmd.subcommand == "proyek"

    def test_check_alias(self):
        cmd = parse_command("check")
        assert cmd.verb == "cek"
        assert cmd.subcommand == "proyek"

    def test_verify_alias(self):
        cmd = parse_command("verify")
        assert cmd.verb == "cek"
        assert cmd.subcommand == "proyek"


class TestKonfigurasi:
    """Test konfigurasi command."""

    def test_konfigurasi(self):
        cmd = parse_command("konfigurasi")
        assert cmd.verb == "konfigurasi"
        assert cmd.args == []

    def test_konfigurasi_key(self):
        cmd = parse_command("konfigurasi user.name")
        assert cmd.verb == "konfigurasi"
        assert cmd.args == ["user.name"]

    def test_konfigurasi_key_value(self):
        cmd = parse_command('konfigurasi user.name "Budi"')
        assert cmd.verb == "konfigurasi"
        # Note: quotes are stripped by parser
        assert cmd.args == ["user.name", "Budi"]

    def test_config_alias(self):
        cmd = parse_command("config user.name")
        assert cmd.verb == "konfigurasi"
        assert cmd.args == ["user.name"]


class TestFlags:
    """Test flag extraction."""

    def test_verbose_flag(self):
        cmd = parse_command("status --verbose")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "perubahan"
        assert "--verbose" in cmd.flags

    def test_json_flag(self):
        cmd = parse_command("riwayat --json")
        assert cmd.verb == "lihat"
        assert cmd.subcommand == "riwayat"
        assert "--json" in cmd.flags

    def test_multiple_flags(self):
        cmd = parse_command("cek --verbose --json")
        assert cmd.verb == "cek"
        assert "--verbose" in cmd.flags
        assert "--json" in cmd.flags


class TestEmptyInput:
    """Test empty input handling."""

    def test_empty_string(self):
        cmd = parse_command("")
        assert cmd.verb == ""
        assert cmd.subcommand == ""
        assert cmd.args == []

    def test_whitespace_only(self):
        cmd = parse_command("   ")
        assert cmd.verb == ""
        assert cmd.subcommand == ""


class TestParsedCommandProperties:
    """Test ParsedCommand properties."""

    def test_full_command(self):
        cmd = parse_command("lihat riwayat")
        assert cmd.full_command == "lihat riwayat"

    def test_full_command_with_subcommand(self):
        cmd = parse_command("buat cabang fitur")
        assert cmd.full_command == "buat cabang"

    def test_first_arg(self):
        cmd = parse_command("stel main.py")
        assert cmd.first_arg == "main.py"

    def test_first_arg_none(self):
        cmd = parse_command("status")
        assert cmd.first_arg is None
