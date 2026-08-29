from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bootstrap


class BootstrapTest(unittest.TestCase):
    def test_default_plugin_is_selective(self) -> None:
        self.assertEqual(bootstrap.select_plugins(None), ["engineering-delivery"])
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.select_plugins(["unknown-plugin"])

    def test_all_target_builds_both_platform_commands(self) -> None:
        commands = bootstrap.build_commands(
            ROOT, ["codex", "claude"], ["engineering-delivery"], "user"
        )
        self.assertEqual(commands[0][:4], ["codex", "plugin", "marketplace", "add"])
        self.assertEqual(
            commands[1],
            ["codex", "plugin", "add", "engineering-delivery@ridgehalo"],
        )
        self.assertEqual(commands[2][0:4], ["claude", "plugin", "marketplace", "add"])
        self.assertEqual(
            commands[3],
            [
                "claude",
                "plugin",
                "install",
                "engineering-delivery@ridgehalo",
                "--scope",
                "user",
            ],
        )

    def test_all_target_preflight_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake_claude = Path(directory) / "claude"
            fake_claude.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_claude.chmod(0o755)
            with patch.dict(os.environ, {"PATH": directory}, clear=False):
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.preflight_binaries(["codex", "claude"])

    def test_codex_deeplink_points_to_marketplace_manifest(self) -> None:
        deeplink = bootstrap.codex_deeplink(ROOT, "engineering-delivery")
        self.assertTrue(deeplink.startswith("codex://plugins/engineering-delivery?"))
        self.assertIn("marketplace.json", deeplink)

    def test_command_output_redacts_tokens(self) -> None:
        output = bootstrap.SENSITIVE_OUTPUT.sub(
            r"\1[REDACTED]", "Authorization: " + "Bearer " + "example-secret"
        )
        self.assertNotIn("example-secret", output)


if __name__ == "__main__":
    unittest.main()
