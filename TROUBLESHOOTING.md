# Troubleshooting

## The editor will not open

Use the Pi’s current IP address if `.local` name resolution fails. Include port `8080` unless you deliberately changed `.menu.env`.

At the Pi console or over SSH:

```bash
hostname -I
systemctl is-active bagel-menu.service
curl http://localhost:8080/health
sudo journalctl -u bagel-menu.service -n 60 --no-pager
```

If localhost works but another device cannot connect, confirm both devices are on the same network and that the router does not isolate clients. An active SSH service does not establish that the web service is running, and vice versa.

## Forgotten application password

The Pi operating-system login and the application login are separate. Another administrator can reset an application password through Users. If no administrator can sign in, use the installation owner’s OS account at the console or through SSH:

```bash
sudo systemctl stop bagel-menu.service
cd ~/maxs-menu
.venv/bin/python reset_admin.py
sudo systemctl start bagel-menu.service
```

The command lists existing administrators, asks which one to reset, and prompts twice for a new password. It re-enables that account and invalidates its existing sessions. It does not create a hidden account or reset menu content. Run it without sudo, as the user who owns the installation. Stop the service first to avoid concurrent writes.

For a lost Pi OS/SSH password, use the operating system’s recovery process or reinstall and restore an application backup. The application cannot recover an OS password.

## Setup was accidentally started twice

An existing configured installation is retained, and setup prints that it has kept the settings. Do not delete `data/` to change a password. Use My Account, Users, or the local recovery command.

If setup was interrupted during its first write, keep a copy of the partial directory before investigating. For a truly unused fresh installation, starting again from a fresh directory/card is simplest. Setup deliberately refuses to overwrite partially populated private data.

## The TV shows an old menu

Publish changes with Save & publish. Connected displays poll about every five seconds. Make sure the TV uses `/display/screenN` without `?direct=1`; the direct parameter is for editor previews that bypass schedules.

A previously loaded display can keep its cached menu when the Pi is unavailable. It cannot receive edits or scheduled switches then. Cached content is a fallback, not a replacement for a working local network. A cold start may still need the Pi to load the page and fonts.

## A scheduled change does not happen

Check the rule’s Screen and Menu selectors, the application timezone, and the live Pi clock shown on Schedule. Change the schedule timezone through **System → Schedule timezone**. That setting is separate from the OS timezone and does not correct an inaccurate clock. The server chooses the menu using its own clock. The stick’s clock does not determine the schedule.

A start time is included and an end time is excluded. An overnight rule continues into the following morning. Rules repeat daily. Outside a rule, the screen uses its matching menu number.

Inspect OS time:

```bash
date
timedatectl status
```

While connected to the internet, enable time synchronization and wait for synchronization:

```bash
sudo timedatectl set-ntp true
```

For an intentionally offline Pi without a working real-time clock, set the correct current time locally after a power interruption. For example, substitute the actual date and local time:

```bash
sudo timedatectl set-ntp false
sudo timedatectl set-time 'YYYY-MM-DD HH:MM:SS'
```

The OS timezone determines how that manual time string is interpreted. Configure it correctly with `sudo raspi-config` or specify the intended timezone through `timedatectl`. The application separately uses the IANA timezone entered during setup. Verify the displayed time afterward.

For dependable schedules during long-term offline use across power failures, use an appropriate battery-backed real-time clock or another reliable time source. The original Pi Zero W and Model B+ do not gain a battery-backed clock just by installing this software.

## Hotspot controls are missing

They are hidden when hotspot support was not enabled during setup, the selected interface is missing, or its driver reports no AP capability. Ethernet-only operation is supported.

```bash
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status
```

For the actual selected Wi-Fi interface, check AP support:

```bash
nmcli -f WIFI-PROPERTIES.AP device show wlan0
```

Replace `wlan0` if your configured interface has another name. Dual-band reception does not automatically mean a USB adapter supports Linux AP mode. This release’s backend remains 2.4 GHz on channel 6; a dual-band adapter will not automatically turn it into a 5 GHz hotspot.

## Hotspot connection or switching fails

Use a local console if switching has made remote access unavailable. Do not repeatedly switch while a trial is pending.

```bash
systemctl is-active NetworkManager
systemctl status maxs-menu-network.service --no-pager
systemctl status maxs-menu-hotspot.service --no-pager
sudo journalctl -u maxs-menu-network.service -u maxs-menu-hotspot.service -n 100 --no-pager
```

A failed/unconfirmed trial returns to the prior saved Wi-Fi connection after three minutes. Rejoin that network and use its assigned IP address. If a confirmed hotspot is active, connect to the chosen SSID and use `http://192.168.50.1:8080/admin`, including `http://` and the port.

Use System’s Show password checkbox to compare the actual saved Wi-Fi password. Save a changed password before switching. A saved password does not need to be re-entered for every switch.

The hotspot intentionally has no internet. Android/Google TV devices may require choosing to stay connected, and their auto-reconnection behavior varies. This candidate does not spoof Android validation or force a streaming device’s network policy. Verify Wi-Fi reconnection and kiosk/browser auto-launch with your exact Onn model and firmware.

## SSH connects but interactive typing is extremely slow

First compare local-console responsiveness with SSH and check network signal/loss. A responsive local console does not prove every network path is healthy.

A diagnostic for networks that mishandle SSH traffic priority is:

```text
ssh -o IPQoS=none YOUR_PI_USER@YOUR_PI_ADDRESS
```

If that does not help, a server-side diagnostic may also be needed. Do not assume the problem is CPU load or rewrite hotspot settings without evidence.

If testing establishes that disabling SSH traffic priority fixes the problem, the Pi’s SSH server can use an `IPQoS none` configuration drop-in. Validate SSH configuration with `sudo /usr/sbin/sshd -t` before reloading the service, and retain an existing session/local console until a new session succeeds. This release does not modify SSH configuration automatically.

## TV colors differ from the desktop

The display includes `color-scheme: only light` and explicit theme colors. Look for forced darkening, accessibility color inversion, or browser-specific rendering on the player. A browser may still override page preferences. Try the same URL in another browser on that device to distinguish browser behavior from TV settings.

## Text is too small or clipped

Preview the saved menu, then view it at the actual TV size and customer distance. Reduce item count, shorten descriptions, or split content among menus. Automatic fitting has a minimum font size and cannot guarantee readable text for unlimited content.

Use matching rotation settings for menus scheduled onto the same physically rotated display. A menu’s food safety footer takes space in the fitted layout.

## Backup restore was rejected

Use a compatible full system backup (format version 2), not a menu-only export. The restore preview validates accounts, content, themes, settings, and schedules. At least one enabled administrator must remain in the backup. A changed file or changed installation after preview requires a new preview.

Menu-only imports accept the current ten-menu schema. Full private-prototype backups are intentionally not supported by this clean-install candidate. Keep those originals separately. Upgrades and system backups from the public RC1 release are supported.

## Upgrade failed

Read [UPGRADING.md](UPGRADING.md). The updater leaves a private timestamped application/data copy for manual rollback, but does not automatically undo every installation command. Preserve the error message, examine the service journal, and keep the backup private.
