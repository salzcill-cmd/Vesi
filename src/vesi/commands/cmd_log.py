"""Command: lihat riwayat - Show version history."""

from __future__ import annotations

from vesi.core.history import get_history, format_history
from vesi.errors.exceptions import RepositoryNotFoundError
from vesi.parser.parser import ParsedCommand
from vesi.repository.repository import Repository


def cmd_lihat_riwayat(
    parsed: ParsedCommand,
    *,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Show version history."""
    try:
        repo = Repository.find()
    except RepositoryNotFoundError:
        raise

    # Parse limit from args
    limit = 10
    if parsed.args:
        try:
            limit = int(parsed.args[0])
        except ValueError:
            pass

    # Get branch name from options if specified
    branch_name = parsed.options.get("branch")

    entries = get_history(repo, limit=limit, branch_name=branch_name)
    print(format_history(entries))

    return 0
