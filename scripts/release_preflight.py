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

    # pytest needs the backend package importable for the fork-guard tests.
    existing_pp = os.environ.get("PYTHONPATH", "")
    backend_pp = str(REPO_ROOT / "backend")
    os.environ["PYTHONPATH"] = backend_pp if not existing_pp else f"{backend_pp}{os.pathsep}{existing_pp}"

    # Fork-wiring guard tests run first and fast: the manifest meta-test, the
    # general signature-drift guard, and every *_wiring.py source-grep test.
    # This makes the release gate fail loudly if an upstream sync dropped a fork
    # patch, before spending time on format/build steps.
    fork_guard_targets = [
        "backend/open_webui/test/util/test_fork_features_manifest.py",
        "backend/open_webui/test/util/test_no_kwarg_signature_drift.py",
    ]
    wiring_dir = REPO_ROOT / "backend" / "open_webui" / "test" / "util"
    for wiring_test in sorted(wiring_dir.glob("test_*_wiring.py")):
        fork_guard_targets.append(wiring_test.relative_to(REPO_ROOT).as_posix())

    commands = [
        [python, "-m", "pytest", "-q", *fork_guard_targets],
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