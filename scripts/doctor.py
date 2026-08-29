#!/usr/bin/env python3
"""Read back marketplace and plugin state without modifying it."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
MARKETPLACE = "ridgehalo"
DEFAULT_PLUGIN = "engineering-delivery"
PLUGIN_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def source_checks(root: Path, plugins: list[str]) -> list[dict[str, str]]:
    sys.path.insert(0, str(SCRIPT_DIR))
    from validate import validate_repository

    errors = validate_repository(root)
    results = [
        check(
            "source-contract",
            "pass" if not errors else "fail",
            "manifest and skill contracts are valid" if not errors else "; ".join(errors),
        )
    ]
    for plugin in plugins:
        if not PLUGIN_NAME.fullmatch(plugin):
            results.append(check(f"source-version:{plugin}", "fail", "invalid plugin name"))
            continue
        manifest_path = root / "plugins" / plugin / ".codex-plugin/plugin.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            version = manifest["version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            results.append(check(f"source-version:{plugin}", "fail", str(error)))
        else:
            results.append(check(f"source-version:{plugin}", "pass", str(version)))
    return results


def source_versions(root: Path, plugins: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for plugin in plugins:
        if not PLUGIN_NAME.fullmatch(plugin):
            versions[plugin] = ""
            continue
        path = root / "plugins" / plugin / ".codex-plugin/plugin.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            version = payload["version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            versions[plugin] = ""
        else:
            versions[plugin] = str(version)
    return versions


def profile_checks(
    root: Path, profiles: list[Path]
) -> list[dict[str, str]]:
    if not profiles:
        return []
    sys.path.insert(0, str(root / "scripts"))
    from contracts import compile_profile

    results: list[dict[str, str]] = []
    for profile_path in profiles:
        try:
            compiled = compile_profile(profile_path.resolve(), root)
            profile_id = compiled["profile"]["profileId"]
            version = compiled["contractVersion"]
            digest = compiled["contractDigest"]
            lock = compiled["contextLock"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            results.append(
                check(
                    f"consumer-profile:{profile_path.name}",
                    "fail",
                    str(error),
                )
            )
            continue
        results.append(
            check(
                f"consumer-profile:{profile_id}",
                "pass",
                f"contractVersion={version} contractDigest={digest} contextLock={lock}",
            )
        )
    return results


def codex_checks(
    plugins: list[str], expected_versions: dict[str, str]
) -> list[dict[str, str]]:
    binary = shutil.which("codex")
    if binary is None:
        return [check("codex-cli", "unverified", "codex CLI is not available on PATH")]
    process = run([binary, "plugin", "list"])
    output = f"{process.stdout}\n{process.stderr}".strip()
    if process.returncode != 0:
        return [check("codex-plugin-list", "fail", output or "command failed")]
    results = [check("codex-cli", "pass", binary)]
    lines = output.splitlines()
    for plugin in plugins:
        identifier = f"{plugin}@{MARKETPLACE}"
        identifier_pattern = re.compile(
            rf"(?<![A-Za-z0-9_.-]){re.escape(identifier)}(?![A-Za-z0-9_.-])"
        )
        matched_line = next(
            (line for line in lines if identifier_pattern.search(line)), None
        )
        if matched_line is None:
            results.append(
                check(f"codex-plugin:{plugin}", "fail", "plugin was not found in codex plugin list")
            )
            continue
        expected = expected_versions[plugin]
        if not expected:
            results.append(
                check(f"codex-plugin:{plugin}", "fail", "source version is unavailable")
            )
            continue
        version_pattern = re.compile(
            rf"(?<![0-9A-Za-z.+-]){re.escape(expected)}(?![0-9A-Za-z.+-])"
        )
        version_seen = version_pattern.search(matched_line) is not None
        results.append(
            check(
                f"codex-plugin:{plugin}",
                "pass" if version_seen else "unverified",
                f"{identifier} version={expected}"
                if version_seen
                else f"{identifier} was found but version {expected} was not visible",
            )
        )
    return results


def claude_checks(
    root: Path, plugins: list[str], expected_versions: dict[str, str]
) -> list[dict[str, str]]:
    binary = shutil.which("claude")
    if binary is None:
        return [check("claude-cli", "unverified", "claude CLI is not available on PATH")]
    results = [check("claude-cli", "pass", binary)]
    market_process = run([binary, "plugin", "marketplace", "list", "--json"])
    if market_process.returncode != 0:
        results.append(
            check(
                "claude-marketplace-list",
                "fail",
                (market_process.stdout + market_process.stderr).strip() or "command failed",
            )
        )
        return results
    try:
        marketplaces = json.loads(market_process.stdout)
    except json.JSONDecodeError as error:
        results.append(check("claude-marketplace-list", "fail", f"invalid JSON: {error}"))
        return results
    if not isinstance(marketplaces, list) or not all(
        isinstance(item, dict) for item in marketplaces
    ):
        results.append(
            check("claude-marketplace-list", "fail", "JSON root must be an array of objects")
        )
        return results
    marketplace = next(
        (item for item in marketplaces if item.get("name") == MARKETPLACE), None
    )
    registered = marketplace is not None
    results.append(
        check(
            "claude-marketplace",
            "pass" if registered else "fail",
            MARKETPLACE if registered else "marketplace was not registered",
        )
    )
    if marketplace is not None:
        registered_path = marketplace.get("path") or marketplace.get("installLocation")
        expected_path = root.resolve()
        try:
            actual_path = (
                Path(registered_path).expanduser().resolve()
                if isinstance(registered_path, str) and registered_path
                else None
            )
        except (OSError, RuntimeError):
            actual_path = None
        source_matches = actual_path == expected_path
        results.append(
            check(
                "claude-marketplace-source",
                "pass" if source_matches else "fail",
                str(actual_path)
                if source_matches
                else f"expected={expected_path} actual={actual_path}",
            )
        )

    plugin_process = run([binary, "plugin", "list", "--json"])
    if plugin_process.returncode != 0:
        results.append(
            check(
                "claude-plugin-list",
                "fail",
                (plugin_process.stdout + plugin_process.stderr).strip() or "command failed",
            )
        )
        return results
    try:
        installed_plugins: list[dict[str, Any]] = json.loads(plugin_process.stdout)
    except json.JSONDecodeError as error:
        results.append(check("claude-plugin-list", "fail", f"invalid JSON: {error}"))
        return results
    if not isinstance(installed_plugins, list) or not all(
        isinstance(item, dict) for item in installed_plugins
    ):
        results.append(
            check("claude-plugin-list", "fail", "JSON root must be an array of objects")
        )
        return results
    for plugin in plugins:
        identifier = f"{plugin}@{MARKETPLACE}"
        matched = next((item for item in installed_plugins if item.get("id") == identifier), None)
        if matched is None:
            results.append(check(f"claude-plugin:{plugin}", "fail", "plugin was not installed"))
            continue
        expected = expected_versions[plugin]
        if not expected:
            results.append(
                check(f"claude-plugin:{plugin}", "fail", "source version is unavailable")
            )
            continue
        status = (
            "pass"
            if matched.get("enabled") is True and matched.get("version") == expected
            else "fail"
        )
        detail = f"version={matched.get('version')} enabled={matched.get('enabled')} scope={matched.get('scope')}"
        results.append(check(f"claude-plugin:{plugin}", status, detail))
    return results


def inspect(
    root: Path,
    targets: list[str],
    plugins: list[str],
    profiles: list[Path] | None = None,
) -> dict[str, Any]:
    source_results = source_checks(root, plugins)
    source_results.extend(profile_checks(root, profiles or []))
    expected_versions = source_versions(root, plugins)
    payload: dict[str, Any] = {"source": source_results, "targets": {}}
    if "codex" in targets:
        payload["targets"]["codex"] = codex_checks(plugins, expected_versions)
    if "claude" in targets:
        payload["targets"]["claude"] = claude_checks(root, plugins, expected_versions)
    all_checks = payload["source"] + [
        item for target_checks in payload["targets"].values() for item in target_checks
    ]
    payload["ok"] = all(item["status"] == "pass" for item in all_checks)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("codex", "claude", "all"), default="codex")
    parser.add_argument("--plugin", action="append", dest="plugins")
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument(
        "--profile",
        action="append",
        type=Path,
        dest="profiles",
        help="Consumer profile to compile and read back. Repeat for multiple profiles.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plugins = args.plugins or [DEFAULT_PLUGIN]
    targets = ["codex", "claude"] if args.target == "all" else [args.target]
    payload = inspect(args.source.resolve(), targets, plugins, args.profiles or [])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in payload["source"]:
            print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
        for target, target_checks in payload["targets"].items():
            print(f"\n{target}:")
            for item in target_checks:
                print(f"[{item['status'].upper()}] {item['name']}: {item['detail']}")
        print(f"\noverall: {'pass' if payload['ok'] else 'not verified'}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
