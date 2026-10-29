# Max's Menu

**Professional digital menu boards, without a cloud subscription.**

Max's Menu turns a Raspberry Pi into a menu server for cafés, bakeries, restaurants, and other places that need information on TVs. Create and update menus from a phone or computer on your local network. Each TV displays a webpage using an inexpensive streaming device or other browser, and updates appear within a few seconds.

You can run it on your existing network or, with compatible Wi-Fi hardware, use an optional standalone hotspot that does not require internet access for day-to-day operation.

**Release status:** [v1.0.0-rc3](https://github.com/mogrinz/maxs-menu/releases/tag/v1.0.0-rc3) is the current prerelease, supporting fresh installation and upgrades from RC1/RC2. It adds three-column menu sections, two new default sample menus, full-height column dividers, and configurable currency formatting. The maintainer has tested the new layouts, dividers, and currency controls. See [TESTING_RC3.md](TESTING_RC3.md) when validating your own Pi/player combination.

<!-- IMAGE TODO: Photo of finished multi-screen digital menu board -->

## What can it do?

- Create and edit **10 menus**. Five sample menus are populated so you can explore the system immediately; Menus 4 and 5 demonstrate three-column layouts, and five menus are empty placeholders.
- Provide **10 permanent screen addresses**, one for each logical display (`screen1` through `screen10`). Any number of compatible TVs can point to the same address.
- Display different menus on different TVs, or show the same menu on several TVs.
- **Schedule automatic menu changes** in 30-minute increments: breakfast in the morning, lunch at noon, and dinner later, for example. The TV's URL stays the same.
- Edit items, prices, availability, layouts, colors, and fonts. Displays check for changes approximately every five seconds.
- Choose from **11 locally hosted themes**, including seasonal and scenery designs.
- Use full-width, two-column or three-column sections, optional prices, and an optional food-safety footer.
- Choose the global item currency and regional number format under System. Currency formatting works offline and does not convert prices.
- Rotate an individual menu 0°, 90°, 180°, or 270° to suit your screen orientation.
- Give administrators and employees separate accounts; download history and a system backup.
- Operate on Ethernet, normal Wi-Fi, or an optional local Wi-Fi hotspot, depending on the Pi's networking hardware.

**How the pieces fit together:** one Raspberry Pi runs Max's Menu and publishes the web pages. Each TV has a streaming stick or other browser to display one of those pages. **You do not run an HDMI cable from the Raspberry Pi to each TV.**

## What you'll need

| Item | Quantity | Notes |
| --- | --- | --- |
| Raspberry Pi | 1 | A supported Pi that can run the specified Raspberry Pi OS Lite release. Network via Ethernet and/or supported Wi-Fi hardware. |
| **microSD card (32 GB recommended)** | 1 | For Raspberry Pi OS and Max's Menu. **32 GB, not 32 MB.** Use a reliable card. |
| Pi power supply | 1 | Appropriate to your model of Pi. |
| Network connection | 1 | Ethernet cable, normal Wi-Fi, or a Wi-Fi adapter compatible with hotspot mode. |
| TV or monitor with HDMI | 1 per physical display | An existing TV is fine. |
| Android/Google TV streaming device | 1 per TV, for the approach demonstrated here | Other devices with a suitable browser may work. |
| Internet-connected computer and microSD reader | During installation | To flash Raspberry Pi OS and transfer software. |
| Phone or computer | For administration | Connect it to the same network as the Raspberry Pi. |

**Start on the workbench:** use a spare computer monitor or TV while installing and testing. It is easier to reach the devices, change settings, and check power-cycle recovery before mounting the displays on a wall.

### Recommended streaming device

The example setup uses the **onn. Full HD Streaming Device with Google TV**, sold by Walmart, with **8 GB of storage and 1.5 GB of RAM** (1080p). [Walmart product listing](https://www.walmart.com/ip/2262757145). This is the stick shown in our build; prices and availability can change. Budget approximately **$30 per screen** as a planning estimate, not a guaranteed current price.

<!-- IMAGE TODO: Photo of the onn. Full HD device, its remote, and packaging -->

Other Android/Google TV devices may work, but setup steps vary. Fire TV devices use Android-derived software, but restrictions can make kiosk setup more involved. We recommend reproducing the tested onn. configuration before trying alternatives.

Each streaming device uses **Fully Kiosk Browser & Lockdown**, a third-party Android app ([Google Play listing](https://play.google.com/store/apps/details?id=de.ozerov.fully)). A free version is available; some advanced functions require a paid license. **Confirm your needed full-screen and startup behavior on your device before installing several TVs.** The software on the Pi is independent of this browser app.

### Which network setup should you choose?

| Mode | Good choice when... | Things to know |
| --- | --- | --- |
| **Ethernet / existing LAN** | Your Pi is near a wired network connection. | Usually the simplest and most reliable. Reserve the Pi's IP address in your router so TV bookmarks keep working. |
| **Normal Wi-Fi / existing LAN** | Ethernet is inconvenient but the site already has Wi-Fi. | Uses the existing access point; a stable connection and preferably a reserved IP are important. |
| **Standalone Pi hotspot** | You need a self-contained menu network without site internet. | Requires supported Wi-Fi access-point hardware; range may be limited. The Onn device may warn that the network has no internet. Initial software installation still needs internet. |

A Pi connected to Ethernet can serve TVs across the same LAN; it does not need to generate a hotspot. Wi-Fi capability alone does **not** guarantee that an adapter can operate as an access point. In this release, hotspot mode uses **2.4 GHz, channel 6**, with no internet sharing or 5 GHz hotspot selection.

## 1. Setting up the Raspberry Pi

First, install the operating system onto a microSD card. You'll need [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your Windows, Mac, or Linux computer.

<!-- SCREENSHOT TODO: Raspberry Pi Imager board and OS selections -->

1. Insert the **32 GB microSD card** into your computer and open Raspberry Pi Imager.
2. Select your Pi model and an appropriate **Raspberry Pi OS Lite** image. This release targets **Raspberry Pi OS 13 (Trixie)** with its standard networking configuration. An original Pi Zero W or Model B+ needs **32-bit** Raspberry Pi OS; use a compatible image for other models.
3. Choose the microSD card as the storage device.
4. In Imager's customization settings, choose a hostname (for example `maxsmenu`), a **Pi operating-system username**, and a strong password. Record these.
5. Enable **SSH**, initially using password authentication, to allow setup from your computer.
6. If using normal Wi-Fi, enter your network details and Wi-Fi country. If using Ethernet, connect the Pi to your router or switch before booting.
7. Write the card, insert it into your Pi, connect power, and wait for it to finish booting.

<!-- SCREENSHOT TODO: Raspberry Pi Imager customization, SSH and Wi-Fi screens -->

**Two different logins:** the Pi OS username/password are used for SSH and transferring files. During Max's Menu installation you will create a **separate Max's Menu administrator account**. There is no preconfigured admin password.

### Find the Pi on your network

Try its hostname, such as `maxsmenu.local`. If that doesn't work, find the Pi's IP address in your router's connected-device list or, from a keyboard and screen attached to the Pi, enter:

```bash
hostname -I
```

On a Windows computer, open **PowerShell**, then connect (replace the example name):

```powershell
ssh YOUR_PI_USER@maxsmenu.local
```

If `.local` doesn't resolve, use the actual IP address instead of `maxsmenu.local`. Accept the new-host fingerprint only after confirming you are connecting to the correct Pi; enter the **Pi OS password** when prompted.

## 2. Download and transfer Max's Menu

Download [**maxs-menu.zip**](https://github.com/mogrinz/maxs-menu/releases/download/v1.0.0-rc3/maxs-menu.zip) from [**Releases → Assets**](https://github.com/mogrinz/maxs-menu/releases) and save it in your computer’s Downloads folder. Use this installation ZIP rather than GitHub’s automatically generated source archives.

The repository contains source code; installable ZIPs are release attachments. No committed `dist` directory is needed. Use **`maxs-menu.zip`** rather than GitHub’s automatically generated **Source code (zip)**, whose top-level folder can differ. The installation ZIP always contains a `maxs-menu` folder; the application and release notes record its version.

From **Windows PowerShell on your computer**, substitute your Pi OS username and hostname/IP:

```powershell
$piUser = 'YOUR_PI_USER'
$piAddress = 'maxsmenu.local'  # Or your Pi's numeric IP address
$release = Join-Path $HOME 'Downloads\maxs-menu.zip'
scp "$release" "${piUser}@${piAddress}:~/"
ssh "${piUser}@${piAddress}"
```

`scp` copies the file; `ssh` signs in to the Pi. These commands prompt you for credentials; you don't need to put a password in the command.

**Using a Mac or Linux computer?** Run equivalent `scp` and `ssh` commands from Terminal, with the ZIP path adjusted to your computer.

## 3. Install and configure Max's Menu

The following commands run **on the Raspberry Pi**, after you sign in using SSH. If `sudo` requests a password, enter your **Pi OS account password**.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip unzip
cd ~
```

**Protect an existing installation:** if `~/maxs-menu` already exists, **stop**. Use [UPGRADING.md](UPGRADING.md) or start with a new card. Don't overwrite a configured installation as part of a first-install tutorial.

```bash
test ! -e "$HOME/maxs-menu" || { echo 'STOP: ~/maxs-menu already exists. See UPGRADING.md.'; exit 1; }
unzip maxs-menu.zip
cd ~/maxs-menu
bash setup.sh
```

> **Existing RC1 installation?** Do not extract over your live folder. Use the temporary-directory upgrade procedure in [UPGRADING.md](UPGRADING.md). It detects the current service directory, including an RC1 folder with a version in its name.

The setup script asks for:

| Setting | What it means |
| --- | --- |
| Site name | The business/site name shown on landing and administration pages. |
| Time zone | Used for scheduled menu changes, e.g. `America/New_York`. |
| Optional hotspot | Choose **no** to use your existing wired or Wi-Fi network. |
| Admin username and password | Your **Max's Menu application account**, separate from the Pi OS account. |
| Hotspot name, password, interface and country | Asked only if you enable the optional hotspot feature. |

Passwords are requested twice and are not displayed. Application passwords currently accept **4–64 printable ASCII characters**; hotspot passwords accept **8–63 characters**. Use strong, unique credentials.

**Hotspot installations only:** before enabling the startup service, install the additional components:

```bash
sudo apt install -y hostapd dnsmasq-base
```

Don't manually enable generic `hostapd` or `dnsmasq` services. Max's Menu manages its own hotspot service.

### Start Max's Menu automatically

Stay on your existing network for this step:

```bash
sudo python3 install_service.py
curl http://localhost:8080/health
```

A successful health response includes `"status":"ok"` and version `1.0.0-rc3`. The application will be managed as a startup service so it can run without a keyboard or monitor attached.

## 4. Open the administration interface

From a **phone or computer on the same network**, open:

```text
http://maxsmenu.local:8080/admin
```

Or replace `maxsmenu.local` with the Pi's actual IP address, for example `http://192.168.1.50:8080/admin` (**example only**). Sign in with the **Max's Menu administrator username and password** created during setup, not the Pi OS credentials.

The application starts with **five populated example menus**. You can explore them, change names and prices, try different themes, and see how screen assignments work before creating your own menus.

### What you'll find in the admin interface

- **Edit Menus:** edit items and headers, optional prices, availability, layouts, and the food-safety warning. Administrators can also set each menu’s rotation here.
- **History:** review prior publications, download them, and, as an administrator, restore an earlier collection.
- **My Account:** view the signed-in account; administrators can change their own passwords.
- **Schedule** (administrators): assign a menu to a screen URL during daily time windows. Outside those windows, the screen shows its matching menu number.
- **Theme** (administrators): preview and save one of 11 themes. The selected theme applies to all menus.
- **System** (administrators): review networking, change the schedule timezone, switch network modes where supported, and download or restore system backups. A yellow status background marks the initial network-settings load and clears when the request finishes.
- **Users** (administrators): manage administrator and employee accounts.

For complete editing instructions, see the [User Guide](USER_GUIDE.md).

**Changes are live:** once you save a menu change, display pages poll the Pi approximately every five seconds. You should see the updated price, item, or theme on connected TVs within a few seconds, without re-entering the TV URL.

## 5. Set up the onn. streaming stick and TV

Repeat this section **for every physical TV** that needs its own streaming player.

<!-- SCREENSHOT TODO: Onn device connected to an HDMI port, and Google TV setup screen -->

1. Plug the onn. Full HD Streaming Device into the TV's HDMI input, connect its supplied power adapter, and follow the Google TV initial setup with the remote. During initial setup, use an **internet-connected Wi-Fi network** so you can install the browser app.
2. In Google TV's app search, look for **Fully Kiosk Browser & Lockdown** by Fully Factory Kiosk Solutions. Install it if available on your device. [Google Play page](https://play.google.com/store/apps/details?id=de.ozerov.fully).
3. Open Fully Kiosk Browser. Find the **Start URL** setting and enter the display address assigned to this TV:

   ```text
   http://YOUR_PI_ADDRESS:8080/display/screen1
   ```

   Replace `YOUR_PI_ADDRESS` with the Pi's actual IP or working hostname. For hotspot mode, the address is `192.168.50.1`, giving `http://192.168.50.1:8080/display/screen1`.
4. Enable **full-screen display** and hide browser navigation/address controls if these options are present. The objective is for the menu to occupy the TV, without browser toolbars.
5. In Fully Kiosk's device-management settings, look for **Launch on Boot / Start on Boot** and **Keep Screen On**. Enable the options available in your installation and grant Android permissions the app requests and you are comfortable allowing.
6. Turn the TV and streaming device fully off and back on to **verify** the player reconnects, launches the browser and shows the correct menu without intervention. Merely enabling a startup option is not proof that your Google TV firmware will permit automatic launching.

<!-- SCREENSHOT TODO: Fully Kiosk Start URL, full-screen, and startup settings on the actual onn. stick -->

**For more displays:** change only the end of the URL: `/display/screen2`, `/display/screen3`, and so on through `/display/screen10`. Two or more physical TVs can use **the same** screen URL if you want them to match.

**Example:** three TVs over a counter could point to `screen1`, `screen2`, and `screen3`. Each can show a different menu; a schedule can replace the morning menu at noon without changing any streaming-stick setting.

**Free app vs paid features:** Fully Kiosk is third-party software, not part of Max's Menu. Test the free edition's behavior in your actual configuration. Its extra kiosk/lockdown features may require a license; do not purchase anything until you know which options you need.

## 6. Optional: run without an internet connection (Pi hotspot)

This is useful for a temporary location or a business that prefers an isolated network. It requires a Pi with built-in Wi-Fi or a **compatible USB Wi-Fi adapter that supports access-point mode**. Hotspot capability and range are hardware dependent.

The installer's hotspot option stores a name and password but **does not immediately activate the hotspot**. Keep your ordinary Wi-Fi connection working during initial configuration.

1. In the Max's Menu administration interface, open **System** and select **Switch to Menu Hotspot**.
2. The Pi will create the configured Wi-Fi network. Reconnect your phone or computer to **your new hotspot SSID**.
3. Open `http://192.168.50.1:8080/system` and select **Keep this mode** **within three minutes**. If you do not confirm, the trial is designed to return to the previous Wi-Fi connection.
4. Connect each streaming stick to the new hotspot, then set its Fully Kiosk Start URL to `http://192.168.50.1:8080/display/screen1` (or the desired screen number).
   - After setting up the stick, **Forget** other saved Wi-Fi networks, including the internet-connected network used during initial setup, so it does not choose one of them at startup. If reconnection fails, use the [Onn hotspot auto-connect guide](ONN_WIFI_AUTOCONNECT.md), which includes an [unlisted walkthrough video](https://youtu.be/kLXIXsSObfs).
5. Test a restart of **both** the Pi and the streaming stick. Make sure the menu automatically returns without internet access.

**Important:** the network switch/rollback procedure requires a saved active **normal Wi-Fi** connection. An Ethernet-only Pi doesn't need to switch to hotspot mode. Do not assume hotspot switching will work over every Wi-Fi adapter, or that every player will automatically reconnect to an offline network.

### Troubleshooting offline Google TV devices

Some streaming devices interpret a Wi-Fi network without internet as broken, even when the local menu server is reachable. If yours refuses to stay connected or doesn't reconnect at startup:

- Check that it is connected to the right SSID and that the browser points to `192.168.50.1`, **not** the previous LAN IP.
- Changing automatic date/time settings did not resolve offline Wi-Fi auto-reconnection on the tested Onn device. It is not a confirmed replacement for the successful ADB change. The Pi must separately have the correct time for scheduled menus.
- Run a full power-cycle test after changing settings.
- **Onn auto-connect workaround and video:** If the stick joins the Pi hotspot manually but will not reconnect automatically, follow the [step-by-step Onn Wi-Fi guide](ONN_WIFI_AUTOCONNECT.md) or [watch the supplemental video](https://youtu.be/kLXIXsSObfs). The guide explains how to run the single ADB setting, then connect to the Pi hotspot and **Forget** every other saved Wi-Fi network. The behavior may vary by firmware.

## 7. Backups, upgrading, and help

Under **System**, choose **Download system backup**, and save it **somewhere other than the Pi**. The backup contains application settings and sensitive material such as account password hashes and, if configured, the hotspot password. Keep it private.

A Max's Menu backup is **not** an SD-card image: it does not restore the Raspberry Pi operating system, the Pi OS login, your home Wi-Fi credentials, or SSH configuration.

For an existing installation, don't repeat the fresh-install unzip/move steps over the top of your installed files. Follow [UPGRADING.md](UPGRADING.md). For help with networking, startup, clocks, and recovery, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## More documentation

- [User Guide](USER_GUIDE.md): managing menus, layouts, schedules, rotation, themes, accounts, backups.
- [Upgrading](UPGRADING.md): protecting your data and updating an existing installation.
- [Troubleshooting](TROUBLESHOOTING.md): networking, clocks, startup, and recovery.
- [Onn Wi-Fi hotspot auto-connect guide](ONN_WIFI_AUTOCONNECT.md): video and optional ADB workaround for offline hotspot reconnection.
- [Video rehearsal checklist](VIDEO_WALKTHROUGH.md): clean installation and demonstration sequence.
- [Validation](VALIDATION.md): checks performed and hardware tests outstanding.
- [Release notes](CHANGELOG.md): what changed.

## License

**Max's Menu source code is licensed under the MIT License.** See the included [LICENSE](LICENSE). Third-party fonts and other bundled assets may have their own notices or licenses; see their accompanying documentation. Fully Kiosk Browser is separate third-party software, not covered by Max's Menu's MIT license.

---

## Appendix A: Onn Full HD / Google TV setup notes

This guide uses the onn. Full HD Streaming Device with Google TV, **8 GB storage / 1.5 GB RAM**. On the tested build, the browser launched and the menu returned after power-on over a wired network. Offline hotspot startup also worked after disabling the internet-validation check through ADB. When the Pi and player were power-cycled together, the menu eventually appeared. The exact firmware/build and successful settings still need to be recorded. Before final release, capture screenshots of:

- Google TV version/build and where the viewer can find **Settings → System → About**.
- The actual route to install Fully Kiosk and configure its **Start URL**, full-screen and startup settings.
- Any Google TV **special app permissions** needed for launch-on-boot behavior.
- Power-cycle recovery after the Pi is temporarily unavailable, and after both devices lose power.
- The optional Wi-Fi-without-internet warning and the tested ADB connectivity-check configuration.

**Optional advanced workaround:** The tested configuration used `adb shell settings put global captive_portal_mode 0` to change Android's captive-portal handling. See [ONN_WIFI_AUTOCONNECT.md](ONN_WIFI_AUTOCONNECT.md) for the full initial-network setup, verification, reversal commands, security warning, saved-network cleanup, and the [companion video](https://youtu.be/kLXIXsSObfs). The exact firmware/build still needs to be captured; this is not confirmed for every Onn device.

## Building and publishing

Run `python build_release.py` from a source checkout to create `maxs-menu.zip` in its parent directory. Runtime accounts, menus, environment settings, backups, and Git history are excluded.

The **Publish release** workflow runs tests, builds the installation ZIP, and creates a release for the version in `models.py`. Repository maintainers can run it manually through GitHub Actions, or explicitly request publication with `[release]` in a commit message on `main`. Versions containing a hyphen are marked as prereleases. The workflow refuses to overwrite an existing release.
