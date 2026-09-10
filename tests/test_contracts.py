from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_repository


class ContractValidationTest(unittest.TestCase):
    def test_repository_contract_is_valid(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_version_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            manifest_path = (
                candidate
                / "plugins/engineering-delivery/.claude-plugin/plugin.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "9.9.9"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            errors = validate_repository(candidate)
            self.assertTrue(any("versions differ" in error for error in errors), errors)

    def test_marketplace_plugin_set_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            manifest_path = candidate / ".agents/plugins/marketplace.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["plugins"] = manifest["plugins"][:1]
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            errors = validate_repository(candidate)
            self.assertTrue(any("plugin set mismatch" in error for error in errors), errors)

    def test_local_absolute_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / "unsafe.md"
            unsafe_path = "/" + "Users/example/private"
            unsafe.write_text(f"local path: {unsafe_path}\n", encoding="utf-8")
            errors = validate_repository(candidate)
            self.assertTrue(any("local absolute path" in error for error in errors), errors)

    def test_json_secret_assignment_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / "unsafe.json"
            unsafe.write_text(
                '{"api_' + 'key": "example-secret"}\n', encoding="utf-8"
            )
            errors = validate_repository(candidate)
            self.assertTrue(any("secret-like assignment" in error for error in errors), errors)

    def test_unlisted_text_extension_secret_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / ".env"
            unsafe.write_text("API_" + "KEY=example-secret\n", encoding="utf-8")
            errors = validate_repository(candidate)
            self.assertTrue(any("secret-like assignment" in error for error in errors), errors)

    def test_generic_credential_assignments_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / ".env"
            keys = [
                "TO" + "KEN",
                "GITHUB_" + "TO" + "KEN",
                "AUTH_" + "TO" + "KEN",
                "COO" + "KIE",
                "SESSION_" + "ID",
            ]
            for key in keys:
                with self.subTest(key=key):
                    unsafe.write_text(f"{key}=example-secret\n", encoding="utf-8")
                    errors = validate_repository(candidate)
                    self.assertTrue(
                        any("secret-like assignment" in error for error in errors), errors
                    )

    def test_known_token_value_is_rejected_without_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / "unsafe.txt"
            unsafe.write_text("value " + "ghp_" + ("a" * 30) + "\n", encoding="utf-8")
            errors = validate_repository(candidate)
            self.assertTrue(any("token-like value" in error for error in errors), errors)

    def test_common_local_absolute_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            unsafe = candidate / "unsafe.txt"
            paths = [
                "/" + "home/example/private.txt",
                "/" + "private/" + "tmp/private.txt",
                "C:" + "\\" + "Users" + "\\" + "example" + "\\" + "private.txt",
            ]
            for local_path in paths:
                with self.subTest(local_path=local_path):
                    unsafe.write_text(local_path + "\n", encoding="utf-8")
                    errors = validate_repository(candidate)
                    self.assertTrue(
                        any("local absolute path" in error for error in errors), errors
                    )


if __name__ == "__main__":
    unittest.main()
