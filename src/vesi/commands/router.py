"""Command router - dispatch parsed commands to handlers."""

from __future__ import annotations

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
from vesi.commands.cmd_tag import cmd_beri_tag, cmd_lihat_tag, cmd_hapus_tag
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
from vesi.commands.cmd_stash import cmd_stash_branch, cmd_stash_show
from vesi.commands.cmd_git_import import cmd_impor_git
from vesi.commands.cmd_git_export import cmd_ekspor_git
from vesi.commands.cmd_clone import cmd_klon
from vesi.commands.cmd_push import cmd_kirim
from vesi.commands.cmd_pull import cmd_ambil_remote
from vesi.commands.cmd_fetch import cmd_unduh
from vesi.commands.cmd_remote import cmd_remote
from vesi.errors.exceptions import InvalidCommandError
from vesi.parser.parser import ParsedCommand


def cmd_hook_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle hook management commands."""
    from vesi.core.hooks import HookManager
    from vesi.utils.platform import print_color

    try:
        from vesi.repository.repository import Repository
        repo = Repository.find()
        hook_mgr = HookManager(repo.root)
    except Exception:
        from vesi.utils.platform import print_color
        print_color("Tidak ada repository.", "red")
        return 1

    sub = parsed.subcommand or "list"

    if sub == "list":
        hooks = hook_mgr.list_hooks()
        print_color("Hooks:\n", "cyan")
        for hook_type, installed in hooks.items():
            status = "✓" if installed else " "
            print(f"  [{status}] {hook_type}")
        return 0

    elif sub == "sample":
        created = hook_mgr.create_sample_hooks()
        print_color(f"✓ {len(created)} sample hooks dibuat!", "green")
        for p in created:
            print(f"  {p.name}")
        return 0

    elif sub == "install":
        if not parsed.args:
            print("Usage: hook install <type> <script>")
            return 1
        hook_type = parsed.args[0]
        script = parsed.args[1] if len(parsed.args) > 1 else "#!/bin/bash\necho Hook"
        hook_mgr.install_hook(hook_type, script)
        print_color(f"✓ Hook '{hook_type}' terinstall!", "green")
        return 0

    elif sub == "uninstall":
        if not parsed.args:
            print("Usage: hook uninstall <type>")
            return 1
        hook_type = parsed.args[0]
        if hook_mgr.uninstall_hook(hook_type):
            print_color(f"✓ Hook '{hook_type}' dihapus.", "green")
        else:
            print(f"Hook '{hook_type}' tidak ditemukan.")
        return 0

    else:
        print(hook_mgr.get_hook_help())
        return 0


def cmd_plugin_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle plugin management commands."""
    from vesi.core.plugin import PluginManager, create_plugin_template
    from vesi.utils.platform import print_color

    plugin_mgr = PluginManager()
    sub = parsed.subcommand or "list"

    if sub == "list":
        plugins = plugin_mgr.list_plugins()
        if not plugins:
            print("Tidak ada plugin terinstall.")
            print("\nBuat plugin baru:")
            print("  vesi plugin buat my-plugin")
            return 0

        print_color(f"Plugin ({len(plugins)}):\n", "cyan")
        for p in plugins:
            status = "✓" if p.enabled else "✗"
            print(f"  [{status}] {p.name} v{p.version}")
            if p.description:
                print(f"      {p.description}")
        return 0

    elif sub in ("create", "buat"):
        if not parsed.args:
            print("Usage: plugin buat <nama>")
            return 1
        name = parsed.args[0]
        path = create_plugin_template(name)
        print_color(f"✓ Plugin template dibuat!", "green")
        print(f"  Lokasi: {path}")
        print(f"\n  Edit {path}/main.py untuk mengembangkan plugin.")
        return 0

    elif sub == "install":
        if not parsed.args:
            print("Usage: plugin install <path>")
            return 1
        from pathlib import Path
        path = Path(parsed.args[0])
        info = plugin_mgr.install_plugin(path)
        if info:
            print_color(f"✓ Plugin '{info.name}' terinstall!", "green")
        else:
            print_color("Gagal install plugin.", "red")
        return 0

    elif sub == "uninstall":
        if not parsed.args:
            print("Usage: plugin uninstall <nama>")
            return 1
        name = parsed.args[0]
        if plugin_mgr.uninstall_plugin(name):
            print_color(f"✓ Plugin '{name}' dihapus.", "green")
        else:
            print(f"Plugin '{name}' tidak ditemukan.")
        return 0

    elif sub in ("enable", "aktifkan"):
        if not parsed.args:
            print("Usage: plugin aktifkan <nama>")
            return 1
        name = parsed.args[0]
        if plugin_mgr.enable_plugin(name):
            print_color(f"✓ Plugin '{name}' diaktifkan.", "green")
        return 0

    elif sub in ("disable", "nonaktifkan"):
        if not parsed.args:
            print("Usage: plugin nonaktifkan <nama>")
            return 1
        name = parsed.args[0]
        if plugin_mgr.disable_plugin(name):
            print_color(f"✓ Plugin '{name}' dinonaktifkan.", "green")
        return 0

    return 0


def cmd_watch_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle file watch commands."""
    from vesi.core.watch import AutoSaveManager
    from vesi.utils.platform import print_color

    try:
        from vesi.repository.repository import Repository
        repo = Repository.find()
    except Exception:
        print_color("Tidak ada repository.", "red")
        return 1

    watch_mgr = AutoSaveManager(repo.root)
    args = parsed.args or []

    if not args or args[0] == "status":
        status = watch_mgr.get_status()
        print_color("Watch Status:\n", "cyan")
        print(f"  Enabled:    {'✓' if status['enabled'] else '✗'}")
        print(f"  Interval:   {status['interval_human']}")
        print(f"  Auto-commit: {'✓' if status['auto_commit'] else '✗'}")
        return 0

    elif args[0] == "aktifkan" or args[0] == "enable":
        interval = int(args[1]) if len(args) > 1 else 300
        watch_mgr.enable(interval)
        print_color(f"✓ Watch diaktifkan (setiap {interval//60} menit)", "green")
        return 0

    elif args[0] == "nonaktifkan" or args[0] == "disable":
        watch_mgr.disable()
        print_color("✓ Watch dinonaktifkan.", "green")
        return 0

    return 0


def cmd_pindah_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle pindah command - dispatch to file or cabang."""
    from vesi.commands.cmd_mv import cmd_pindah_file
    from vesi.commands.cmd_branch import cmd_pindah_cabang

    # Check if it's 'pindah file' or 'pindah cabang'
    if parsed.args and parsed.args[0].lower() == "file":
        # Remove 'file' from args
        new_parsed = ParsedCommand(
            verb=parsed.verb,
            subcommand="file",
            args=parsed.args[1:],
            flags=parsed.flags,
        )
        return cmd_pindah_file(new_parsed, verbose=verbose, debug=debug)
    else:
        # Default to branch
        return cmd_pindah_cabang(parsed, verbose=verbose, debug=debug)


def cmd_atur_ulang_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle atur ulang command."""
    from vesi.commands.cmd_reset import cmd_atur_ulang
    return cmd_atur_ulang(parsed, verbose=verbose, debug=debug)


def cmd_bersihkan_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle bersihkan command."""
    from vesi.commands.cmd_clean import cmd_bersihkan
    return cmd_bersihkan(parsed, verbose=verbose, debug=debug)


def cmd_visual_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle visual diff command."""
    from vesi.core.visual_diff import VisualDiff
    from vesi.utils.platform import print_color

    try:
        from vesi.repository.repository import Repository
        repo = Repository.find()
    except Exception:
        print_color("Tidak ada repository.", "red")
        return 1

    args = parsed.args or []
    side_by_side = "--side-by-side" in parsed.flags
    mode = "side-by-side" if side_by_side else "unified"

    if not args:
        # Show diff of working directory
        print_color("Visual diff:\n", "cyan")
        print("Gunakan: visual <file> atau visual --side-by-side <file>")
        return 0

    filepath = args[0]
    file_path = repo.root / filepath

    if not file_path.is_file():
        print_color(f"File '{filepath}' tidak ditemukan.", "red")
        return 1

    # Get current content
    current_content = file_path.read_text(encoding="utf-8", errors="replace")

    # Get staged/HEAD content
    head_hash = repo.get_head_commit()
    old_content = ""
    if head_hash:
        from vesi.core.snapshot import SnapshotManager
        snapshot_mgr = SnapshotManager(repo)
        try:
            tree = snapshot_mgr.get_tree(head_hash)
            entry = tree.get_entry(filepath)
            if entry:
                old_content = repo.blobs.load_content(entry.hash_id).decode("utf-8", errors="replace")
        except Exception:
            pass

    differ = VisualDiff(use_color=True)

    if side_by_side:
        result = differ.side_by_side(old_content, current_content, f"HEAD/{filepath}", f"working/{filepath}")
    else:
        result = differ.unified(old_content, current_content, f"HEAD/{filepath}", f"working/{filepath}")

    print(result)
    return 0


def cmd_suggest_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle suggest commit command."""
    from vesi.core.smart_commit import generate_commit_suggestions
    from vesi.utils.platform import print_color

    try:
        from vesi.repository.repository import Repository
        repo = Repository.find()
    except Exception:
        print_color("Tidak ada repository.", "red")
        return 1

    # Get changed files
    from vesi.core.change import detect_changes
    from vesi.core.snapshot import SnapshotManager

    snapshot_mgr = SnapshotManager(repo)
    index = repo.index.load()
    head_hash = repo.get_head_commit()

    tree = None
    if head_hash:
        try:
            tree = snapshot_mgr.get_tree(head_hash)
        except Exception:
            pass

    changes = detect_changes(repo.root, tree, index or {})
    changed_files = [c.path for c in changes]

    if not changed_files:
        print_color("Tidak ada perubahan untuk di-suggest.", "yellow")
        return 0

    # Get diff content
    diff_content = ""
    for change in changes:
        if change.new_hash:
            try:
                file_path = repo.root / change.path
                if file_path.is_file():
                    diff_content += file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

    # Generate suggestions
    suggestions = generate_commit_suggestions(changed_files, diff_content)

    print_color("💡 Saran commit message:\n", "cyan")
    for i, s in enumerate(suggestions, 1):
        confidence_bar = "█" * int(s.confidence * 10)
        print(f"  {i}. {s.message}")
        print(f"     {s.description}")
        print(f"     Confidence: {confidence_bar} ({s.confidence:.0%})")
        print()

    print("Gunakan salah satu:")
    print(f'  vesi simpan "{suggestions[0].message}"')
    return 0


def cmd_completion_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle completion commands."""
    from vesi.core.completion import (
        generate_bash_completion, generate_zsh_completion,
        generate_fish_completion, install_completion, get_completion_help,
    )
    from vesi.utils.platform import print_color

    args = parsed.args or []

    if not args:
        print(get_completion_help())
        return 0

    shell = args[0]

    if shell == "install" and len(args) > 1:
        target_shell = args[1]
        path = install_completion(target_shell)
        print_color(f"✓ Completion terinstall untuk {target_shell}!", "green")
        print(f"  Lokasi: {path}")
        return 0

    if shell == "bash":
        print(generate_bash_completion())
    elif shell == "zsh":
        print(generate_zsh_completion())
    elif shell == "fish":
        print(generate_fish_completion())
    else:
        print(f"Shell '{shell}' tidak didukung.")
        print("Gunakan: bash, zsh, atau fish")
        return 1

    return 0


def cmd_git_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'git' command - dispatch to import/export."""
    if parsed.subcommand == "impor":
        return cmd_impor_git(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "ekspor":
        return cmd_ekspor_git(parsed, verbose=verbose, debug=debug)
    else:
        # Show git bridge help
        from vesi.utils.platform import print_color
        print_color("Bridger Git ↔ Vesi\n", "cyan")
        print("  Impor repository Git ke format Vesi:")
        print("    git impor [path]        Import .git ke .vesi")
        print("    git impor --branches    Import semua branch")
        print()
        print("  Ekspor repository Vesi ke format Git:")
        print("    git ekspor [path]       Export .vesi ke .git")
        print("    git ekspor --all        Export semua branch")
        print("    git ekspor --bare       Export sebagai bare repo")
        return 0


def cmd_beri(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'beri tag' command."""
    if parsed.subcommand == "tag":
        return cmd_beri_tag(parsed, verbose=verbose, debug=debug)
    return cmd_beri_tag(parsed, verbose=verbose, debug=debug)


def cmd_ambil_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'ambil' command - dispatch to stash or cherry-pick."""
    if parsed.subcommand == "stash":
        return cmd_ambil_stash(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "versi":
        return cmd_ambil_versi(parsed, verbose=verbose, debug=debug)
    else:
        # Default to cherry-pick
        return cmd_ambil_versi(parsed, verbose=verbose, debug=debug)


def cmd_bagi_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'bagi' command - dispatch to bisect."""
    return cmd_bagi_cari(parsed, verbose=verbose, debug=debug)


def cmd_folder_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'folder' command - dispatch to worktree."""
    return cmd_folder_kerja(parsed, verbose=verbose, debug=debug)


def cmd_pola_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'pola' command - dispatch to commit templates."""
    return cmd_pola_commit(parsed, verbose=verbose, debug=debug)


def cmd_bantu_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'bantu' command - dispatch to conflict helper."""
    return cmd_bantu_konflik(parsed, verbose=verbose, debug=debug)


def cmd_simpan_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle simpan command with --amend flag."""
    if "--amend" in parsed.flags:
        return cmd_simpan_amend(parsed, verbose=verbose, debug=debug)
    return cmd_simpan_versi(parsed, verbose=verbose, debug=debug)


def cmd_batalkan_semua_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'batalkan' command for 'batalkan semua'."""
    if parsed.subcommand == "semua":
        return cmd_batalkan_semua(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "versi":
        return cmd_batalkan_versi(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "perubahan":
        return cmd_batalkan_perubahan(parsed, verbose=verbose, debug=debug)
    elif parsed.subcommand == "gabungan":
        return cmd_batalkan_gabungan(parsed, verbose=verbose, debug=debug)
    else:
        return cmd_batalkan_perubahan(parsed, verbose=verbose, debug=debug)


def cmd_kembali_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'kembali' command for 'kembali ke waktu'."""
    if parsed.subcommand == "ke waktu":
        return cmd_kembali_ke_waktu(parsed, verbose=verbose, debug=debug)
    else:
        return cmd_kembali_ke_waktu(parsed, verbose=verbose, debug=debug)


def cmd_pindah_cepat_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle 'pindah' command for 'pindah cepat'."""
    if parsed.subcommand == "cepat":
        return cmd_pindah_cepat(parsed, verbose=verbose, debug=debug)
    else:
        return cmd_pindah_cabang(parsed, verbose=verbose, debug=debug)


def cmd_rerere_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle rerere commands."""
    from vesi.commands.cmd_rerere import cmd_rerere
    return cmd_rerere(parsed, verbose=verbose, debug=debug)


def cmd_sebagian_handler(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Handle sparse checkout commands."""
    from vesi.commands.cmd_sparse import cmd_sebagian
    return cmd_sebagian(parsed, verbose=verbose, debug=debug)


# Map of verb -> handler function (for simple commands)
COMMANDS: dict[str, callable] = {
    "mulai": cmd_mulai_proyek,
    "stel": cmd_stel,
    "simpan": cmd_simpan_handler,
    "bandingkan": cmd_bandingkan,
    "pulihkan": cmd_pulihkan,
    "cek": cmd_cek,
    "konfigurasi": cmd_konfigurasi,
    "bantuan": cmd_bantuan,
    "jelaskan": cmd_jelaskan,
    "gabungkan": cmd_gabungkan,
    "beri": cmd_beri,
    "isi": cmd_isi,
    "cari": cmd_cari,
    "susun": cmd_susun_ulang,
    "ambil": cmd_ambil_handler,
    "siapa": cmd_siapa_ubah,
    "bagi": cmd_bagi_handler,
    "jejak": cmd_jejak,
    "folder": cmd_folder_handler,
    "cadangan": cmd_cadangan,
    "pola": cmd_pola_handler,
    "bantu": cmd_bantu_handler,
    "statistik": cmd_statistik,
    "auto": cmd_auto_simpan,
    "ekspor": cmd_ekspor,
    "impor": cmd_impor,
    "alias": cmd_alias,
    "kunci": cmd_kunci_file,
    "asisten": cmd_asisten_gabung,
    "batalkan": cmd_batalkan_semua_handler,
    "kembali": cmd_kembali_handler,
    "pindah": cmd_pindah_cepat_handler,
    "foto": cmd_foto_otomatis,
    "pesan": cmd_pesan_pintar,
    "titik": cmd_titik_pulih,
    # New upgraded commands
    "tampilkan": cmd_tampilkan_versi,
    "ringkasan": cmd_ringkasan,
    "grafik": cmd_grafik,
    "deskripsi": cmd_deskripsi,
    "catatan": cmd_catatan,
    # Git bridge
    "git": cmd_git_handler,
    # Remote operations
    "klon": cmd_klon,
    "kirim": cmd_kirim,
    "unduh": cmd_unduh,
    "remote": cmd_remote,
    # Advanced features
    "hook": cmd_hook_handler,
    "plugin": cmd_plugin_handler,
    "watch": cmd_watch_handler,
    "completion": cmd_completion_handler,
    # New vesi-exclusive commands
    "pindah": cmd_pindah_handler,
    "balikkan": cmd_balikkan,
    "atur": cmd_atur_ulang_handler,
    "bersihkan": cmd_bersihkan_handler,
    "visual": cmd_visual_handler,
    "suggest": cmd_suggest_handler,
    # Rerere
    "ulang": cmd_rerere_handler,
    # Sparse checkout
    "sebagian": cmd_sebagian_handler,
}

# Map of verb+subcommand -> handler function
SUBCOMMANDS: dict[tuple[str, str], callable] = {
    ("lihat", "perubahan"): cmd_lihat_perubahan,
    ("lihat", "riwayat"): cmd_lihat_riwayat,
    ("lihat", "cabang"): cmd_lihat_cabang,
    ("lihat", "tag"): cmd_lihat_tag,
    ("lihat", "stash"): cmd_lihat_stash,
    ("buat", "cabang"): cmd_buat_cabang,
    ("pindah", "cabang"): cmd_pindah_cabang,
    ("hapus", "cabang"): cmd_hapus_cabang,
    ("hapus", "tag"): cmd_hapus_tag,
    ("hapus", "stash"): cmd_hapus_stash,
    ("batalkan", "perubahan"): cmd_batalkan_perubahan,
    ("batalkan", "gabungan"): cmd_batalkan_gabungan,
    ("lanjutkan", "gabungan"): cmd_lanjutkan_gabungan,
    ("susun", "ulang"): cmd_susun_ulang,
    ("susun", "ke"): cmd_susun_ulang_ke,
    ("ambil", "stash"): cmd_ambil_stash,
    ("ambil", "versi"): cmd_ambil_versi,
    ("simpan", "sementara"): cmd_simpan_sementara,
    ("batalkan", "versi"): cmd_batalkan_versi,
    ("lihat", "file"): cmd_lihat_file,
    ("bandingkan", "pintar"): cmd_bandingkan_pintar,
    ("cari", "riwayat"): cmd_cari_riwayat,
    ("siapa", "ubah"): cmd_siapa_ubah,
    ("bagi", "cari"): cmd_bagi_cari,
    ("bagi", "mulai"): cmd_bagi_cari,
    ("bagi", "baik"): cmd_bagi_cari,
    ("bagi", "buruk"): cmd_bagi_cari,
    ("bagi", "selesai"): cmd_bagi_cari,
    ("folder", "kerja"): cmd_folder_kerja,
    ("folder", "buat"): cmd_folder_kerja,
    ("folder", "hapus"): cmd_folder_kerja,
    ("folder", "list"): cmd_folder_kerja,
    # New advanced commands
    ("simpan", "interaktif"): cmd_simpan_interaktif,
    ("simpan", "wizard"): cmd_simpan_interaktif,
    ("auto", "simpan"): cmd_auto_simpan,
    ("auto", "aktifkan"): cmd_auto_simpan,
    ("auto", "nonaktifkan"): cmd_auto_simpan,
    ("auto", "status"): cmd_auto_simpan,
    ("alias", "tambah"): cmd_alias,
    ("alias", "hapus"): cmd_alias,
    ("alias", "list"): cmd_alias,
    ("kunci", "file"): cmd_kunci_file,
    ("kunci", "buka"): cmd_kunci_file,
    ("kunci", "status"): cmd_kunci_file,
    ("asisten", "gabung"): cmd_asisten_gabung,
    # Latest features
    ("batalkan", "semua"): cmd_batalkan_semua,
    ("kembali", "ke waktu"): cmd_kembali_ke_waktu,
    ("pindah", "cepat"): cmd_pindah_cepat,
    ("foto", "otomatis"): cmd_foto_otomatis,
    ("foto", "lihat"): cmd_foto_otomatis,
    ("foto", "pulihkan"): cmd_foto_otomatis,
    ("pesan", "pintar"): cmd_pesan_pintar,
    ("lihat", "cabang detail"): cmd_lihat_cabang_detail,
    ("lihat", "cabang bandingkan"): cmd_lihat_cabang_detail,
    ("titik", "pulih"): cmd_titik_pulih,
    ("titik", "buat"): cmd_titik_pulih,
    ("titik", "hapus"): cmd_titik_pulih,
    # New upgraded commands
    ("tampilkan", "versi"): cmd_tampilkan_versi,
    ("tampilkan", "commit"): cmd_tampilkan_versi,
    # Notes
    ("catatan", "tambah"): cmd_catatan,
    ("catatan", "lihat"): cmd_catatan,
    ("catatan", "list"): cmd_catatan,
    ("catatan", "hapus"): cmd_catatan,
    ("catatan", "bersih"): cmd_catatan,
    # Tag verify
    ("verifikasi", "tag"): cmd_catatan,
    # Git bridge
    ("git", "impor"): cmd_impor_git,
    ("git", "import"): cmd_impor_git,
    ("git", "ekspor"): cmd_ekspor_git,
    ("git", "export"): cmd_ekspor_git,
    ("git", "status"): cmd_git_handler,
    # Remote operations
    ("remote", "tambah"): cmd_remote,
    ("remote", "hapus"): cmd_remote,
    ("remote", "ganti"): cmd_remote,
    ("remote", "lihat"): cmd_remote,
    ("remote", "rename"): cmd_remote,
}

# Suggestion map for similar commands
SUGGESTIONS: dict[str, str] = {
    "mulai": "mulai proyek",
    "init": "mulai proyek",
    "status": "lihat perubahan",
    "add": "stel",
    "stage": "stel",
    "commit": "simpan versi",
    "save": "simpan versi",
    "log": "lihat riwayat",
    "history": "lihat riwayat",
    "riwayat": "lihat riwayat",
    "diff": "bandingkan",
    "restore": "pulihkan",
    "checkout": "pindah cabang",
    "branch": "lihat cabang",
    "cabang": "lihat cabang",
    "tag": "lihat tag",
    "merge": "gabungkan",
    "gabung": "gabungkan",
    "help": "bantuan",
    "explain": "jelaskan",
    "check": "cek",
    "config": "konfigurasi",
    "show": "isi",
    "cat": "isi",
    "search": "cari",
    "grep": "cari",
    "find": "cari",
    # Stash commands
    "stash": "simpan sementara",
    "sementara": "simpan sementara",
    "pop": "ambil stash",
    # Rebase commands
    "rebase": "susun ulang",
    "squash": "susun ulang",
    # Cherry-pick
    "cherry-pick": "ambil versi",
    "pick": "ambil versi",
    # Blame
    "blame": "siapa ubah",
    "annotate": "siapa ubah",
    # Bisect
    "bisect": "bagi cari",
    # Reflog
    "reflog": "jejak",
    # Worktree
    "worktree": "folder kerja",
}


def route_command(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Route a parsed command to its handler.

    Returns exit code.
    """
    verb = parsed.verb

    if not verb:
        raise InvalidCommandError(parsed.raw or "(empty)")

    # Try subcommand routing first
    if parsed.subcommand:
        subcommand_key = (verb, parsed.subcommand)
        handler = SUBCOMMANDS.get(subcommand_key)
        if handler:
            return handler(parsed, verbose=verbose, debug=debug)

    # Try simple command routing
    handler = COMMANDS.get(verb)
    if handler:
        return handler(parsed, verbose=verbose, debug=debug)

    # Unknown command - check for suggestion from parser
    suggestion = SUGGESTIONS.get(verb)
    
    # Check if parser found a similar command
    if not suggestion and "_suggestion" in parsed.options:
        suggestion = parsed.options["_suggestion"]
    
    raise InvalidCommandError(verb, suggestion=suggestion)
