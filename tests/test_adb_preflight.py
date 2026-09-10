from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "plugins/android-device-control/scripts/adb_preflight.py"
)
SPEC = importlib.util.spec_from_file_location("adb_preflight", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
adb_preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adb_preflight)


class AdbPreflightTest(unittest.TestCase):
    def test_single_authorized_device_is_selected(self) -> None:
        devices = adb_preflight.parse_devices(
            "List of devices attached\nemulator-5554 device product:sdk model:phone\n"
        )
        ok, reason, selected = adb_preflight.select_device(devices, None)
        self.assertTrue(ok)
        self.assertIsNone(reason)
        self.assertEqual(selected[0]["serial"], "emulator-5554")

    def test_multiple_devices_require_explicit_serial(self) -> None:
        devices = adb_preflight.parse_devices(
            "List of devices attached\nfirst device\nsecond device\n"
        )
        ok, reason, _ = adb_preflight.select_device(devices, None)
        self.assertFalse(ok)
        self.assertEqual(reason, "multiple_devices_require_serial")

        ok, reason, selected = adb_preflight.select_device(devices, "second")
        self.assertTrue(ok)
        self.assertIsNone(reason)
        self.assertEqual(selected[0]["serial"], "second")

    def test_unauthorized_and_offline_devices_fail_closed(self) -> None:
        for state in ("unauthorized", "offline"):
            with self.subTest(state=state):
                ok, reason, _ = adb_preflight.select_device(
                    [{"serial": "example", "state": state, "details": []}], None
                )
                self.assertFalse(ok)
                self.assertEqual(reason, f"device_{state}")

    def test_missing_device_or_serial_fails_closed(self) -> None:
        self.assertEqual(
            adb_preflight.select_device([], None)[:2], (False, "no_device")
        )
        self.assertEqual(
            adb_preflight.select_device(
                [{"serial": "present", "state": "device", "details": []}],
                "missing",
            )[:2],
            (False, "expected_device_not_found"),
        )


if __name__ == "__main__":
    unittest.main()
