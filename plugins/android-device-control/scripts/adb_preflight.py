#!/usr/bin/env python3
"""Read-only ADB connection preflight with machine-readable output."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any


def parse_devices(output: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in output.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2:
            devices.append(
                {"serial": fields[0], "state": fields[1], "details": fields[2:]}
            )
    return devices


def select_device(
    devices: list[dict[str, Any]], serial: str | None
) -> tuple[bool, str | None, list[dict[str, Any]]]:
    selected = (
        [device for device in devices if device["serial"] == serial]
        if serial
        else devices
    )
    if not selected:
        return False, "expected_device_not_found" if serial else "no_device", selected
    if len(selected) > 1:
        return False, "multiple_devices_require_serial", selected
    if selected[0]["state"] != "device":
        return False, f"device_{selected[0]['state']}", selected
    return True, None, selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="Expected ADB serial when multiple devices are connected")
    args = parser.parse_args()

    if shutil.which("adb") is None:
        print(json.dumps({"ok": False, "reason": "adb_not_found"}))
        return 2

    completed = subprocess.run(
        ["adb", "devices", "-l"], text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        print(
            json.dumps(
                {"ok": False, "reason": "adb_failed", "stderr": completed.stderr.strip()}
            )
        )
        return 2

    devices = parse_devices(completed.stdout)
    ok, reason, selected = select_device(devices, args.serial)
    print(
        json.dumps(
            {"ok": ok, "reason": reason, "selected": selected, "all_devices": devices},
            ensure_ascii=False,
        )
    )
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
