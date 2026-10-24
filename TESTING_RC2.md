# RC2 test sequence before GitHub publication

Start with your working RC1 installation. Keep the existing Pi/Onn configuration so the upgrade test proves it is retained. Nothing in this package publishes to GitHub.

## 1. Back up and upgrade RC1

1. Download a System backup to your computer, and note the current editor URL and a few distinctive menu prices/settings.
2. Return to ordinary Wi-Fi or Ethernet. If changing from the hotspot, confirm the normal network mode in System first.
3. Copy the supplied `maxs-menu.zip` to your Pi home folder with SCP.
4. On the Pi, run:

```bash
cd ~
release_dir="$(mktemp -d "$HOME/maxs-menu-release.XXXXXX")"
unzip "$HOME/maxs-menu.zip" -d "$release_dir"
bash "$release_dir/maxs-menu/upgrade.sh"
curl http://localhost:8080/health
```

If your configured port differs, use that port. Expect version **1.0.0-rc2** and `status: ok`. The updater should use your existing service directory, retain data, and create a timestamped backup. No service-file moving or fresh account setup should be necessary for RC1.

## 2. Check what must survive

- Your existing administrator login and employee accounts still work.
- Menus, prices, headers, two-column assignments, rotation, food safety settings, and theme match RC1.
- Schedule rules, application timezone, site name, and normal editor URL remain the same.
- System shows the existing hotspot name and saved password if hotspot support was configured.
- Your existing TV URL continues to show the intended menu.

If any setting resets, stop and send the exact result before changing more settings. Keep the pre-upgrade backup private.

## 3. Check the new UI

1. Open System. The initial “Loading network settings…” message should have a yellow background with dark text. The background should return to normal when loading finishes. Later polling should not flash yellow repeatedly. A phone video or browser network throttling can help catch the initial state if it loads quickly.
2. Open Schedule. The clock should look like `Friday, Dec 18 2026 7:00AM America/New York`, with the actual current day/date/time and your timezone. It should refresh without reloading the page.
3. In System, temporarily save another valid schedule timezone. Check that Schedule’s clock and zone update, then restore the correct timezone. Rule dropdown times should stay unchanged.
4. Sign in as an employee and confirm that System remains unavailable. They must not gain timezone or network administration access.

## 4. Verify a real schedule boundary

Create temporary rules around the next half-hour boundary so one screen changes between two visibly different menus. Leave the player on its usual `/display/screenN` URL, without `?direct=1`.

Confirm the change appears within about five seconds of the boundary. Remove the temporary rules and confirm fallback to the corresponding menu. Use a full system backup if you want to preserve your exact prior rule list for comparison.

## 5. Hotspot and restart regression check

After the ordinary-network checks pass, trial-switch to the hotspot, reconnect, and confirm it. Check the existing name/password, editor, TV display, and SSH/SCP using the Pi’s OS account.

Reboot the Pi and power-cycle the Onn. Confirm the saved mode and menu return. Your existing ADB configuration on the Onn stays on the Onn; RC2 does not change it. Switching the Pi back to ordinary networking should still work.

## 6. Fresh installation on a spare card

Before calling the first public release ready, follow README on a fresh OS card using different OS/application account names and a different site/hotspot name. Prove that no default or private-development account is required, then reboot and check automatic startup. An Ethernet-only run should hide unsupported hotspot controls and still allow backup/timezone settings.

At minimum, complete steps 1–5 before reporting the upgrade result. The fresh-card rehearsal in step 6 verifies the path new viewers will follow.

## 7. Backup recovery

On a spare installation, restore a private RC1 or RC2 system backup. Check the restored administrator login, menus, theme, timezone, schedule, and rotation. Hotspot credentials remain a separate staged application, so restoring content does not immediately disconnect the current network.

## What to report back

- Health response/version and whether RC1 settings were retained.
- Loading-highlight and clock/timezone results.
- Actual schedule-boundary result.
- Hotspot/reboot/player reconnection result.
- Fresh-install and backup-recovery results if completed.

Paste exact errors rather than the contents of private backup/configuration files.
