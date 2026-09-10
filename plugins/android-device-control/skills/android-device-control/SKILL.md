---
name: android-device-control
description: Inspect, debug, and safely operate a user-authorized Android phone over ADB, including app navigation, screenshots, UI hierarchy, device settings, and verified account-sensitive migrations. Do not use for iOS, lock bypass, credential extraction, DRM circumvention, or direct manipulation of protected app data.
---

# Android Device Control

Use ADB as a controlled UI automation channel. Prefer observable app behavior over direct edits to app storage.

## Before operating

- When setup or connection troubleshooting is needed, read [references/setup.md](references/setup.md).
- Run `scripts/adb_preflight.py`. Continue only with exactly one `device`-state target, or an explicitly selected serial. Stop on `unauthorized`, `offline`, multiple ambiguous devices, or a changed serial.
- Record the package, account-facing display name, target items or settings, intended mutations, and exclusions. Do not print email addresses, tokens, notification bodies, or unrelated screen content.
- Read-only inspection is safe to begin. Before an account switch, deletion, purchase, permission or system-setting change, or third-party-app write, present one named Human Gate with the exact scope. Approval covers only that scope.

## Operate and verify

1. Wake the device without bypassing its lock. Confirm the foreground package, activity, and current screen.
2. Prefer resource IDs, text, and content descriptions from `uiautomator dump --compressed`. Use coordinates only after verifying resolution, orientation, target identity, and current bounds.
3. For media pages or custom-rendered UIs, corroborate identity with `dumpsys media_session`, a screenshot, or OCR before tapping a mutating control.
4. After each mutation, read the resulting UI state. For batches, restart or reopen the app and read the destination list or setting back.
5. Distinguish button-state confirmation, list membership, completed transfer or download, and cloud persistence. Never infer one from another.

When UIAutomator reports `could not get idle state`, pause active media, retry with a fresh remote XML path, and then fall back to a screenshot plus OCR. Never reuse stale XML. Platform-native OCR is suitable when titles are absent from the accessibility tree.

For account-sensitive work, identify accounts only by a user-approved display label. Preserve the source unless deletion was explicitly approved. Never copy encrypted, offline, or DRM media files; trigger the official app's download flow and verify its account-specific result.

## Device settings

Read current values before proposing a change. For settings such as screen timeout or stay-awake-while-plugged-in, show the exact key, value, and reversibility in the Human Gate, apply the smallest change, then read the value back. Do not weaken PIN, biometric, device-policy, or lock-screen security.

## Completion evidence

Report device identity, active account label, successful mutations, failed or skipped items, app-list readback, and device evidence separately. Stop with a visible reason if identity or state cannot be verified.
