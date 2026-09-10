---
name: android-device-operations
description: Operate a user-authorized Android device and its apps over ADB for explicit personal workflows such as navigation, settings, screenshots, and account or data migration. Do not use for application debugging, lock bypass, credential extraction, DRM circumvention, or direct extraction of protected app data.
---

# Android Device Operations

Use ADB to carry out an explicit workflow on a device the user has authorized. Treat the device UI and official application flows as the source of truth; do not manipulate protected application storage to imitate an outcome.

## Establish the operating boundary

- When setup or connection troubleshooting is needed, read [the shared setup reference](../../references/setup.md).
- Run `../../scripts/adb_preflight.py`. Continue only with exactly one `device`-state target, or an explicitly selected serial. Stop on `unauthorized`, `offline`, multiple ambiguous devices, or a changed serial.
- Confirm the target device, foreground package and activity, current screen, requested outcome, permitted accounts or display labels, and exclusions. Keep the source account read-only unless the user explicitly approves a source-side mutation.
- Read-only inspection may begin without a mutation gate. Before an account switch, external write, purchase, deletion, permission or system-setting change, install, uninstall, data clear, or other state-changing action, present one named Human Gate with the exact target, scope, exclusions, expected effect, and reversibility. Approval covers only that gate.
- Do not bypass a lock screen, PIN, biometric check, device policy, app authentication, purchase confirmation, or service security control. Pause for the user whenever personal authentication or an informed confirmation must be completed by them.

## Operate through observable UI

1. Read the current UI before acting. Prefer resource IDs, text, and content descriptions from a fresh `uiautomator dump --compressed`.
2. Use coordinates only after verifying resolution, orientation, target identity, and current bounds. Never reuse coordinates or XML after the screen changes.
3. For custom-rendered or media UIs, corroborate controls with a screenshot or OCR. Use media-session state only when it helps identify the active media flow.
4. Perform the smallest approved action, then read the resulting screen or system value back before continuing.
5. When an item or account is ambiguous, stop rather than choosing by position, avatar, or partial label alone.

## Account, data, and media workflows

- Use only user-approved account display labels and the official app or service UI. Do not expose email addresses, tokens, session state, notification contents, or unrelated application data in logs or public evidence.
- Never copy, decrypt, export, or reconstruct protected app storage, encrypted databases, offline media files, or DRM-controlled content. For offline downloads and transfers, use the service's supported application flow and report platform limitations explicitly.
- Distinguish a tapped control, a visible state change, list membership, a completed download or transfer, and server-side persistence. One does not prove the others.
- Do not assume that matching counts means matching content. When practical, verify stable visible identifiers without publishing personal history.

## Device settings

Read the current value first, propose the smallest reversible change, apply it only after its Human Gate, and read it back. Record enough information to restore the original value when requested. Never weaken PIN, biometric, device-policy, or lock-screen security.

## Completion evidence

Report each requested outcome as successful, failed, or skipped, with its read-back evidence and any remaining manual action. Separate local UI observation from device storage state and cloud persistence. If the device, account, target item, or completion state cannot be verified, stop with a visible reason instead of claiming success.
