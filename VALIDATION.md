# Validation for 1.0.0-rc2

This is a review candidate, not a hardware-certified image. It supports fresh installation and upgrades from the public RC1 data/configuration model. Earlier private-prototype migration is outside scope. No private runtime data or Git history is included.

## Automated application checks

The release includes standard-library unittest tests. Run after setup/dependency installation:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The preparation environment ran 68 tests: **67 passed, one skipped**. The skip is an AF_UNIX socket round-trip because this execution environment blocks Unix sockets. Run that check on the Pi; the remaining controller tests use mocks/fakes.

Coverage includes:

- Fresh and repeated interactive setup; no supplied/default/hidden accounts.
- RC1-compatible state copied to a version-named installation with accounts, opaque account tokens, menus/prices, rotation, theme, schedules, and local environment retained byte-for-byte.
- Actual upgrade shell flow reusing an existing service directory, tested through safe command stubs.
- Separate integration check generated a configured installation using the original RC1 code, copied RC2 over it through the updater, and verified RC2 health, existing logins, theme/rotation/schedules, and unchanged private data.
- Existing complete RC1 root network configuration and hotspot credentials preserved during helper installation.
- Readable clock formatting, timezone validation, administrator-only settings changes, revision conflicts, scheduling effects, and RC1 backup restoration.
- Reproducible ZIP layout, checksums, and exclusion of injected private runtime data.
- Configurable site name, timezone, administrator, hotspot name, and interface.
- Ten-menu validation and Screen 1–10 URLs, including existing uppercase variants.
- Schedule boundaries, fallback mapping, overnight rules, overlap rejection, invalid time increments, and stale revision rejection.
- Administrator equality, last-enabled-administrator protection, employee permissions, and rotation access checks.
- Local administrator reset and login-session invalidation.
- Backup validation, restored accounts/theme/schedules/rotation, preview/confirmation conflicts, staged hotspot identity, and interrupted-restore rollback.
- Code upgrade preserving private data, environment settings, and existing login, with a private prior-version copy.
- Root network installation with chosen identity and saved credentials without a network switch, using a temporary mapped filesystem and mocked system commands.
- Hotspot trial confirmation/expiry/cancel, startup recovery, failed-target rollback, and retry behavior.
- Ethernet-only hardware, missing Wi-Fi, disabled optional hotspot support, hostapd configuration, process readiness, cleanup, and error redaction.

## Browser checks performed during preparation

Headless Chromium exercised the actual app, using temporary synthetic accounts/data and a mocked network controller:

- Ten-menu editor, creating Menu 4 content, price display, publishing, and saved 90° rotation.
- Schedule page add/save and a permanent Screen 1 URL displaying Menu 4 during a matching interval.
- Editor preview bypassing the schedule to show the selected menu.
- All four rotations at 1920×1080 and 1080×1920, checking canvas bounds, content fitting, and food safety footer.
- All five new themes on the previously dark classic second menu, with explicit theme overrides and locally loaded fonts.
- Configurable hotspot identity, Show password, saved password behavior, administrator user controls, employee restrictions, and mobile-width layout.
- Initial yellow network-loading background cleared on success and error; periodic polling does not re-highlight it.
- Schedule timezone saved and validated through System, readable clock refreshed, and unsaved schedule drafts retained during clock polling.
- Timezone controls remain usable when the network-status request fails; mobile layout checked.
- No uncaught JavaScript errors in those flows.

Python compilation, JavaScript syntax, shell syntax, generated systemd unit syntax (with a local NetworkManager dependency placeholder), documentation links, and package exclusions are checked as part of packaging. The package is scanned for known prototype account/network identifiers and passwords. Synthetic test fixtures remain; no live password hashes or account files are included.

## Physical acceptance status

The maintainer reports that all tests in TESTING_RC2.md passed before first GitHub publication. The following hardware checks remain relevant when qualifying additional Pi/player configurations:

- Fresh install on the intended Pi and OS, including apt/pip installation and real systemd startup/reboot.
- Actual AF_UNIX controller permissions and NetworkManager/hostapd/DHCP operation.
- Original Pi Zero W, Ethernet-only Model B+, and any new USB adapter behavior.
- Custom hotspot name/password, client joins, trial rollback, saved mode after reboot, and SSH/SCP.
- Walmart Onn kiosk startup and reconnection after player/Pi power cycles with no internet.
- Correct scheduling through a real time boundary and after loss of power; ensure the Pi clock is correct.
- Long-running menu readability/colors on the actual TV/browser, particularly rotated displays.
- Full recovery onto a second SD card/Pi from an off-device system backup.

Use [TESTING_RC2.md](TESTING_RC2.md) for the requested physical test sequence.

The candidate retains the 2.4 GHz hostapd approach. It does not implement a new 5 GHz backend, internet sharing, or Android validation spoofing, and does not claim those unresolved player/network issues are fixed.
