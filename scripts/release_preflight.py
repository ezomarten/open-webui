from __future__ import annotations

import shutil
import subprocess
import sys
import os
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


def ensure_supported_node_version(node: str) -> None:
    result = subprocess.run(
        [node, "--version"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip()
    major_text = version.removeprefix("v").split(".", 1)[0]

    try:
        major = int(major_text)
    except ValueError as exc:
        raise SystemExit(f"Unable to parse Node.js version: {version}") from exc

    if major < 18 or major > 22:
        raise SystemExit(
            "Release preflight requires Node.js >=18.13.0 <=22.x.x; "
            f"found {version}. Switch to Node 22 and rerun."
        )


def main() -> int:
    python = sys.executable
    node = resolve_binary("node")
    npm = resolve_binary("npm")

    ensure_supported_node_version(node)

    commands = [
        [python, "-m", "black", "--check", "backend"],
        [npm, "run", "check:format"],
        [npm, "run", "check:i18n"],
        [npm, "run", "test:frontend"],
        [npm, "run", "build"],
    ]

    if os.environ.get("OPENWEBUI_SKIP_CHAT_SMOKE") != "1":
        commands.append([python, "scripts/chat_smoke.py"])

    for command in commands:
        run(command)

    print("Release preflight passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())