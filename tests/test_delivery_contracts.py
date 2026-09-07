from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import contracts


class DeliveryContractTest(unittest.TestCase):
    def test_public_contract_and_generated_docs_are_current(self) -> None:
        self.assertEqual(contracts.validate_contracts(ROOT), [])
        manifest = contracts.load_manifest(ROOT)
        self.assertIn("deliveryEvent", manifest["schemas"])
        self.assertEqual(set(manifest["goalModes"]), {"manual", "auto", "hold"})
        self.assertEqual(manifest["unsetGoalModeSelection"], "excluded")
        self.assertIn("repository-write", manifest["goalModes"]["auto"]["authorizes"])
        self.assertIn("merge", manifest["goalModes"]["auto"]["excludes"])
        self.assertEqual(manifest["contractVersion"], "0.4.0")
        self.assertIn("ssotProjection", manifest["schemas"])
        terminal_reporting = manifest["terminalReporting"]
        self.assertEqual(
            terminal_reporting["heading"],
            "## あなたにお願いしたいアクション",
        )
        self.assertEqual(
            terminal_reporting["requiredActionFields"],
            ["target", "operation", "reason", "resumeCondition"],
        )
        self.assertEqual(
            terminal_reporting["actionKinds"],
            ["human-gate", "decision", "external-input", "review"],
        )
        self.assertIn("terminalReport", manifest["schemas"])
        template_contract = manifest["templateContract"]
        self.assertEqual(template_contract["version"], "1.0.0")
        self.assertEqual(
            template_contract["requiredTopLevelSections"],
            [
                "1. 概要",
                "2. 背景",
                "3. 詳細設計",
                "4. テスト影響範囲",
                "5. 新規テストケース",
                "6. 実装順",
                "7. マージ前確認",
                "8. スコープ外",
            ],
        )
        generated = (
            ROOT
            / "plugins/engineering-delivery/docs/generated/engineering-delivery-contract.md"
        )
        self.assertEqual(generated.read_text(encoding="utf-8"), contracts.render_docs(ROOT))
        self.assertEqual(
            (ROOT / "scripts/contracts.py").read_text(encoding="utf-8"),
            (
                ROOT / "plugins/engineering-delivery/scripts/contracts.py"
            ).read_text(encoding="utf-8"),
        )

    def test_repository_templates_match_the_public_canonical_templates(self) -> None:
        plugin = ROOT / "plugins/engineering-delivery"
        issue = (plugin / "templates/issue-contract.md").read_text(encoding="utf-8")
        pull_request = (plugin / "templates/pr-evidence.md").read_text(encoding="utf-8")

        self.assertEqual(
            (ROOT / ".github/ISSUE_TEMPLATE/goal.md").read_text(encoding="utf-8"),
            issue,
        )
        self.assertEqual(
            (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8"),
            pull_request,
        )
        for heading in contracts.load_manifest(ROOT)["templateContract"][
            "requiredTopLevelSections"
        ]:
            self.assertIn(f"## {heading}", issue)
            self.assertIn(f"## {heading}", pull_request)

    def test_personal_and_product_profiles_compile_without_shared_state(self) -> None:
        personal = contracts.compile_profile(
            ROOT / "plugins/engineering-delivery/profiles/personal-consumer.json",
            ROOT,
        )
        product = contracts.compile_profile(
            ROOT / "plugins/engineering-delivery/profiles/product-consumer.json",
            ROOT,
        )

        self.assertEqual(personal["contractVersion"], product["contractVersion"])
        self.assertEqual(personal["profile"]["trustDomain"], "personal")
        self.assertEqual(product["profile"]["trustDomain"], "product")
        self.assertNotEqual(personal["contextLock"], product["contextLock"])
        self.assertEqual(
            personal["profile"]["contractDigest"], personal["contractDigest"]
        )
        self.assertNotIn("privateData", json.dumps(personal))
        self.assertNotIn("privateData", json.dumps(product))

    def test_each_negative_fixture_is_rejected_for_the_declared_reason(self) -> None:
        fixture_root = (
            ROOT / "plugins/engineering-delivery/fixtures/invalid"
        )
        fixtures = sorted(fixture_root.glob("*.json"))
        self.assertGreaterEqual(len(fixtures), 6)

        for fixture_path in fixtures:
            with self.subTest(fixture=fixture_path.name):
                fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
                errors = contracts.validate_payload(
                    fixture["kind"], fixture["payload"], contracts.load_manifest(ROOT)
                )
                self.assertTrue(
                    any(fixture["expectedError"] in error for error in errors),
                    errors,
                )

    def test_stale_profile_pin_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            profile_path = (
                candidate
                / "plugins/engineering-delivery/profiles/personal-consumer.json"
            )
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["contractVersion"] = "0.0.0"
            profile_path.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = contracts.validate_contracts(candidate)
            self.assertTrue(
                any("contractVersion must match" in error for error in errors),
                errors,
            )

    def test_stale_profile_digest_is_rejected_and_changes_context_lock(self) -> None:
        profile_path = (
            ROOT / "plugins/engineering-delivery/profiles/personal-consumer.json"
        )
        current = contracts.compile_profile(profile_path, ROOT)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__")
            )
            manifest_path = (
                candidate
                / "plugins/engineering-delivery/contracts/manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["goalModes"]["auto"]["authorizes"].append("comment-update")
            manifest["contractDigest"] = contracts.compute_contract_digest(
                candidate, manifest
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            errors = contracts.validate_contracts(candidate)
            self.assertTrue(
                any("contractDigest must match" in error for error in errors), errors
            )
            stale_profile = json.loads(profile_path.read_text(encoding="utf-8"))
            stale_profile["contractDigest"] = manifest["contractDigest"]
            updated_profile = Path(directory) / "updated-profile.json"
            updated_profile.write_text(
                json.dumps(stale_profile, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            compiled = contracts.compile_profile(updated_profile, candidate)
            self.assertNotEqual(current["contextLock"], compiled["contextLock"])

    def test_critical_delivery_requires_human_decision(self) -> None:
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/delivery-manifest.json"
            ).read_text(encoding="utf-8")
        )
        fixture["payload"]["risk"] = "critical"
        errors = contracts.validate_payload(
            "deliveryManifest", fixture["payload"], contracts.load_manifest(ROOT)
        )
        self.assertTrue(any("humanDecision" in error for error in errors), errors)

    def test_release_requires_human_decision_for_every_risk(self) -> None:
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/delivery-manifest.json"
            ).read_text(encoding="utf-8")
        )
        fixture["payload"]["risk"] = "low"
        fixture["payload"]["reviewerCount"] = 0
        fixture["payload"]["gates"]["release"] = "passed"
        errors = contracts.validate_payload(
            "deliveryManifest", fixture["payload"], contracts.load_manifest(ROOT)
        )
        self.assertTrue(any("humanDecision must be approved" in item for item in errors))

    def test_unknown_enabled_contract_is_rejected(self) -> None:
        profile = json.loads(
            (
                ROOT / "plugins/engineering-delivery/profiles/product-consumer.json"
            ).read_text(encoding="utf-8")
        )
        profile["enabledContracts"] = ["doesNotExist"]
        errors = contracts.validate_payload(
            "consumerProfile", profile, contracts.load_manifest(ROOT)
        )
        self.assertTrue(any("enabledContracts are not registered" in item for item in errors))

    def test_unset_goal_mode_cannot_become_auto(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__")
            )
            manifest_path = (
                candidate / "plugins/engineering-delivery/contracts/manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["unsetGoalModeSelection"] = "scheduled-eligible"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            errors = contracts.validate_contracts(candidate)
            self.assertTrue(any("unsetGoalModeSelection" in item for item in errors), errors)

    def test_plugin_only_copy_can_validate_and_compile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "engineering-delivery"
            shutil.copytree(
                ROOT / "plugins/engineering-delivery",
                plugin,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            validator = plugin / "scripts/contracts.py"
            validate = subprocess.run(
                [sys.executable, str(validator), "validate"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            compile_result = subprocess.run(
                [
                    sys.executable,
                    str(validator),
                    "compile",
                    "--profile",
                    str(plugin / "profiles/product-consumer.json"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                compile_result.returncode,
                0,
                compile_result.stdout + compile_result.stderr,
            )
            self.assertEqual(
                json.loads(compile_result.stdout)["contractDigest"],
                contracts.load_manifest(ROOT)["contractDigest"],
            )
            self.assertEqual(
                json.loads(compile_result.stdout)["terminalReporting"]["heading"],
                "## あなたにお願いしたいアクション",
            )

    def test_終端報告の完了_停止_操作なしfixtureを受理する(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture_root = ROOT / "plugins/engineering-delivery/fixtures/valid"

        for name in (
            "terminal-report-completed.json",
            "terminal-report-stopped.json",
            "terminal-report-no-action.json",
            "terminal-report-readback-failed.json",
        ):
            with self.subTest(fixture=name):
                fixture = json.loads((fixture_root / name).read_text(encoding="utf-8"))
                self.assertEqual(
                    contracts.validate_payload(
                        fixture["kind"], fixture["payload"], manifest
                    ),
                    [],
                )

    def test_対話報告は必須情報を保ち機械schemaと分ける(self) -> None:
        required_terms = (
            "interactive-delivery.md",
            "対象", "操作", "理由", "再開条件",
            "必須操作と任意提案", "terminalReport", "固定schemaを維持",
            "既承認の同じscopeを再承認へ戻さず",
        )
        for skill_name in ("issue-to-pr", "pr-self-review"):
            skill = (
                ROOT
                / "plugins/engineering-delivery/skills"
                / skill_name
                / "SKILL.md"
            ).read_text(encoding="utf-8")
            with self.subTest(skill=skill_name):
                for term in required_terms:
                    self.assertIn(term, skill)

    def test_操作なし報告に明示文がなければ拒否する(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = {
            "outcome": "completed",
            "heading": "## あなたにお願いしたいアクション",
            "summary": ["処理が完了した"],
            "requiredActions": [],
            "optionalSuggestions": [],
            "authorization": {
                "sourceStateReadBack": "succeeded",
                "standingAuthorizationValid": False,
                "operationRequestMatched": False,
            },
        }

        errors = contracts.validate_payload("terminalReport", fixture, manifest)

        self.assertTrue(any("noActionMessage" in error for error in errors), errors)

    def test_routine_writeを必須Actionとして再承認依頼できない(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = {
            "outcome": "stopped",
            "heading": "## あなたにお願いしたいアクション",
            "summary": ["処理を停止した"],
            "requiredActions": [
                {
                    "kind": "routine-write",
                    "target": "Issue",
                    "operation": "本文を更新する",
                    "reason": "進捗を記録する",
                    "resumeCondition": "更新を確認できたこと",
                }
            ],
            "optionalSuggestions": [],
            "authorization": {
                "sourceStateReadBack": "succeeded",
                "standingAuthorizationValid": True,
                "operationRequestMatched": True,
            },
        }

        errors = contracts.validate_payload("terminalReport", fixture, manifest)

        self.assertTrue(any("kind" in error for error in errors), errors)

    def test_standing_authorizationにはsource_stateのread_back成功を必須にする(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/terminal-report-no-action.json"
            ).read_text(encoding="utf-8")
        )["payload"]
        fixture["authorization"]["sourceStateReadBack"] = "failed"

        errors = contracts.validate_payload("terminalReport", fixture, manifest)

        self.assertTrue(any("sourceStateReadBack" in error for error in errors), errors)

    def test_source_stateのread_back失敗を停止報告として表現できる(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/terminal-report-readback-failed.json"
            ).read_text(encoding="utf-8")
        )["payload"]

        errors = contracts.validate_payload("terminalReport", fixture, manifest)

        self.assertEqual(errors, [])

    def test_operation_request一致だけではstanding_authorizationにならない(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/terminal-report-no-action.json"
            ).read_text(encoding="utf-8")
        )["payload"]
        fixture["authorization"]["standingAuthorizationValid"] = False
        fixture["authorization"]["operationRequestMatched"] = True

        errors = contracts.validate_payload("terminalReport", fixture, manifest)

        self.assertTrue(
            any("operationRequestMatched" in error for error in errors), errors
        )

    def test_ssot_projectionの正本とtimestamp付き投影を受理する(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/ssot-projection.json"
            ).read_text(encoding="utf-8")
        )

        errors = contracts.validate_payload(
            fixture["kind"], fixture["payload"], manifest
        )

        self.assertEqual(errors, [])

    def test_ssot_projectionで同一fieldの二重正本を拒否する(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/ssot-projection.json"
            ).read_text(encoding="utf-8")
        )["payload"]
        fixture["sources"].append(
            {
                "sourceId": "duplicate-project",
                "sourceKind": "github-project",
                "canonicalFor": ["workflow.current-status"],
                "generated": False,
            }
        )

        errors = contracts.validate_payload("ssotProjection", fixture, manifest)

        self.assertTrue(any("canonicalFor must be unique" in item for item in errors), errors)

    def test_ssot_projectionで本文linkをdependency正本にできない(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/ssot-projection.json"
            ).read_text(encoding="utf-8")
        )["payload"]
        relationship_source = next(
            source
            for source in fixture["sources"]
            if "work-item.dependencies" in source["canonicalFor"]
        )
        relationship_source["sourceKind"] = "issue-body"

        errors = contracts.validate_payload("ssotProjection", fixture, manifest)

        self.assertTrue(
            any("work-item.dependencies must use github-native-relationships" in item for item in errors),
            errors,
        )

    def test_ssot_projectionでcurrent_statusをmerge前分類に流用できない(self) -> None:
        manifest = contracts.load_manifest(ROOT)
        fixture = json.loads(
            (
                ROOT
                / "plugins/engineering-delivery/fixtures/valid/ssot-projection.json"
            ).read_text(encoding="utf-8")
        )["payload"]
        fixture["projections"][0]["purpose"] = "pre-merge-classification"

        errors = contracts.validate_payload("ssotProjection", fixture, manifest)

        self.assertTrue(any("current-status cannot be pre-merge-classification" in item for item in errors), errors)

    def test_templatesとskillsがProject現在値を本文へ複製しない(self) -> None:
        plugin = ROOT / "plugins/engineering-delivery"
        issue = (plugin / "templates/issue-contract.md").read_text(encoding="utf-8")
        pull_request = (plugin / "templates/pr-evidence.md").read_text(encoding="utf-8")

        self.assertIn("現在値はGitHub Projectを正本", issue)
        self.assertNotIn("- Status: `Todo`", issue)
        self.assertIn("Project Classification Snapshot", pull_request)
        self.assertIn("Observed at:", pull_request)
        for skill_name in ("issue-to-pr", "pr-self-review"):
            skill = (
                plugin / "skills" / skill_name / "SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn("native Relationships", skill)
            self.assertIn("observed_at", skill)

    def test_skill_promotion_policy_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__")
            )
            manifest_path = (
                candidate / "plugins/engineering-delivery/contracts/manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["skillPromotionPolicy"]["minimumConsumers"] = 1
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            errors = contracts.validate_contracts(candidate)
            self.assertTrue(any("minimumConsumers" in item for item in errors), errors)

    def test_generated_docs_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            generated = (
                candidate
                / "plugins/engineering-delivery/docs/generated/engineering-delivery-contract.md"
            )
            generated.write_text(generated.read_text(encoding="utf-8") + "\ndrift\n", encoding="utf-8")

            errors = contracts.validate_contracts(candidate)
            self.assertTrue(any("generated contract docs are stale" in error for error in errors))

    def test_release_metadata_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            plugin_version = json.loads(
                (
                    ROOT
                    / "plugins/engineering-delivery/.codex-plugin/plugin.json"
                ).read_text(encoding="utf-8")
            )["version"]
            changelog = candidate / "CHANGELOG.md"
            changelog.write_text(
                changelog.read_text(encoding="utf-8").replace(
                    f"[{plugin_version}]", "[removed]"
                ),
                encoding="utf-8",
            )
            compatibility = candidate / "docs/compatibility.md"
            contract_version = contracts.load_manifest(ROOT)["contractVersion"]
            compatibility.write_text(
                compatibility.read_text(encoding="utf-8").replace(
                    f"contract version `{contract_version}`",
                    "contract version is missing",
                ),
                encoding="utf-8",
            )

            errors = contracts.validate_contracts(candidate)
            self.assertTrue(any("CHANGELOG" in error for error in errors), errors)
            self.assertTrue(any("compatibility declaration" in error for error in errors), errors)

    def test_contract_content_drift_requires_new_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(ROOT, candidate, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            template = (
                candidate
                / "plugins/engineering-delivery/templates/test-intent.md"
            )
            template.write_text(
                template.read_text(encoding="utf-8") + "\nNew normative rule\n",
                encoding="utf-8",
            )

            errors = contracts.validate_contracts(candidate)
            self.assertTrue(any("contractDigest" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
