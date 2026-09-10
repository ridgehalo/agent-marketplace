# Android ADB setup

Read this reference only when preparing or troubleshooting a workstation and device connection.

## Workstation and phone

1. Install Android SDK Platform Tools from Google. Package managers such as Homebrew may provide `android-platform-tools` on macOS.
2. Use a data-capable USB cable. On the phone, enable Developer options and USB debugging.
3. Connect the phone, verify the host fingerprint, and accept the phone's RSA authorization prompt.
4. Run `adb devices -l`; the target must be in `device` state.
5. With multiple devices, select an explicit serial and pass `-s SERIAL` to every ADB command.

Useful read-only commands:

```sh
adb devices -l
adb shell wm size
adb shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
adb shell dumpsys package APP_PACKAGE
adb shell pidof APP_PACKAGE
adb logcat --pid APP_PID
adb shell uiautomator dump --compressed /sdcard/window.xml
adb exec-out cat /sdcard/window.xml
adb shell screencap -p /sdcard/screen.png
adb pull /sdcard/screen.png ./screen.png
adb shell dumpsys power
```

Typical UI actions are `adb shell input tap X Y`, `swipe`, `text`, and `keyevent`. Treat them as writes when they change target application state.

Installing a debug build, clearing application data, changing permissions, or resetting the application requires approval because it can replace or destroy device state:

```sh
adb install -r ./app-debug.apk
adb shell pm clear APP_PACKAGE
adb shell pm grant APP_PACKAGE ANDROID_PERMISSION
```

Prefer a time-bounded or PID-scoped `logcat` capture around one reproduction. Do not retain unrelated application logs or production user data.

Optional keep-awake settings require approval before applying:

```sh
adb shell settings get system screen_off_timeout
adb shell settings get global stay_on_while_plugged_in
adb shell settings put system screen_off_timeout 300000
adb shell settings put global stay_on_while_plugged_in 2
```

Read both keys back after any change. Value `2` means USB power only. Capture original values before changing them so they can be restored when requested.

## iOS boundary

ADB is Android-specific. Physical iPhone automation normally requires macOS, Xcode, device pairing and trust, Developer Mode, and a signed XCTest, XCUITest, or WebDriverAgent runner, optionally orchestrated by Appium. iOS provides no equivalent general shell and deliberately limits introspection and protected third-party app data.
