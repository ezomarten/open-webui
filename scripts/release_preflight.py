from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def resolve_binary(name: str) -> str:
    binary = shutil.which(name)
    if binary is None:
        raise SystemExit(f"Required command not found in PATH: {name}")
    return binary


def run(command: list[str]) -> None:
    print(f"> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> int:
    python = sys.executable
    npm = resolve_binary("npm")

    commands = [
        [python, "-m", "black", "--check", "backend"],
        [npm, "run", "check:format"],
        [npm, "run", "check:i18n"],
        [npm, "run", "test:frontend"],
        [npm, "run", "build"],
    ]

    for command in commands:
        run(command)

    print("Release preflight passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())