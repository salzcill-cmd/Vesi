"""Hook system - pre-commit, post-commit, pre-push hooks.

Allows users to run custom scripts/commands during vesi operations.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Callable


@dataclass
class HookResult:
    """Result of running a hook."""

    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0


# Available hook types
HOOK_TYPES = [
    "pre-commit",      # Runs before commit
    "post-commit",     # Runs after commit
    "pre-push",        # Runs before push
    "post-merge",      # Runs after merge
    "post-checkout",   # Runs after branch switch
    "pre-rebase",      # Runs before rebase
    "post-rewrite",    # Runs after commit amend/rebase
    "prepare-commit-msg",  # Runs before commit message editor
    "commit-msg",      # Runs after commit message is written
]


class HookManager:
    """Manages git-style hooks."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.vesi_dir = repo_root / ".vesi"
        self.hooks_dir = self.vesi_dir / "hooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        self._hook_dir_added_to_path = False

    def list_hooks(self) -> dict[str, bool]:
        """List all available hooks and their status."""
        hooks = {}
        for hook_type in HOOK_TYPES:
            hook_path = self.hooks_dir / hook_type
            hooks[hook_type] = hook_path.is_file() and os.access(hook_path, os.X_OK)
        return hooks

    def install_hook(
        self,
        hook_type: str,
        script: str,
        executable: bool = True,
    ) -> Path:
        """Install a hook script.

        Args:
            hook_type: Type of hook (pre-commit, post-commit, etc.)
            script: Script content or path to script
            executable: Make the hook executable

        Returns path to installed hook.
        """
        if hook_type not in HOOK_TYPES:
            raise ValueError(f"Unknown hook type: {hook_type}. Valid: {HOOK_TYPES}")

        hook_path = self.hooks_dir / hook_type

        # Check if it's a file path or inline script
        if "\n" not in script and Path(script).is_file():
            # Copy from file
            import shutil
            shutil.copy2(script, hook_path)
        else:
            # Write inline script
            if not script.startswith("#!"):
                script = f"#!/bin/bash\n{script}"
            hook_path.write_text(script, encoding="utf-8")

        # Make executable
        if executable:
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        return hook_path

    def uninstall_hook(self, hook_type: str) -> bool:
        """Uninstall a hook."""
        hook_path = self.hooks_dir / hook_type
        if hook_path.is_file():
            hook_path.unlink()
            return True
        return False

    def get_hook(self, hook_type: str) -> str | None:
        """Get hook script content."""
        hook_path = self.hooks_dir / hook_type
        if hook_path.is_file():
            return hook_path.read_text(encoding="utf-8")
        return None

    def has_hook(self, hook_type: str) -> bool:
        """Check if a hook is installed."""
        hook_path = self.hooks_dir / hook_type
        return hook_path.is_file() and os.access(hook_path, os.X_OK)

    def run_hook(
        self,
        hook_type: str,
        env: dict | None = None,
        stdin_data: str | None = None,
        timeout: int = 60,
    ) -> HookResult:
        """Run a hook script.

        Args:
            hook_type: Type of hook to run
            env: Additional environment variables
            stdin_data: Data to pass to stdin
            timeout: Timeout in seconds

        Returns HookResult with success status and output.
        """
        hook_path = self.hooks_dir / hook_type

        if not hook_path.is_file():
            return HookResult(success=True, output="Hook tidak ditemukan, skip.")

        if not os.access(hook_path, os.X_OK):
            return HookResult(
                success=False,
                error=f"Hook '{hook_type}' tidak executable.",
                exit_code=1,
            )

        # Prepare environment
        hook_env = os.environ.copy()
        hook_env["VESI_DIR"] = str(self.vesi_dir)
        hook_env["VESI_REPO_DIR"] = str(self.repo_root)
        hook_env["VESI_HOOK"] = hook_type

        if env:
            hook_env.update(env)

        try:
            result = subprocess.run(
                [str(hook_path)],
                cwd=str(self.repo_root),
                env=hook_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=stdin_data,
            )

            return HookResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return HookResult(
                success=False,
                error=f"Hook '{hook_type}' timeout setelah {timeout} detik.",
                exit_code=124,
            )
        except Exception as e:
            return HookResult(
                success=False,
                error=f"Error menjalankan hook: {e}",
                exit_code=1,
            )

    def run_hooks(
        self,
        hook_type: str,
        env: dict | None = None,
        stdin_data: str | None = None,
    ) -> HookResult:
        """Run all hooks of a type (main hook + any chain hooks).

        Returns combined result.
        """
        # Run main hook
        main_result = self.run_hook(hook_type, env=env, stdin_data=stdin_data)

        if not main_result.success:
            return main_result

        # Run chain hooks (hook-type-1, hook-type-2, etc.)
        combined_output = main_result.output

        for i in range(1, 100):
            chain_hook = f"{hook_type}-{i}"
            if not self.has_hook(chain_hook):
                break

            chain_result = self.run_hook(chain_hook, env=env)
            combined_output += f"\n--- {chain_hook} ---\n{chain_result.output}"

            if not chain_result.success:
                return HookResult(
                    success=False,
                    output=combined_output,
                    error=chain_result.error,
                    exit_code=chain_result.exit_code,
                )

        return HookResult(
            success=True,
            output=combined_output,
        )

    def create_sample_hooks(self) -> list[Path]:
        """Create sample hook scripts."""
        samples = {
            "pre-commit": """#!/bin/bash
# Pre-commit hook - runs before each commit
# Use this for linting, formatting, tests, etc.

echo "Running pre-commit checks..."

# Example: Run tests
# python -m pytest tests/ -q

# Example: Check for debug statements
# if grep -rn "TODO\\|FIXME\\|XXX" --include="*.py" src/; then
#     echo "Warning: Found TODO/FIXME comments"
# fi

# Example: Run linter
# python -m ruff check src/

echo "Pre-commit checks passed!"
exit 0
""",
            "commit-msg": """#!/bin/bash
# Commit-msg hook - validates commit message
# $1 is the path to the file containing the commit message

commit_msg_file=$1
commit_msg=$(cat "$commit_msg_file")

# Example: Check minimum length
if [ ${#commit_msg} -lt 3 ]; then
    echo "Error: Commit message too short (min 3 chars)"
    exit 1
fi

# Example: Check conventional commit format
# if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|test|chore|breaking):"; then
#     echo "Warning: Commit message doesn't follow conventional format"
# fi

exit 0
""",
            "pre-push": """#!/bin/bash
# Pre-push hook - runs before push
# Receives: $1 = remote name, $2 = remote URL

remote=$1
url=$2

echo "Pushing to $remote ($url)"

# Example: Run tests before push
# python -m pytest tests/ -q

# Example: Check for sensitive data
# if git log origin/main..HEAD --oneline | grep -qi "password\\|secret\\|token"; then
#     echo "Warning: Commit messages may contain sensitive data"
#     exit 1
# fi

exit 0
""",
        }

        created = []
        for hook_type, content in samples.items():
            hook_path = self.install_hook(hook_type, content)
            created.append(hook_path)

        return created

    def get_hook_help(self, hook_type: str | None = None) -> str:
        """Get help text for hooks."""
        if hook_type:
            help_text = f"Hook: {hook_type}\n\n"
            help_text += f"Deskripsi: {self._get_hook_description(hook_type)}\n\n"
            help_text += f"Status: {'✓ Installed' if self.has_hook(hook_type) else '✗ Not installed'}\n\n"

            content = self.get_hook(hook_type)
            if content:
                help_text += f"Script:\n{content}\n"

            return help_text

        # List all hooks
        help_text = "Vesi Hooks\n\n"
        help_text += "Hooks memungkinkanmu menjalankan script otomatis saat operasi vesi.\n\n"
        help_text += "Hook Types:\n"

        for hook_type in HOOK_TYPES:
            status = "✓" if self.has_hook(hook_type) else " "
            desc = self._get_hook_description(hook_type)
            help_text += f"  [{status}] {hook_type:<25} {desc}\n"

        help_text += "\nCommands:\n"
        help_text += "  vesi hook install <type> <script>  Install hook\n"
        help_text += "  vesi hook uninstall <type>        Uninstall hook\n"
        help_text += "  vesi hook list                    List all hooks\n"
        help_text += "  vesi hook sample                  Create sample hooks\n"

        return help_text

    def _get_hook_description(self, hook_type: str) -> str:
        """Get description for a hook type."""
        descriptions = {
            "pre-commit": "Runs before commit (linting, tests)",
            "post-commit": "Runs after commit (notifications)",
            "pre-push": "Runs before push (final checks)",
            "post-merge": "Runs after merge (dependency install)",
            "post-checkout": "Runs after branch switch",
            "pre-rebase": "Runs before rebase",
            "post-rewrite": "Runs after amend/rebase",
            "prepare-commit-msg": "Before commit message editor",
            "commit-msg": "Validates commit message",
        }
        return descriptions.get(hook_type, "")
