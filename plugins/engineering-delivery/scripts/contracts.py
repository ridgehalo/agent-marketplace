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
RFC3339_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
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

    if kind == "terminalReport":
        terminal_contract = manifest.get("terminalReporting")
        if not isinstance(terminal_contract, dict):
            errors.append("terminalReporting contract is required")
            return errors
        if payload.get("heading") != terminal_contract.get("heading"):
            errors.append("terminalReport.heading must match the fixed heading")
        actions = payload.get("requiredActions")
        no_action_message = payload.get("noActionMessage")
        if isinstance(actions, list):
            if actions and no_action_message is not None:
                errors.append(
                    "terminalReport.noActionMessage must be omitted when actions exist"
                )
            if not actions and no_action_message not in terminal_contract.get(
                "noActionMessages", []
            ):
                errors.append(
                    "terminalReport.noActionMessage is required when no actions exist"
                )
        authorization = payload.get("authorization")
        if isinstance(authorization, dict):
            if (
                authorization.get("standingAuthorizationValid") is True
                and authorization.get("sourceStateReadBack") != "succeeded"
            ):
                errors.append(
                    "terminalReport.authorization.sourceStateReadBack must succeed "
                    "for standing authorization"
                )
            if (
                authorization.get("operationRequestMatched") is True
                and authorization.get("standingAuthorizationValid") is not True
            ):
                errors.append(
                    "terminalReport.authorization.operationRequestMatched requires "
                    "standingAuthorizationValid"
                )

    if kind == "ssotProjection":
        sources = payload.get("sources")
        projections = payload.get("projections")
        source_by_id: dict[str, dict[str, Any]] = {}
        field_owner: dict[str, str] = {}
        if isinstance(sources, list):
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    continue
                source_id = source.get("sourceId")
                if isinstance(source_id, str):
                    if source_id in source_by_id:
                        errors.append(
                            f"ssotProjection.sources[{index}].sourceId must be unique"
                        )
                    source_by_id[source_id] = source
                canonical_fields = source.get("canonicalFor")
                if not isinstance(canonical_fields, list):
                    continue
                for field in canonical_fields:
                    if not isinstance(field, str):
                        continue
                    if field in field_owner:
                        errors.append(
                            "ssotProjection.sources.canonicalFor must be unique: "
                            + field
                        )
                    elif isinstance(source_id, str):
                        field_owner[field] = source_id
                    if (
                        field == "work-item.dependencies"
                        and source.get("sourceKind")
                        != "github-native-relationships"
                    ):
                        errors.append(
                            "ssotProjection work-item.dependencies must use "
                            "github-native-relationships"
                        )

        if isinstance(projections, list):
            projection_ids: set[str] = set()
            for index, projection in enumerate(projections):
                if not isinstance(projection, dict):
                    continue
                projection_id = projection.get("projectionId")
                if isinstance(projection_id, str):
                    if projection_id in projection_ids:
                        errors.append(
                            f"ssotProjection.projections[{index}].projectionId "
                            "must be unique"
                        )
                    projection_ids.add(projection_id)
                observed_at = projection.get("observedAt")
                if (
                    isinstance(observed_at, str)
                    and not RFC3339_UTC.fullmatch(observed_at)
                ):
                    errors.append(
                        f"ssotProjection.projections[{index}].observedAt "
                        "must be RFC 3339 UTC"
                    )
                projection_of = projection.get("projectionOf")
                if not isinstance(projection_of, dict):
                    continue
                source_id = projection_of.get("sourceId")
                if isinstance(source_id, str) and source_id not in source_by_id:
                    errors.append(
                        f"ssotProjection.projections[{index}].projectionOf.sourceId "
                        "must reference a source"
                    )
                fields = projection_of.get("fields")
                if not isinstance(fields, list):
                    continue
                for field in fields:
                    if not isinstance(field, str):
                        continue
                    if field_owner.get(field) != source_id:
                        errors.append(
                            f"ssotProjection.projections[{index}] field {field} "
                            "must be owned by projectionOf.sourceId"
                        )
                    if (
                        field == "workflow.current-status"
                        and projection.get("purpose")
                        == "pre-merge-classification"
                    ):
                        errors.append(
                            "ssotProjection workflow.current-status cannot be "
                            "pre-merge-classification"
                        )

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
        "terminalReporting": manifest["terminalReporting"],
        "ssotProjection": manifest["ssotProjection"],
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
    terminal = manifest["terminalReporting"]
    terminal_fields = " / ".join(
        f"`{item}`" for item in terminal["requiredActionFields"]
    )
    no_action_messages = "\n".join(
        f"- `{item}`" for item in terminal["noActionMessages"]
    )
    ssot = manifest["ssotProjection"]
    current_state_fields = "\n".join(
        f"- `{item}`" for item in ssot["currentStateFields"]
    )
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

## Terminal reporting

固定見出し: `{terminal['heading']}`

必須Actionのfield: {terminal_fields}

必須Actionのkind: {', '.join(terminal['actionKinds'])}

Actionがない場合の明示文:

{no_action_messages}

任意の提案は必須Actionから分離する。現在のsource stateをlive read-backし、standing
authorizationとOperation Requestが一致するroutine writeを再承認依頼しない。

## SSOT projection

mutableな現在値と本文へ残す投影を区別する。

現在値として扱うfield:

{current_state_fields}

- current stateの正本はconsumerが指定するGitHub Projectとする
- dependencyのfield `{ssot['relationshipField']}` は
  `{ssot['relationshipSourceKind']}`だけが正本になれる
- PR本文の`{ssot['classificationField']}`はmerge前classificationであり、
  Project current statusではない
- 投影には`projectionOf`、`observedAt`、`generated`を必須にする
- Issue / PR本文のmutableなsnapshotを現在値として扱わない

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


def _validate_template_contract(
    root: Path, manifest: dict[str, Any], plugin_root: Path
) -> list[str]:
    errors: list[str] = []
    template_contract = manifest.get("templateContract")
    if not isinstance(template_contract, dict):
        return ["templateContract is required"]

    required_sections = template_contract.get("requiredTopLevelSections")
    expected_sections = [
        "1. 概要",
        "2. 背景",
        "3. 詳細設計",
        "4. テスト影響範囲",
        "5. 新規テストケース",
        "6. 実装順",
        "7. マージ前確認",
        "8. スコープ外",
    ]
    if required_sections != expected_sections:
        errors.append("templateContract.requiredTopLevelSections is incomplete")

    templates = manifest.get("templates")
    if not isinstance(templates, dict):
        return errors
    paths = {
        "issue": templates.get("issue"),
        "pull-request": templates.get("prEvidence"),
    }
    contents: dict[str, str] = {}
    for kind, relative in paths.items():
        if not isinstance(relative, str):
            errors.append(f"{kind} canonical template path is missing")
            continue
        try:
            content = (plugin_root / relative).read_text(encoding="utf-8")
        except OSError as error:
            errors.append(f"{kind} canonical template: {error}")
            continue
        contents[kind] = content
        headings = re.findall(r"^## (.+)$", content, flags=re.MULTILINE)
        if headings[: len(expected_sections)] != expected_sections:
            errors.append(f"{kind} canonical template section order differs")

    evidence_fields = template_contract.get("requiredPrEvidenceFields")
    pull_request = contents.get("pull-request", "")
    if not isinstance(evidence_fields, list) or not evidence_fields:
        errors.append("templateContract.requiredPrEvidenceFields is required")
    else:
        missing = [
            field
            for field in evidence_fields
            if not isinstance(field, str) or f"- {field}:" not in pull_request
        ]
        if missing:
            errors.append(
                "pull-request canonical template is missing Evidence fields: "
                + ", ".join(str(field) for field in missing)
            )

    appendix = template_contract.get("appendixCoverage")
    expected_appendix = {chr(code) for code in range(ord("A"), ord("M") + 1)}
    if not isinstance(appendix, dict) or set(appendix) != expected_appendix:
        errors.append("templateContract.appendixCoverage must cover A through M")
    else:
        allowed_decisions = {"adopt", "adapt", "adapt-or-na"}
        for identifier, resolution in appendix.items():
            if (
                not isinstance(resolution, dict)
                or resolution.get("decision") not in allowed_decisions
                or not isinstance(resolution.get("owner"), str)
                or not isinstance(resolution.get("artifact"), str)
            ):
                errors.append(f"templateContract.appendixCoverage.{identifier} is invalid")

    if (root / "plugins/engineering-delivery").is_dir():
        repository_copies = {
            "issue": root / ".github/ISSUE_TEMPLATE/goal.md",
            "pull-request": root / ".github/pull_request_template.md",
        }
        for kind, path in repository_copies.items():
            try:
                copy = path.read_text(encoding="utf-8")
            except OSError as error:
                errors.append(f"repository {kind} template: {error}")
                continue
            if copy != contents.get(kind):
                errors.append(f"repository {kind} template differs from public canonical")

    return errors


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
    terminal = manifest.get("terminalReporting")
    expected_terminal = {
        "heading": "## あなたにお願いしたいアクション",
        "requiredActionFields": [
            "target",
            "operation",
            "reason",
            "resumeCondition",
        ],
        "actionKinds": ["human-gate", "decision", "external-input", "review"],
        "noActionMessages": [
            "ありません。今回の処理は完了です。",
            "ありません。外部状態が変わるまで待機します。",
        ],
        "standingAuthorizationRule": "live-read-back-and-operation-request-match",
    }
    if terminal != expected_terminal:
        errors.append("terminalReporting contract is incomplete")
    expected_ssot = {
        "currentStateFields": [
            "workflow.current-status",
            "workflow.priority",
            "workflow.goal-mode",
        ],
        "classificationField": "pull-request.pre-merge-classification",
        "relationshipField": "work-item.dependencies",
        "relationshipSourceKind": "github-native-relationships",
        "projectionPurposes": ["snapshot", "pre-merge-classification"],
        "requiredProjectionFields": [
            "projectionOf",
            "observedAt",
            "generated",
        ],
    }
    if manifest.get("ssotProjection") != expected_ssot:
        errors.append("ssotProjection contract is incomplete")
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

    errors.extend(_validate_template_contract(root, manifest, plugin_root))

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
