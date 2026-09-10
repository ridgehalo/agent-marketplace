from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import doctor


class DoctorTest(unittest.TestCase):
    def make_cli(self, directory: Path, name: str, body: str) -> None:
        path = directory / name
        path.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
        path.chmod(0o755)

    def test_source_contract_is_read_back(self) -> None:
        results = doctor.source_checks(
            ROOT, ["engineering-delivery", "android-device-control"]
        )
        self.assertTrue(all(item["status"] == "pass" for item in results), results)

    def test_consumer_profile_pin_is_read_back(self) -> None:
        profile = ROOT / "plugins/engineering-delivery/profiles/personal-consumer.json"
        results = doctor.profile_checks(ROOT, [profile])
        self.assertEqual(results[0]["status"], "pass", results)
        self.assertIn("contractVersion=0.4.0", results[0]["detail"])
        self.assertIn("contractDigest=", results[0]["detail"])
        self.assertIn("contextLock=", results[0]["detail"])

    def test_stale_consumer_profile_pin_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "profile.json"
            source = ROOT / "plugins/engineering-delivery/profiles/personal-consumer.json"
            payload = json.loads(source.read_text(encoding="utf-8"))
            payload["contractVersion"] = "0.0.0"
            profile.write_text(json.dumps(payload), encoding="utf-8")

            results = doctor.profile_checks(ROOT, [profile])
        self.assertEqual(results[0]["status"], "fail", results)
        self.assertIn("contractVersion must match", results[0]["detail"])

    def test_fake_platforms_are_read_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "codex",
                """
                import sys
                if sys.argv[1:] == ["plugin", "list"]:
                    print("engineering-delivery@ridgehalo 0.5.0")
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            self.make_cli(
                bin_dir,
                "claude",
                f"""
                import json
                import sys
                args = sys.argv[1:]
                if args == ["plugin", "marketplace", "list", "--json"]:
                    print(json.dumps([{{"name": "ridgehalo", "path": {str(ROOT)!r}}}]))
                    raise SystemExit(0)
                if args == ["plugin", "list", "--json"]:
                    print(json.dumps([{{
                        "id": "engineering-delivery@ridgehalo",
                        "version": "0.5.0",
                        "scope": "user",
                        "enabled": True
                    }}]))
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.inspect(
                    ROOT, ["codex", "claude"], ["engineering-delivery"]
                )
            self.assertTrue(result["ok"], json.dumps(result, indent=2))

    def test_missing_cli_is_unverified(self) -> None:
        with patch("doctor.shutil.which", return_value=None):
            result = doctor.codex_checks(
                ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
            )
        self.assertEqual(result[0]["status"], "unverified")

    def test_codex_version_must_be_on_matching_plugin_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "codex",
                """
                import sys
                if sys.argv[1:] == ["plugin", "list"]:
                    print("engineering-delivery-old@other 0.1.0")
                    print("foo@ridgehalo 9.9.9")
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.codex_checks(
                    ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
                )
            plugin_check = next(
                item for item in result if item["name"] == "codex-plugin:engineering-delivery"
            )
            self.assertEqual(plugin_check["status"], "fail")

    def test_codex_version_from_other_plugin_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "codex",
                """
                import sys
                if sys.argv[1:] == ["plugin", "list"]:
                    print("other-plugin@other 0.1.0")
                    print("engineering-delivery@ridgehalo version-hidden")
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.codex_checks(
                    ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
                )
            plugin_check = next(
                item for item in result if item["name"] == "codex-plugin:engineering-delivery"
            )
            self.assertEqual(plugin_check["status"], "unverified")

    def test_codex_build_metadata_must_match_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "codex",
                """
                import sys
                if sys.argv[1:] == ["plugin", "list"]:
                    print("engineering-delivery@ridgehalo 0.2.0+other")
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.codex_checks(
                    ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
                )
            plugin_check = next(
                item for item in result if item["name"] == "codex-plugin:engineering-delivery"
            )
            self.assertEqual(plugin_check["status"], "unverified")

    def test_missing_source_is_reported_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = doctor.inspect(
                Path(directory), [], ["engineering-delivery"]
            )
        self.assertFalse(result["ok"])
        self.assertTrue(any(item["status"] == "fail" for item in result["source"]))

    def test_non_object_manifest_is_reported_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "marketplace"
            shutil.copytree(
                ROOT,
                candidate,
                ignore=shutil.ignore_patterns(
                    ".git", "validator-venv", "claude-config", "claude-config-full", "__pycache__"
                ),
            )
            manifest = candidate / "plugins/engineering-delivery/.codex-plugin/plugin.json"
            manifest.write_text("[]\n", encoding="utf-8")
            result = doctor.inspect(candidate, [], ["engineering-delivery"])
        self.assertFalse(result["ok"])
        self.assertTrue(any(item["status"] == "fail" for item in result["source"]))

    def test_claude_marketplace_source_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "claude",
                f"""
                import json
                import sys
                args = sys.argv[1:]
                if args == ["plugin", "marketplace", "list", "--json"]:
                    print(json.dumps([{{"name": "ridgehalo", "path": {str(ROOT.parent / 'other-source')!r}}}]))
                    raise SystemExit(0)
                if args == ["plugin", "list", "--json"]:
                    print(json.dumps([]))
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.claude_checks(
                    ROOT, ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
                )
            source_check = next(
                item for item in result if item["name"] == "claude-marketplace-source"
            )
            self.assertEqual(source_check["status"], "fail")

    def test_stale_claude_version_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bin_dir = Path(directory)
            self.make_cli(
                bin_dir,
                "claude",
                f"""
                import json
                import sys
                args = sys.argv[1:]
                if args == ["plugin", "marketplace", "list", "--json"]:
                    print(json.dumps([{{"name": "ridgehalo", "path": {str(ROOT)!r}}}]))
                    raise SystemExit(0)
                if args == ["plugin", "list", "--json"]:
                    print(json.dumps([{{
                        "id": "engineering-delivery@ridgehalo",
                        "version": "0.0.9",
                        "scope": "user",
                        "enabled": True
                    }}]))
                    raise SystemExit(0)
                raise SystemExit(2)
                """,
            )
            path = f"{bin_dir}:{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": path}, clear=False):
                result = doctor.claude_checks(
                    ROOT, ["engineering-delivery"], {"engineering-delivery": "0.2.0"}
                )
            plugin_check = next(
                item for item in result if item["name"] == "claude-plugin:engineering-delivery"
            )
            self.assertEqual(plugin_check["status"], "fail")


if __name__ == "__main__":
    unittest.main()
