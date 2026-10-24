# Upgrading Max’s Menu

## Supported starting point

**RC1 and later public releases are supported.** Earlier private development prototypes are outside this upgrade path. New installations use the fresh-install instructions in README.

RC2 does not add migration work for those private prototypes. It preserves a working RC1 installation’s accounts, menus, themes, schedules, rotations, timezone, port, and network configuration. If your earlier RC1 installation needed its prototype network configuration corrected, retain that working configuration.

## Before upgrading

1. In **System**, download a system backup and save it off the Pi.
2. Note your existing editor URL and current version.
3. Switch to Ethernet or your saved ordinary Wi-Fi, with internet available for dependency installation. Confirm that mode in System before proceeding. Do not upgrade through the active menu hotspot.
4. Keep the previous release ZIP and your OS login credentials.

## Copy and extract the new package safely

Copy **`maxs-menu.zip`** to your Pi’s home directory using SCP. Do not unzip it over your live installation: the ZIP always contains a `maxs-menu` folder.

Run the following on the Pi, signed in as the OS user who owns the installation:

```bash
cd ~
release_dir="$(mktemp -d "$HOME/maxs-menu-release.XXXXXX")"
unzip "$HOME/maxs-menu.zip" -d "$release_dir"
bash "$release_dir/maxs-menu/upgrade.sh"
```

The script reads the existing `bagel-menu.service` working directory and updates that directory. This also supports an RC1 installation in a version-named folder. It does not relocate your installation or create a new application login.

To inspect the selected directory beforehand:

```bash
systemctl show bagel-menu.service -p WorkingDirectory --value
```

If the service has not been installed, pass the actual existing RC1 application directory explicitly:

```bash
bash "$release_dir/maxs-menu/upgrade.sh" /absolute/path/to/your/rc1-installation
```

A target without existing account and menu state is rejected. If the downloaded release was extracted into the live directory accidentally, stop and recover from backup rather than attempting to use the updater on itself.

## What the updater does

1. Checks normal-network connectivity and required network dependencies.
2. Stops the application service and any manual server owned by your user in the target directory.
3. Saves a private timestamped prior application/data copy under a sibling `maxs-menu-backups/` folder.
4. Copies new code while keeping `data/`, `.menu.env`, and `.venv`.
5. Installs pinned Python dependencies and validates the existing site settings without repeating first-time setup.
6. Updates the restricted root service helpers while preserving the existing RC1 controller configuration and hotspot profile/password.
7. Restarts the application and checks that `/health` reports the new release version.

The application service name stays `bagel-menu.service`. Because the target directory stays the same, the existing service is accepted by the installer. There is no need to move or delete that service definition for a normal RC1 upgrade.

| Settings | Upgrade behavior |
| --- | --- |
| Accounts, password hashes, enabled states, session secret | Preserved |
| Menu content, optional prices, food safety settings, rotation | Preserved |
| Schedule rules, timezone, theme, site name, history, audit | Preserved |
| Port in `.menu.env` | Preserved |
| RC1 network controller configuration and hotspot password | Preserved |
| Pi OS login, normal Wi-Fi profiles, SSH settings | Not replaced |

The bundled sample content is used for fresh installations only. It never replaces an existing collection during upgrade.

## Verify

```bash
curl http://localhost:8080/health
systemctl is-active bagel-menu.service
```

If you changed the port, use that port instead of 8080. For this package, health should report **1.0.0-rc2**. Sign in with your existing application account. Follow [TESTING_RC2.md](TESTING_RC2.md) before publishing or discarding the prior copy.

## If an upgrade fails

The updater exits at the failing command; it does not automatically reverse every OS-level action. Keep the error message and the timestamped private backup. Use Ethernet/ordinary Wi-Fi or the local console for recovery.

For manual application rollback:

1. Stop the application with `sudo systemctl stop bagel-menu.service`.
2. Note the actual installation directory shown by `systemctl show`.
3. Rename the failed application directory to an unused sibling name so it remains available for diagnosis.
4. Copy the selected timestamped backup back to the **same original installation path**.
5. In that restored folder, run `bash setup.sh` and `sudo python3 install_service.py`.
6. Verify health and sign in with the restored credentials.

The private prior-version copy excludes `.venv`; setup recreates it. Restore matching old code and data together. Application backups exclude the OS login, SSH settings, and ordinary network credentials.

For complete hardware failure, install a stock OS and Max’s Menu on a new card, then restore an off-device System backup as described in the user guide.
