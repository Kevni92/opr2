"""Install this repository's optional Git hooks without changing global config."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        git_root = Path(result.stdout.strip()).resolve()
        hooks = repo / ".githooks"
        if git_root != repo or not hooks.is_dir():
            raise RuntimeError("run this installer from a complete opr2 Git checkout")
        for hook_name in ("pre-commit", "pre-push"):
            hook = hooks / hook_name
            if not hook.is_file():
                raise RuntimeError(f"required hook is missing: {hook}")
            # Git requires executable hooks on Unix; this is harmless on Windows.
            hook.chmod(0o755)
        subprocess.run(
            ["git", "-C", str(repo), "config", "--local", "core.hooksPath", ".githooks"],
            check=True,
        )
        print(f"Installed repository-local hooks from {hooks}")
        return 0
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"hook installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
