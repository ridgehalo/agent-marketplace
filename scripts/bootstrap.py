#!/usr/bin/env python3
"""Selectively register the RidgeHalo marketplace and install plugins."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
MARKETPLACE = "ridgehalo"
AVAILABLE_PLUGINS = {"engineering-delivery"}
SENSITIVE_OUTPUT = re.compile(
    r"(?i)(authorization:\s*bearer\s+|(?:access[_-]?)?token\s*[=:]\s*)\S+"
)


class BootstrapError(RuntimeError):
    pass


def codex_deeplink(root: Path, plugin: str) -> str:
    manifest = (root / ".agents/plugins/marketplace.json").resolve()
    return f"codex://plugins/{quote(plugin)}?marketplacePath={quote(str(manifest), safe='')}"


def select_plugins(raw_plugins: list[str] | None) -> list[str]:
    plugins = raw_plugins or ["engineering-delivery"]
    unknown = sorted(set(plugins) - AVAILABLE_PLUGINS)
    if unknown:
        raise BootstrapError(f"unknown plugin: {', '.join(unknown)}")
    return list(dict.fromkeys(plugins))


def validate_source(root: Path) -> None:
    sys.path.insert(0, str(SCRIPT_DIR))
    from validate import validate_repository

    errors = validate_repository(root)
    if errors:
        raise BootstrapError("source validation failed: " + "; ".join(errors))


def build_commands(
    root: Path, targets: list[str], plugins: list[str], scope: str
) -> list[list[str]]:
    commands: list[list[str]] = []
    if "codex" in targets:
        commands.append(["codex", "plugin", "marketplace", "add", str(root)])
        commands.extend(
            [["codex", "plugin", "add", f"{plugin}@{MARKETPLACE}"] for plugin in plugins]
        )
    if "claude" in targets:
        commands.append(
            ["claude", "plugin", "marketplace", "add", str(root), "--scope", scope]
        )
        commands.extend(
            [
                [
                    "claude",
                    "plugin",
                    "install",
                    f"{plugin}@{MARKETPLACE}",
                    "--scope",
                    scope,
                ]
                for plugin in plugins
            ]
        )
    return commands


def preflight_binaries(targets: list[str]) -> None:
    missing = [target for target in targets if shutil.which(target) is None]
    if missing:
        detail = f"required CLI not found on PATH: {', '.join(missing)}"
        if "codex" in missing:
            detail += ". Codex Desktop users can install with the marketplace deeplink shown by --dry-run"
        raise BootstrapError(detail)


def execute(commands: list[list[str]]) -> None:
    for command in commands:
        process = subprocess.run(command, text=True, capture_output=True, check=False)
        output = SENSITIVE_OUTPUT.sub(r"\1[REDACTED]", process.stdout + process.stderr).strip()
        if output:
            print(output)
        if process.returncode != 0:
            raise BootstrapError(
                f"command failed ({process.returncode}): {' '.join(command)}"
            )


def run_doctor(root: Path, target: str, plugins: list[str]) -> None:
    sys.stdout.flush()
    command = [
        sys.executable,
        str(SCRIPT_DIR / "doctor.py"),
        "--source",
        str(root),
        "--target",
        target,
    ]
    for plugin in plugins:
        command.extend(["--plugin", plugin])
    process = subprocess.run(command, text=True, check=False)
    if process.returncode != 0:
        raise BootstrapError("installation commands completed, but doctor read-back did not pass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install = subparsers.add_parser("install", help="register and install selected plugins")
    install.add_argument("--target", choices=("codex", "claude", "all"), default="codex")
    install.add_argument("--plugin", action="append", dest="plugins")
    install.add_argument("--scope", choices=("user", "project", "local"), default="user")
    install.add_argument("--source", type=Path, default=ROOT)
    install.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.source.resolve()
    try:
        plugins = select_plugins(args.plugins)
        validate_source(root)
        targets = ["codex", "claude"] if args.target == "all" else [args.target]
        commands = build_commands(root, targets, plugins, args.scope)
        if args.dry_run:
            print(json.dumps({"targets": targets, "plugins": plugins, "commands": commands}, indent=2))
            if "codex" in targets:
                for plugin in plugins:
                    print(f"Codex Desktop: {codex_deeplink(root, plugin)}")
            return 0
        preflight_binaries(targets)
        execute(commands)
        run_doctor(root, args.target, plugins)
    except BootstrapError as error:
        print(f"bootstrap stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
