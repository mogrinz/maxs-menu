# Fresh-install rehearsal for the video

This is a review checklist, not a scheduled reminder. Use a new SD card/image so the audience sees the same path you test.

1. **Explain the architecture.** The Pi hosts the editor and menu pages. Each TV uses a browser/player on the same local network. Internet is needed for initial package downloads, not ordinary local menu delivery.
2. **Flash stock Raspberry Pi OS Lite.** Select the correct 32/64-bit image for the board. Choose your own hostname and OS login; enable SSH; configure normal Wi-Fi or use Ethernet. Do not record a real password on screen.
3. **Transfer the ZIP.** Demonstrate the exact PowerShell variables and commands in README, using values chosen for the video.
4. **Run setup.** Extract into `~/maxs-menu`, install dependencies, and run `bash setup.sh`. Show the site name, timezone, application administrator choice, and optional hotspot questions. Explain the difference between OS, application, and hotspot credentials.
5. **Install startup.** Run `sudo python3 install_service.py`, check `/health`, and reboot once. Verify the app returns without manually starting Python.
6. **Open the sample.** Sign in with your chosen application account. Show Menus 1–3 populated and Menus 4–10 empty.
7. **Edit.** Change an item, description, and price. Add a header, demonstrate two columns, reorder, and publish. Show the matching public screen URL on the TV.
8. **Rotate.** Set a menu to 90° and save. Confirm the entire display and footer fit. Restore the appropriate orientation for the video setup.
9. **Schedule.** Add rules that move Screen 1 among Menus 1, 4, and 5. Keep the TV on `/display/screen1`. Check the clock/timezone and deliberately cross a real boundary during rehearsal.
10. **Theme.** Preview the five new themes and save one. Confirm the actual streaming stick does not recolor it.
11. **Accounts.** Create an employee and demonstrate restricted navigation. Explain equal administrator rights and the documented local password reset. Do not introduce any hidden recovery account.
12. **Backup.** Download a system backup off-device. Restore onto a separate fresh installation; prove the restored administrator, menu, rotation, schedule, and theme work. Do not publish the backup or show its contents in the video.
13. **Optional hotspot.** Only if included in the video: verify adapter/AP support, trial-switch, reconnect, confirm, and test a reboot. Test Onn power cycling and offline Wi-Fi reconnection separately. This review candidate retains 2.4 GHz hostapd and provides no internet sharing/spoofing.
14. **Upgrade rehearsal.** Export a backup, return to ordinary networking, and extract `maxs-menu.zip` into a temporary folder before running `upgrade.sh`. Verify settings and existing login survive. First test an upgrade from RC1 in its actual service directory. Confirm that the existing accounts, menus, theme, rotation, schedules, timezone, and hotspot identity remain available.
15. **Publication check.** Publish only this clean source tree after reviewing the included MIT license and package audit. Do not upload a configured SD image, private backup, populated `data/`, `.menu.env`, or old prototype archives. Add the final video link to README once it exists. Use the RC2 hardware acceptance checklist in TESTING_RC2.md before publishing.

Before calling it a stable release, leave the actual Pi and TV players running through several schedule boundaries and perform complete power-off/restart tests. Automated browser checks cannot establish real Wi-Fi reconnection reliability.
