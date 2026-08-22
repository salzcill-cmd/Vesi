"""History - version log traversal."""

from __future__ import annotations

from dataclasses import dataclass

from vesi.core.snapshot import SnapshotInfo, SnapshotManager
from vesi.repository.repository import Repository
from vesi.storage.refs import Refs


@dataclass
class HistoryEntry:
    """A single entry in the version history."""

    info: SnapshotInfo
    is_head: bool = False
    branch_indicator: str = ""


def get_history(
    repo: Repository,
    limit: int = 10,
    branch_name: str | None = None,
) -> list[HistoryEntry]:
    """Get version history.

    Walks the commit chain from HEAD backwards, collecting up to limit entries.
    """
    snapshot_mgr = SnapshotManager(repo)

    # Start from the branch tip or specified branch
    if branch_name:
        start_hash = repo.refs.get_branch_hash(branch_name)
    else:
        start_hash = repo.get_head_commit()

    if not start_hash:
        return []

    entries: list[HistoryEntry] = []
    current_hash = start_hash
    active_branch = repo.refs.get_active_branch()

    while current_hash and len(entries) < limit:
        try:
            info = snapshot_mgr.get_info(current_hash)
        except Exception:
            break

        is_head = current_hash == start_hash
        branch_indicator = ""
        if is_head and active_branch:
            branch_indicator = f" ({active_branch})"

        entries.append(
            HistoryEntry(
                info=info,
                is_head=is_head,
                branch_indicator=branch_indicator,
            )
        )

        current_hash = info.parent

    return entries


def format_history(entries: list[HistoryEntry]) -> str:
    """Format history for display."""
    if not entries:
        return "Belum ada versi yang disimpan. Mulai dengan: mulai proyek"

    lines: list[str] = []
    lines.append(f"Riwayat versi ({len(entries)} terakhir):")
    lines.append("")

    for entry in entries:
        info = entry.info
        head_marker = "* " if entry.is_head else "  "
        branch_suffix = entry.branch_indicator

        lines.append(f"  {head_marker}{info.id}  {info.message}{branch_suffix}")
        lines.append(
            f"           {info.timestamp[:16]}  ({info.file_count} file)"
        )
        lines.append("")

    return "\n".join(lines)
