---
name: android-device-control
description: Debug an Android application on a user-authorized physical device over ADB by reproducing issues, collecting scoped logs and UI evidence, controlling the app, and verifying fixes. Use for apps the user owns or is authorized to test; do not use for unrelated third-party apps, iOS, lock bypass, or credential extraction.
---

# Android Device Control

Use ADB as a controlled debugging and UI automation channel for an application the user owns or is authorized to test. Prefer observable app behavior over direct edits to app storage.

## Before operating

- When setup or connection troubleshooting is needed, read [references/setup.md](references/setup.md).
- Run `scripts/adb_preflight.py`. Continue only with exactly one `device`-state target, or an explicitly selected serial. Stop on `unauthorized`, `offline`, multiple ambiguous devices, or a changed serial.
- Read the project instructions and identify the intended build, package, launch activity, reproduction steps, expected behavior, and allowed device. Stop if the foreground package or build identity cannot be matched.
- Keep logs and screenshots scoped to the target app. Do not print tokens, notification bodies, unrelated screen content, production customer data, or identifiers that are not needed for diagnosis.
- Read-only inspection is safe to begin. Before installing or replacing a build, clearing app data, changing permissions or system settings, or operating outside the target app, present one named Human Gate with the exact scope. Approval covers only that scope.

## Operate and verify

1. Wake the device without bypassing its lock. Confirm the device, installed package version, foreground package, activity, and current screen.
2. Reproduce the issue from a stated initial condition. Capture the smallest useful evidence: package-scoped logcat, exception or ANR, UI hierarchy, screenshot, app process state, and exact reproduction step.
3. Prefer resource IDs, text, and content descriptions from `uiautomator dump --compressed`. Use coordinates only after verifying resolution, orientation, target identity, and current bounds.
4. For custom-rendered UIs, corroborate identity with a screenshot or OCR before tapping a mutating control. Never reuse a stale UI dump.
5. After a code or configuration change, deploy only the user-approved build, restart from the same initial condition, repeat the reproduction, and compare the same evidence.
6. Distinguish a locally observed UI result, process stability, network response, and backend persistence. Never infer one from another.

When UIAutomator reports `could not get idle state`, pause active media, retry with a fresh remote XML path, and then fall back to a screenshot plus OCR. Never reuse stale XML. Platform-native OCR is suitable when titles are absent from the accessibility tree.

Use PID- or package-scoped log collection where possible, and bound every capture by time or reproduction step. Do not leave broad `logcat` collection running. Treat app uninstall, reinstall, data clearing, permission reset, and database inspection as mutations; explain their effect and preserve recoverable state unless the user approves otherwise.

## Device settings

Read current values before proposing a change. For settings such as screen timeout or stay-awake-while-plugged-in, show the exact key, value, and reversibility in the Human Gate, apply the smallest change, then read the value back. Do not weaken PIN, biometric, device-policy, or lock-screen security.

## Completion evidence

Report the device/build identity, reproduction result, evidence collected, diagnosed cause or remaining hypotheses, mutations performed, and fix-verification result separately. Do not claim a native-device fix from browser, simulator, build, or install evidence alone. Stop with a visible reason if the target app, build, or device state cannot be verified.
