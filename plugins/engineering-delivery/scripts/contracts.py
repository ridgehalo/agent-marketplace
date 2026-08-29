#!/usr/bin/env python3
"""Validate, compile, and document the public engineering-delivery contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(root: Path = ROOT) -> dict[str, Any]:
    path = _plugin_root(root) / "contracts/manifest.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("contract manifest root must be an object")
    return payload


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_contract_digest(
    root: Path = ROOT, manifest: dict[str, Any] | None = None
) -> str:
    contract = manifest or load_manifest(root)
    plugin_root = _plugin_root(root)
    manifest_material = {
        key: value
        for key, value in contract.items()
        if key not in {"contractDigest", "generatedDocs"}
    }
    artifact_paths: list[str] = []
    for field in ("schemas", "templates", "tools"):
        values = contract.get(field, {})
        if isinstance(values, dict):
            artifact_paths.extend(
                value for value in values.values() if isinstance(value, str)
            )
    artifacts = {
        relative: (plugin_root / relative).read_text(encoding="utf-8")
        for relative in sorted(set(artifact_paths))
    }
    return canonical_hash({"manifest": manifest_material, "artifacts": artifacts})


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return False


def _validate_schema(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _matches_type(value, expected_type):
        return [f"{path} must be {expected_type}"]

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path} must be one of {enum}")

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path} must have at least {minimum} characters")

    if isinstance(value, list):
        minimum = schema.get("minItems")
        if isinstance(minimum, int) and len(value) < minimum:
            errors.append(f"{path} must contain at least {minimum} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_validate_schema(item, item_schema, f"{path}[{index}]"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, item in value.items():
                item_schema = properties.get(key)
                if isinstance(item_schema, dict):
                    errors.extend(_validate_schema(item, item_schema, f"{path}.{key}"))
                elif schema.get("additionalProperties") is False:
                    errors.append(f"{path}.{key} is not allowed")
    return errors


def _plugin_root(root: Path) -> Path:
    nested = root / "plugins/engineering-delivery"
    return nested if nested.is_dir() else root


def _schema_for(kind: str, manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    schemas = manifest.get("schemas")
    if not isinstance(schemas, dict) or kind not in schemas:
        raise ValueError(f"unknown contract kind: {kind}")
    relative = schemas[kind]
    if not isinstance(relative, str):
        raise ValueError(f"schema path must be a string: {kind}")
    schema = read_json(_plugin_root(root) / relative)
    if not isinstance(schema, dict):
        raise ValueError(f"schema root must be an object: {kind}")
    return schema


def validate_payload(
    kind: str,
    payload: Any,
    manifest: dict[str, Any],
    root: Path = ROOT,
) -> list[str]:
    try:
        schema = _schema_for(kind, manifest, root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [str(error)]

    errors = _validate_schema(payload, schema, kind)
    if not isinstance(payload, dict):
        return errors

    if kind == "promotionBundle":
        allowed = payload.get("allowedFields")
        promoted = payload.get("payload")
        if isinstance(allowed, list) and isinstance(promoted, dict):
            unexpected = sorted(set(promoted) - set(allowed))
            if unexpected:
                errors.append(
                    "promotionBundle.allowedFields does not permit: "
                    + ", ".join(unexpected)
                )

    if kind == "contextAssemblyManifest":
        sources = payload.get("sources")
        lock = payload.get("contextLock")
        if isinstance(sources, list) and isinstance(lock, str):
            expected_lock = canonical_hash(sources)
            if lock != expected_lock:
                errors.append(
                    "contextAssemblyManifest.contextLock does not match canonical sources"
                )

    if kind == "deliveryManifest":
        risk = payload.get("risk")
        reviewer_count = payload.get("reviewerCount")
        routing = manifest.get("riskRouting")
        if isinstance(routing, dict) and risk in routing:
            expected = routing[risk].get("reviewers")
            if reviewer_count != expected:
                errors.append(
                    f"deliveryManifest.reviewerCount must be {expected} for risk {risk}"
                )
            if routing[risk].get("humanRequired") is True:
                decision = payload.get("humanDecision")
                if decision is None:
                    errors.append(
                        "deliveryManifest.humanDecision is required for critical risk"
                    )
            release = payload.get("gates", {}).get("release")
            decision = payload.get("humanDecision")
            if release == "passed" and decision != "approved":
                errors.append(
                    "deliveryManifest.humanDecision must be approved before release passes"
                )
        evidence_types = manifest.get("evidenceTypes")
        evidence = payload.get("evidence")
        if isinstance(evidence_types, list) and isinstance(evidence, list):
            for index, item in enumerate(evidence):
                if isinstance(item, dict) and item.get("type") not in evidence_types:
                    errors.append(
                        f"deliveryManifest.evidence[{index}].type is not registered"
                    )

    if kind == "consumerProfile":
        if payload.get("contractVersion") != manifest.get("contractVersion"):
            errors.append("consumerProfile.contractVersion must match public contract")
        if payload.get("contractDigest") != manifest.get("contractDigest"):
            errors.append("consumerProfile.contractDigest must match public contract")
        enabled = payload.get("enabledContracts")
        schemas = manifest.get("schemas")
        if isinstance(enabled, list) and isinstance(schemas, dict):
            unknown = sorted(set(enabled) - set(schemas))
            if unknown:
                errors.append(
                    "consumerProfile.enabledContracts are not registered: "
                    + ", ".join(unknown)
                )
        if payload.get("externalProjectionMode") != "read-only":
            errors.append("consumerProfile.externalProjectionMode must be read-only")
        if payload.get("stateStoreOwnership") != "consumer":
            errors.append("consumerProfile.stateStoreOwnership must be consumer")

    return errors


def compile_profile(profile_path: Path, root: Path = ROOT) -> dict[str, Any]:
    manifest = load_manifest(root)
    profile = read_json(profile_path)
    errors = validate_payload("consumerProfile", profile, manifest, root)
    if errors:
        raise ValueError("; ".join(errors))
    lock_input = {
        "contractVersion": manifest["contractVersion"],
        "contractDigest": manifest["contractDigest"],
        "profile": profile,
    }
    return {
        "contractVersion": manifest["contractVersion"],
        "contractDigest": manifest["contractDigest"],
        "profile": profile,
        "gates": manifest["gates"],
        "riskRouting": manifest["riskRouting"],
        "goalModes": manifest["goalModes"],
        "unsetGoalModeSelection": manifest["unsetGoalModeSelection"],
        "reviewerOutputFields": manifest["reviewerOutputFields"],
        "testInfrastructureRequirements": manifest[
            "testInfrastructureRequirements"
        ],
        "skillPromotionPolicy": manifest["skillPromotionPolicy"],
        "evidenceTypes": manifest["evidenceTypes"],
        "schemas": manifest["schemas"],
        "templates": manifest["templates"],
        "contextLock": canonical_hash(lock_input),
    }


def render_docs(root: Path = ROOT) -> str:
    manifest = load_manifest(root)
    risk_rows = "\n".join(
        f"| {risk} | {rule['reviewers']} | "
        f"{'yes' if rule['humanRequired'] else 'no'} |"
        for risk, rule in manifest["riskRouting"].items()
    )
    schema_rows = "\n".join(
        f"| `{name}` | `{path}` |"
        for name, path in manifest["schemas"].items()
    )
    template_rows = "\n".join(
        f"| `{name}` | `{path}` |"
        for name, path in manifest["templates"].items()
    )
    tool_rows = "\n".join(
        f"| `{name}` | `{path}` |" for name, path in manifest["tools"].items()
    )
    evidence = "\n".join(f"- `{item}`" for item in manifest["evidenceTypes"])
    goal_rows = "\n".join(
        f"| `{mode}` | {rule['selection']} | "
        f"{', '.join(rule.get('authorizes', [])) or '-'} |"
        for mode, rule in manifest["goalModes"].items()
    )
    reviewer_fields = " / ".join(
        f"`{item}`" for item in manifest["reviewerOutputFields"]
    )
    infrastructure = "\n".join(
        f"- `{item}`" for item in manifest["testInfrastructureRequirements"]
    )
    gates = " → ".join(f"`{gate}`" for gate in manifest["gates"])
    promotion = manifest["skillPromotionPolicy"]
    return f"""# Engineering Delivery Contract

この文書は `contracts/manifest.json` から生成する。手動編集しない。

## Version

`{manifest['contractVersion']}`

Contract digest: `{manifest['contractDigest']}`

## Gates

{gates}

`release`はmerge、deploy、公開、課金、権限変更のHuman Gateを含み、
`plan / build / verify`の成功から自動承認しない。

## Risk routing

| Risk | Read-only reviewers | Human decision required |
| --- | ---: | --- |
{risk_rows}

## Goal Modes

| Mode | Selection | Standing authorization |
| --- | --- | --- |
{goal_rows}

`auto`の除外対象: {', '.join(manifest['goalModes']['auto']['excludes'])}

Goal Modeが未設定の場合: `{manifest['unsetGoalModeSelection']}`

## Reviewer output

{reviewer_fields}

1 reviewerには1 viewpointと必要最小限のcontextだけを渡し、直接編集させない。

## Safe test infrastructure

{infrastructure}

## Evidence types

{evidence}

## Schemas

| Contract | Path |
| --- | --- |
{schema_rows}

## Templates

| Template | Path |
| --- | --- |
{template_rows}

## Tools

| Tool | Path |
| --- | --- |
{tool_rows}

## Trust domains

- personal consumerとproduct consumerは同じpublic contract versionをpinする
- state storeは各consumerが所有し、共有databaseを要求しない
- external projectionはread-onlyで、source revisionと観測時刻を必須にする
- promotionは許可fieldとredaction classをHuman Gateの記録へ固定する

## Compatibility

- minimum contract version: `{manifest['compatibility']['minimumContractVersion']}`
- breaking change: `{manifest['compatibility']['breakingChangePolicy']}`
- rollback: `{manifest['compatibility']['rollback']}`
- skill昇格は{promotion['minimumConsumers']} consumer以上または
  `{promotion['alternative']}`のEvidence後に行う
- Evidenceが不足する場合は`{promotion['defaultArtifact']}`として保管する
"""


def validate_contracts(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_manifest(root)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"contract manifest: {error}"]

    version = manifest.get("contractVersion")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("contractVersion must be strict semver")
    try:
        expected_digest = compute_contract_digest(root, manifest)
    except (OSError, TypeError, json.JSONDecodeError) as error:
        errors.append(f"contractDigest could not be calculated: {error}")
        expected_digest = None
    if expected_digest and manifest.get("contractDigest") != expected_digest:
        errors.append("contractDigest does not match schemas, templates, and profiles")
    if manifest.get("gates") != ["plan", "build", "verify", "release"]:
        errors.append("gates must be plan, build, verify, release")
    goal_modes = manifest.get("goalModes")
    if not isinstance(goal_modes, dict) or set(goal_modes) != {
        "manual",
        "auto",
        "hold",
    }:
        errors.append("goalModes must define manual, auto, hold")
    else:
        auto = goal_modes["auto"]
        required_authorizations = {
            "repository-write",
            "issue-update",
            "project-update",
            "pull-request",
        }
        required_exclusions = {
            "merge",
            "deployment",
            "publication",
            "payment",
            "permission-change",
        }
        if not required_authorizations.issubset(set(auto.get("authorizes", []))):
            errors.append("goalModes.auto is missing standing authorization")
        if not required_exclusions.issubset(set(auto.get("excludes", []))):
            errors.append("goalModes.auto is missing release exclusions")
    if manifest.get("unsetGoalModeSelection") != "excluded":
        errors.append("unsetGoalModeSelection must be excluded")
    if manifest.get("reviewerOutputFields") != [
        "severity",
        "condition",
        "impact",
        "evidence",
        "minimalFix",
    ]:
        errors.append("reviewerOutputFields contract is incomplete")

    promotion = manifest.get("skillPromotionPolicy")
    if not isinstance(promotion, dict):
        errors.append("skillPromotionPolicy is required")
    else:
        minimum_consumers = promotion.get("minimumConsumers")
        if not isinstance(minimum_consumers, int) or minimum_consumers < 2:
            errors.append("skillPromotionPolicy.minimumConsumers must be at least 2")
        if promotion.get("alternative") != "repeated-use":
            errors.append("skillPromotionPolicy.alternative must be repeated-use")
        if promotion.get("defaultArtifact") != "template":
            errors.append("skillPromotionPolicy.defaultArtifact must be template")

    schemas = manifest.get("schemas")
    if not isinstance(schemas, dict) or not schemas:
        errors.append("contract manifest must register schemas")
    else:
        for kind in schemas:
            try:
                schema = _schema_for(kind, manifest, root)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                errors.append(f"schema {kind}: {error}")
                continue
            for required in ("$schema", "$id", "title", "type", "required", "properties"):
                if required not in schema:
                    errors.append(f"schema {kind} missing {required}")

    plugin_root = _plugin_root(root)
    templates = manifest.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append("contract manifest must register templates")
    else:
        for name, relative in templates.items():
            if not isinstance(relative, str) or not (plugin_root / relative).is_file():
                errors.append(f"template {name} is missing")

    tools = manifest.get("tools")
    if not isinstance(tools, dict) or not tools:
        errors.append("contract manifest must register tools")
    else:
        for name, relative in tools.items():
            if not isinstance(relative, str) or not (plugin_root / relative).is_file():
                errors.append(f"tool {name} is missing")

    profiles = manifest.get("profiles")
    trust_domains: set[str] = set()
    profile_ids: set[str] = set()
    if not isinstance(profiles, list) or not profiles:
        errors.append("contract manifest must register consumer profiles")
    else:
        for relative in profiles:
            path = plugin_root / relative
            try:
                profile = read_json(path)
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"profile {relative}: {error}")
                continue
            profile_errors = validate_payload(
                "consumerProfile", profile, manifest, root
            )
            errors.extend(f"profile {relative}: {item}" for item in profile_errors)
            if isinstance(profile, dict):
                trust_domain = profile.get("trustDomain")
                profile_id = profile.get("profileId")
                if isinstance(trust_domain, str):
                    trust_domains.add(trust_domain)
                if isinstance(profile_id, str):
                    if profile_id in profile_ids:
                        errors.append(f"duplicate profileId: {profile_id}")
                    profile_ids.add(profile_id)
    if trust_domains != {"personal", "product"}:
        errors.append("consumer profiles must cover separate personal and product domains")

    if (root / "plugins/engineering-delivery").is_dir():
        try:
            plugin_manifest = read_json(plugin_root / ".codex-plugin/plugin.json")
            plugin_version = plugin_manifest["version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            errors.append(f"plugin release metadata: {error}")
            plugin_version = None
        try:
            changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"CHANGELOG: {error}")
        else:
            if plugin_version and f"[{plugin_version}]" not in changelog:
                errors.append("CHANGELOG is missing current plugin version")
            digest = manifest.get("contractDigest")
            if isinstance(digest, str) and f"contract-digest: {digest}" not in changelog:
                errors.append("CHANGELOG is missing current contractDigest")
        try:
            compatibility = (root / "docs/compatibility.md").read_text(
                encoding="utf-8"
            )
        except OSError as error:
            errors.append(f"compatibility declaration: {error}")
        else:
            if f"contract version `{version}`" not in compatibility:
                errors.append("compatibility declaration is missing contract version")
            digest = manifest.get("contractDigest")
            if isinstance(digest, str) and f"contract digest `{digest}`" not in compatibility:
                errors.append("compatibility declaration is missing contractDigest")

    valid_root = plugin_root / "fixtures/valid"
    for path in sorted(valid_root.glob("*.json")):
        try:
            fixture = read_json(path)
            fixture_errors = validate_payload(
                fixture["kind"], fixture["payload"], manifest, root
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            errors.append(f"valid fixture {path.name}: {error}")
            continue
        errors.extend(f"valid fixture {path.name}: {item}" for item in fixture_errors)

    invalid_root = plugin_root / "fixtures/invalid"
    for path in sorted(invalid_root.glob("*.json")):
        try:
            fixture = read_json(path)
            fixture_errors = validate_payload(
                fixture["kind"], fixture["payload"], manifest, root
            )
            expected = fixture["expectedError"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            errors.append(f"invalid fixture {path.name}: {error}")
            continue
        if not fixture_errors:
            errors.append(f"invalid fixture {path.name} was accepted")
        elif not any(expected in item for item in fixture_errors):
            errors.append(
                f"invalid fixture {path.name} did not report expectedError {expected}"
            )

    generated_relative = manifest.get("generatedDocs")
    if not isinstance(generated_relative, str):
        errors.append("generatedDocs path is required")
    else:
        generated_path = plugin_root / generated_relative
        try:
            current = generated_path.read_text(encoding="utf-8")
        except OSError:
            errors.append("generated contract docs are missing")
        else:
            if current != render_docs(root):
                errors.append("generated contract docs are stale")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("--profile", type=Path, required=True)
    render_parser = subparsers.add_parser("render-docs")
    render_parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "validate":
        errors = validate_contracts(ROOT)
        if errors:
            print("Contract validation failed:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Contract validation passed")
        return 0

    if args.command == "compile":
        try:
            payload = compile_profile(args.profile.resolve(), ROOT)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Profile compilation failed: {error}", file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    generated = render_docs(ROOT)
    manifest = load_manifest(ROOT)
    destination = _plugin_root(ROOT) / manifest["generatedDocs"]
    if args.check:
        try:
            current = destination.read_text(encoding="utf-8")
        except OSError:
            current = ""
        if current != generated:
            print("Generated contract docs are stale", file=sys.stderr)
            return 1
        print("Generated contract docs are current")
        return 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generated, encoding="utf-8")
    print(destination.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
