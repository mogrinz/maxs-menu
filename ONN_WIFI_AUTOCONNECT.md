# Onn streaming stick: Wi-Fi hotspot auto-connect workaround

**[Watch the companion step-by-step video](https://youtu.be/kLXIXsSObfs)**

## When to use this

If your Onn streaming stick connects manually to a Raspberry Pi running Max's Menu in hotspot mode but does **not** reconnect automatically after a restart, the following optional workaround may help. It was used on the project's Onn setup with a **2.4 GHz hotspot and no internet access**. The exact Android build and behavior on other Onn models are not yet documented. A 5 GHz hotspot has **not** been tested; the current Max's Menu release uses **2.4 GHz, channel 6**, not 5 GHz.

The suspected cause is Android's internet/captive-portal checks, but that cause is not confirmed. Changing automatic date/time did not fix the problem in the tested setup. The workaround changes an **Android system-wide setting**; it does not add internet access to the Pi hotspot. If automatic reconnection already works, skip these steps.

## 1. Start on your normal Wi-Fi network

Before changing anything, connect **both the computer and the Onn stick to the same existing Wi-Fi network** (ideally with internet access). Do **not** forget this network yet: it is used for ADB configuration. If your router isolates wireless clients, ADB connections may fail even when both devices appear on the same Wi-Fi.

## 2. Download Android Platform Tools

Download and extract the official [Android SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) for Windows, macOS, or Linux. Open a terminal in the extracted `platform-tools` directory. Commands below run **on your computer**, not on the Raspberry Pi.

## 3. Enable developer and debugging options

On the Onn stick, open **Settings > System > About**. Highlight **Android TV OS Build** and press Select **seven times**, until developer mode is enabled.

Return to **Settings > System > Developer options** and enable **ADB debugging** or **Wireless debugging**, depending on the firmware. Menu labels may differ by device.

## 4. Connect from your computer using ADB

Find the Onn stick's IP address in its **Network & Internet** settings. For firmware supporting direct network ADB, run (substituting your Onn's IP):

```sh
adb connect 192.168.1.125
adb devices
```

Accept the debugging authorization prompt on the Onn stick, if shown. `adb devices` should show the stick with status `device`, not `unauthorized`.

Some Android versions require **Wireless debugging pairing** instead. Use the pairing IP/port and code displayed by the stick, then connect using the *debugging* port displayed there (which may differ from the pairing port):

```sh
adb pair <ONN_IP>:<PAIRING_PORT>
adb connect <ONN_IP>:<DEBUG_PORT>
adb devices
```

If the connection fails, check that both devices are on the same reachable network, debugging is enabled, and you used the correct IP/port.

## 5. Apply and verify the workaround

Run this **single** command on your computer:

```sh
adb shell settings put global captive_portal_mode 0
```

Verify the value:

```sh
adb shell settings get global captive_portal_mode
```

Expected output: `0`. This confirms the setting was written, **not** that auto-connect will necessarily work on your firmware. No second, deprecated captive-portal command is needed.

## 6. Enable the Raspberry Pi hotspot

In the Max's Menu administration interface, open **System** and choose **Switch to Menu Hotspot**. The Pi will broadcast the configured hotspot SSID. Reconnect your phone/computer to that hotspot and visit **http://192.168.50.1:8080/system** to select **Keep this mode** within the three-minute confirmation window. Otherwise the Pi is designed to revert to its previous Wi-Fi mode.

The current release uses a **2.4 GHz hotspot on channel 6**. The hotspot deliberately has **no internet access**. Ensure it is active before changing the stick's saved networks.

## 7. Connect the Onn stick to the Pi and forget other Wi-Fi networks

On the stick, open **Settings > Network & Internet**, select your **Pi hotspot SSID**, and enter its password. A **No internet** indication is expected; the menu is served locally.

Once connected, go through the stick's **saved Wi-Fi networks** and select **Forget** for *every other network*, including the normal network you used for ADB earlier. Leave **only the Pi hotspot** saved. This reduces the chance the stick selects another available network on startup. Forgetting the original network will terminate the earlier ADB connection; that is expected.

Set the Fully Kiosk Browser Start URL to:

```text
http://192.168.50.1:8080/display/screen1
```

Change `screen1` to the appropriate screen number for that TV.

## 8. Test unattended startup

Reboot the Onn stick and confirm it reconnects to the Pi hotspot and loads the menu. Then **remove power and restore it**, repeating several times. Also test turning on the Pi and the Onn stick together, and starting the stick before the hotspot is available. Check both Wi-Fi reconnection **and** Fully Kiosk automatic launch separately.

If it still fails, verify the Pi hotspot is running and confirmed, check the SSID/password, confirm the stick saved only the hotspot, and check that the browser uses `192.168.50.1` rather than the Pi's old LAN address. See [Troubleshooting](TROUBLESHOOTING.md) for Pi network-switching diagnostics.

## Undo the change and security notes

To restore Android's standard captive-portal handling, reconnect via ADB on a reachable network and run:

```sh
adb shell settings put global captive_portal_mode 1
```

Or remove the override entirely to allow device defaults:

```sh
adb shell settings delete global captive_portal_mode
```

Disabling captive-portal checks changes behavior for **all** networks on that stick; Android may not detect public Wi-Fi login portals or some internet-connectivity problems normally. Disable ADB/Wireless debugging after configuration if you do not need it. Firmware updates could change these behaviors. This is an **optional tested workaround, not a universal fix**.

**Companion video:** https://youtu.be/kLXIXsSObfs
