#!/usr/bin/env python3
"""Validate marketplace contracts without reading user configuration."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PLUGINS = {
    "engineering-delivery": {
        "issue-to-pr",
        "pr-self-review",
        "loop-review",
        "dev-experience-evidence",
    },
    "android-device-control": {"android-app-debugging", "android-device-operations"},
}
FORBIDDEN_TEXT = {
    "github.com/" + "users/": "user-specific GitHub Project URL",
    "LIMITLESS_" + "API_" + "KEY": "private external-service setting",
    "db/" + "auth/": "authenticated browser session path",
}
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:['\"])?(?:api[_-]?key|password|client[_-]?secret|secret|(?:[a-z0-9]+[_-])*token|cookie|session(?:[_-]?(?:id|token|key))?)(?:['\"])?\s*[:=]\s*(?:['\"][^'\"\r\n]+['\"]|[^\s#;,}\]]+)"
)
TOKEN_VALUE = re.compile(
    r"(?i)(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})"
)
LOCAL_ABSOLUTE_PATH = re.compile(
    r"(?i)(?:/(?:Users|home)/[^/\s]+/|/(?:private/)?tmp/|[A-Z]:\\Users\\[^\\\s]+\\)"
)
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
BEARER_VALUE = re.compile(r"(?i)authorization:\s*bearer\s+(?!\[REDACTED\])\S+")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
TODO_MARKER = "[" + "TODO:"


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return None
    except json.JSONDecodeError as error:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {error}")
        return None
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path.relative_to(ROOT)}")
        return None
    return value


def require_fields(
    payload: dict[str, Any], fields: tuple[str, ...], label: str, errors: list[str]
) -> None:
    for field in fields:
        value = payload.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"{label} missing required field: {field}")


def frontmatter(path: Path, errors: list[str]) -> dict[str, str] | None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"missing YAML frontmatter: {path.relative_to(ROOT)}")
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append(f"unterminated YAML frontmatter: {path.relative_to(ROOT)}")
        return None
    parsed: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"invalid frontmatter line: {path.relative_to(ROOT)}: {line}")
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parsed


def validate_repository(root: Path = ROOT) -> list[str]:
    global ROOT
    original_root = ROOT
    ROOT = root.resolve()
    errors: list[str] = []
    try:
        codex_market = load_json(ROOT / ".agents/plugins/marketplace.json", errors)
        claude_market = load_json(ROOT / ".claude-plugin/marketplace.json", errors)
        plugin_versions: dict[str, str | None] = {}
        for plugin_name in EXPECTED_PLUGINS:
            plugin_root = ROOT / "plugins" / plugin_name
            codex_plugin = load_json(plugin_root / ".codex-plugin/plugin.json", errors)
            claude_plugin = load_json(plugin_root / ".claude-plugin/plugin.json", errors)
            platform_manifests = (
                ("Codex", codex_plugin),
                ("Claude", claude_plugin),
            )
            manifests = [item for _, item in platform_manifests if item is not None]
            for platform, manifest in platform_manifests:
                if manifest is None:
                    continue
                label = f"{platform} plugin manifest {plugin_name}"
                require_fields(
                    manifest,
                    ("name", "version", "description", "author", "license"),
                    label,
                    errors,
                )
                if manifest.get("name") != plugin_name:
                    errors.append(f"plugin manifest name must be {plugin_name}")
                if not SEMVER.fullmatch(str(manifest.get("version", ""))):
                    errors.append(f"plugin manifest version must be strict semver: {plugin_name}")
                if manifest.get("license") != "Apache-2.0":
                    errors.append(f"plugin manifest license must be Apache-2.0: {plugin_name}")
                author = manifest.get("author")
                if not isinstance(author, dict) or not author.get("name"):
                    errors.append(f"plugin manifest author.name is required: {plugin_name}")
                for forbidden in ("hooks", "mcpServers", "apps"):
                    if forbidden in manifest:
                        errors.append(f"plugin must not declare {forbidden}: {plugin_name}")

            versions = {str(item.get("version")) for item in manifests}
            if len(versions) != 1:
                errors.append(
                    f"plugin manifest versions differ: {plugin_name}: {sorted(versions)}"
                )
            plugin_versions[plugin_name] = next(iter(versions), None)

        if codex_market is not None:
            require_fields(codex_market, ("name", "plugins"), "Codex marketplace", errors)
            if codex_market.get("name") != "ridgehalo":
                errors.append("Codex marketplace name must be ridgehalo")
            entries = codex_market.get("plugins")
            if not isinstance(entries, list):
                errors.append("Codex marketplace plugins must be an array")
            else:
                names = {entry.get("name") for entry in entries if isinstance(entry, dict)}
                if names != set(EXPECTED_PLUGINS) or len(entries) != len(EXPECTED_PLUGINS):
                    errors.append(f"Codex marketplace plugin set mismatch: {sorted(str(name) for name in names)}")
                for entry in entries:
                    if not isinstance(entry, dict):
                        errors.append("Codex marketplace plugin entry must be an object")
                        continue
                    name = entry.get("name")
                    expected_source = {"source": "local", "path": f"./plugins/{name}"}
                    if entry.get("source") != expected_source:
                        errors.append(f"Codex marketplace source mismatch: {name}")
                    policy = entry.get("policy")
                    if not isinstance(policy, dict):
                        errors.append(f"Codex marketplace entry missing policy: {name}")
                    else:
                        require_fields(
                            policy,
                            ("installation", "authentication"),
                            f"Codex marketplace policy {name}",
                            errors,
                        )
                    if not entry.get("category"):
                        errors.append(f"Codex marketplace entry missing category: {name}")

        if claude_market is not None:
            require_fields(
                claude_market,
                ("name", "owner", "plugins"),
                "Claude marketplace",
                errors,
            )
            if claude_market.get("name") != "ridgehalo":
                errors.append("Claude marketplace name must be ridgehalo")
            entries = claude_market.get("plugins")
            if not isinstance(entries, list):
                errors.append("Claude marketplace plugins must be an array")
            else:
                names = {entry.get("name") for entry in entries if isinstance(entry, dict)}
                if names != set(EXPECTED_PLUGINS) or len(entries) != len(EXPECTED_PLUGINS):
                    errors.append(f"Claude marketplace plugin set mismatch: {sorted(str(name) for name in names)}")
                for entry in entries:
                    if not isinstance(entry, dict):
                        errors.append("Claude marketplace plugin entry must be an object")
                        continue
                    name = entry.get("name")
                    if entry.get("source") != f"./plugins/{name}":
                        errors.append(f"Claude marketplace source mismatch: {name}")
                    if str(entry.get("version")) != plugin_versions.get(str(name)):
                        errors.append(f"Claude marketplace and plugin versions differ: {name}")

        for plugin_name, expected_skills in EXPECTED_PLUGINS.items():
            plugin_root = ROOT / "plugins" / plugin_name
            skill_root = plugin_root / "skills"
            actual_skills = {path.parent.name for path in skill_root.glob("*/SKILL.md")}
            if actual_skills != expected_skills:
                errors.append(
                    f"skill set mismatch: {plugin_name}: expected={sorted(expected_skills)} actual={sorted(actual_skills)}"
                )
            for skill_path in sorted(skill_root.glob("*/SKILL.md")):
                metadata = frontmatter(skill_path, errors)
                if metadata is None:
                    continue
                folder = skill_path.parent.name
                if metadata.get("name") != folder:
                    errors.append(f"skill name does not match folder: {skill_path.relative_to(ROOT)}")
                description = metadata.get("description", "")
                if len(description) < 40:
                    errors.append(f"skill description is not discriminating: {folder}")
                text = skill_path.read_text(encoding="utf-8")
                if "../../references/github-safety.md" in text and not (
                    plugin_root / "references/github-safety.md"
                ).is_file():
                    errors.append(f"missing shared reference for skill: {folder}")

        ignored_parts = {".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__", ".pycache"}
        for path in ROOT.rglob("*"):
            if ignored_parts.intersection(path.parts):
                continue
            if path.is_symlink():
                errors.append(f"symlinks are not allowed in release content: {path.relative_to(ROOT)}")
                continue
            if not path.is_file():
                continue
            try:
                content = path.read_bytes()
            except OSError as error:
                errors.append(f"unreadable release file: {path.relative_to(ROOT)}: {error}")
                continue
            if b"\0" in content:
                continue
            text = content.decode("utf-8", errors="replace")
            for needle, label in FORBIDDEN_TEXT.items():
                if needle in text:
                    errors.append(f"{label} found in {path.relative_to(ROOT)}")
            if SECRET_ASSIGNMENT.search(text):
                errors.append(f"secret-like assignment found in {path.relative_to(ROOT)}")
            if TOKEN_VALUE.search(text):
                errors.append(f"token-like value found in {path.relative_to(ROOT)}")
            if LOCAL_ABSOLUTE_PATH.search(text):
                errors.append(f"local absolute path found in {path.relative_to(ROOT)}")
            if PRIVATE_KEY.search(text):
                errors.append(f"private key found in {path.relative_to(ROOT)}")
            if BEARER_VALUE.search(text):
                errors.append(f"bearer credential found in {path.relative_to(ROOT)}")
            if TODO_MARKER in text:
                errors.append(f"unfinished placeholder found in {path.relative_to(ROOT)}")

        sys.path.insert(0, str(ROOT / "scripts"))
        from contracts import validate_contracts

        errors.extend(
            f"engineering-delivery contract: {error}"
            for error in validate_contracts(ROOT)
        )
    finally:
        ROOT = original_root
    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation passed: manifests, skills, permissions boundary, and release content")
    return 0


if __name__ == "__main__":
    sys.exit(main())
