# Max’s Menu user guide

## Menus and screens

A **menu** is a saved collection of headers, items, descriptions, prices, and display settings. A **screen** is a permanent public URL assigned to a TV. There are ten menus and ten screen URLs. You can use only one or two if that is all you need.

By default, Screen 1 displays Menu 1, Screen 2 displays Menu 2, and so on. A schedule rule temporarily selects another menu for a screen. The TV stays on the same URL.

The site name identifies the installation on administrative and landing pages. It is not added as a heading on TV displays. Menu content is under your control.

## Accounts and navigation

Sign in at `/admin`. The navigation contains Edit Menus, History, and My Account. Administrators also see Schedule, Theme, System, and Users.

| Action | Employee | Administrator |
| --- | --- | --- |
| Edit and publish menu content | Yes | Yes |
| Change food safety setting | Yes | Yes |
| Download menu/history exports or import a menu draft | Yes | Yes |
| View history | Yes | Yes |
| Change display rotation | No | Yes |
| Restore history | No | Yes |
| Change own password | No | Yes |
| Manage accounts or reset passwords | No | Yes |
| Set schedules/themes or use System | No | Yes |

Administrators have equal rights regardless of their names. There is no protected or hidden account. One administrator can reset another administrator’s password. At least one enabled administrator must remain; deletion, disabling, and demotion that would remove the last one are rejected. Someone with access to the Pi’s OS account can recover an existing administrator using the documented local command.

## Edit Menus

1. Choose Menu 1–10 in the menu dropdown.
2. Make changes to entries or settings.
3. Select **Save & publish**.

Changes remain a draft in the browser until published. The save button publishes the entire collection, including changes made on other menus during the same editing session. Displays refresh within about five seconds while connected.

If another user publishes first, your stale save is rejected rather than silently replacing their work. Keep a copy of any text you need, reload the saved collection, and reapply your changes.

**Reload saved** discards the current draft after confirmation. The browser also warns when leaving a page with unpublished edits. The preview shows published content, not the unsaved draft.

### Items and prices

**Add item or header** is available above and below the entry list. A new item has:

- A name, up to 120 characters.
- An optional description, up to 400 characters.
- An optional price.
- A **Show on display** checkbox.

Positive prices appear to the right with a dollar sign and two decimal places. Blank, zero, and negative prices do not display in the price area. You can put a price or other pricing information in the description instead. The current release uses dollar formatting; it has no currency picker.

**Choice / option** creates a name-only line without a separate price or description, useful for included choices such as dressings.

Clear **Show on display** to hide an entry without deleting it. **Remove entry** deletes it from the draft. Use Move up/down to reorder entries, or **Move to menu** to transfer an entry to another menu. Moving a header moves that entry only, not all the items following it.

There is a limit of 500 entries across the ten menus. More content can require smaller text; check readability from the actual ordering distance rather than relying only on whether it fits.

### Headers and columns

Check **Header Item** to create a heading without price or description. Headers can be renamed and moved like items. Removing a header keeps its following items.

A header’s role can be:

- **Start a new section:** begins a new full-width or two-column section.
- **Column heading / label:** labels content within an existing section.

For a two-column section:

1. Add a section header, choose **2 Columns**, and select Column 1.
2. Add a second header with **Column heading / label** and Column 2 if desired.
3. Assign each following item to Column 1 or Column 2.
4. Add another section header to end the two-column section.

The two headings occupy a common heading row, so the first items in both columns align below them. Two-column headers have no underline. Move up/down for an ordinary entry in a two-column section reorders within its own column.

### Display rotation

Administrators see radio buttons for **0°, 90°, 180°, and 270° clockwise** on Edit Menus. Rotation belongs to the selected menu, and is published with it. The complete display rotates, including the food safety footer. Text fitting uses the rotated width and height.

The editor remains upright. Preview the saved menu to see the result. If multiple menus will appear on one rotated TV through scheduling, give those menus the same rotation. Otherwise a scheduled menu change can intentionally change orientation.

### Food safety warning

Check **Include Food Safety Warning** on a menu to place this exact text at the bottom:

```text
*CONSUMING RAW OR UNDERCOOKED MEATS, POULTRY, SEAFOOD, SHELLFISH, OR EGGS MAY INCREASE YOUR RISK OF FOODBORNE ILLNESS, ESPECIALLY IF YOU HAVE CERTAIN MEDICAL CONDITIONS.
```

The leading asterisk and capitals are preserved. The footer wraps to the available width, participates in text fitting, and uses the smallest rendered content font size. The setting follows the menu when scheduled onto a different screen.

### Public URL and preview

The editor shows the selected menu’s **default public screen URL**. For Menu 4, that is `/display/screen4`. A schedule may make that screen URL display another menu, so it is not a permanent direct-menu link.

The editor’s preview deliberately bypasses scheduling and always shows the selected published menu. This direct-preview mode uses `?direct=1`; omit that parameter on TVs that should follow schedules.

### Import and export

**Download current menu** exports the entire ten-menu collection, including rotations and food safety settings. It does not export accounts, the selected global theme, or the schedule.

Use **Import menu** to load a compatible JSON collection into the browser draft. Review it and select Save & publish to change the displays. Importing alone does not publish. Employees cannot use import to change administrator-only rotation settings.

## Schedule

Administrators can add, edit, and delete daily rules on **Schedule**. Each row contains From, Until, Screen, and Displays (menu). Time dropdowns advance in 30-minute increments.

Example:

| From | Until | Screen | Displays |
| --- | --- | --- | --- |
| 7:00 AM | 11:00 AM | Screen 1 | Menu 1 |
| 11:00 AM | 2:00 PM | Screen 1 | Menu 4 |
| 2:00 PM | 11:00 PM | Screen 1 | Menu 5 |

Use **Save schedule** to publish rules. Existing rows can be edited directly; Delete rule takes effect after saving. Reload saved discards unsaved changes after confirmation. Screens without rules always show their corresponding menu number. Gaps between rules also use that default.

The start time is included and the end time is excluded. At 11:00 AM in the example, Menu 4 replaces Menu 1. Rules that meet at an endpoint are allowed; overlapping rules on the same screen are rejected. Different screens can have rules at the same time.

An end time earlier than the start runs overnight: 10:00 PM–2:00 AM covers late evening and early morning. Midnight appears as 12:00 AM. Equal start/end times are rejected; use the default mapping or two adjacent rules for an all-day assignment. There are at most 200 rules. This release has daily rules, not weekday/date-specific schedules.

Scheduling uses the configured application timezone. The page shows the Pi’s clock as, for example, **Friday, Dec 18 2026 7:00AM America/New York**, and refreshes it about every 15 seconds. The actual weekday is calculated from the date. Change the schedule timezone under **System → Schedule timezone**; this does not change the OS timezone or set the clock. Daylight-saving changes follow local wall time. A Pi without a battery-backed clock needs a valid time source after power loss. The menus can work offline, but correct schedules require a correct Pi clock. See Troubleshooting.

The Pi chooses the active menu; it does not depend on the streaming stick’s clock. Updates appear on connected displays within about five seconds. If the Pi becomes unreachable, a display may retain its last menu but cannot receive scheduled changes.

## Theme

The selected theme applies to all menus. Choose a style, select the menu to preview, and use **Save theme** to update displays. Previewing alone does not publish the choice.

| Theme | Style |
| --- | --- |
| Classic Bagel Shop | Cream, forest green, copper, traditional headings |
| Modern Minimalistic | Black and white, Jost sans-serif |
| Golden Chalk | Charcoal, golden handwritten item names |
| Coffeehouse Chalkboard | Dark chalkboard and white lettering |
| Rose Café | Blush pink and thicker uppercase serif lettering |
| Retro Diner | Warm white, coral script, blue condensed lettering |
| Starlight Café | Navy, subtle stars, gold headings |
| Seaside Café | Sand, sea blue, script headings |
| Autumn Harvest | Warm cream, copper, rich brown |
| Winter Hearth | Deep blue-green, cream, gold |
| Spring Garden | Soft cream, green, plum script |

All font files are served by the Pi, so displays do not need Google Fonts access. The display requests a light browser color scheme to discourage forced color changes; dark themes use explicit colors of their own.

## History

Publishing records the previous collection in History, up to 30 versions. **Download** exports that historical collection for import into an editor draft. Administrators can also **Restore** it directly. Restoring content creates another history record.

History restores menu content, rotation, and food safety settings. It does not roll back account settings, the theme, or schedules. A system backup covers those separately. Recent publication/restore audit events are retained, up to 200 entries.

## My Account and Users

Administrators can change their own passwords in My Account. Employees must ask an administrator to reset theirs.

In Users, an administrator can create an Employee or Administrator, reset a password, enable/disable an account, change its role, or delete it. Resetting a password, changing a role, or disabling an account invalidates that account’s current login sessions. Changing your own password in My Account keeps your current browser signed in.

There are at most 50 accounts. Username matching is case-insensitive; usernames use letters, numbers, underscores, or hyphens. Application password recovery is described in Troubleshooting and never requires a built-in backdoor.

## System and networking

System shows connection status and assigned IPv4 addresses. On first opening the page, “Loading network settings…” has a yellow background with dark text. The highlight clears after the initial request completes, including an error response, and normal polling does not flash it repeatedly. It hides hotspot controls when the selected adapter cannot publish an access point, or hotspot support was not enabled during installation. Ethernet installations retain editing, displays, and backup/restore.

For optional hotspot installations, the hotspot name is chosen during setup. The Wi-Fi password is loaded into the field for administrators. **Show password** sits between the field and **Save password**. Only save again after changing the value; a changed, unsaved password must be saved before switching.

Switching between the hotspot and a saved normal Wi-Fi profile starts a three-minute trial. Reconnect on the target network, sign in to System, and select **Keep this mode**. The Pi returns to the previous connection if the trial expires, is canceled, or is interrupted by a restart. A confirmed mode is restored after boot.

This release supports saved NetworkManager Wi-Fi profiles, not scanning for or creating home/shop Wi-Fi profiles through the editor. It uses one selected radio for client mode or a 2.4 GHz hotspot. It does not share internet access. When switching Wi-Fi, phones, TVs, and SSH sessions may disconnect and need reconnection. Android may require an explicit choice to stay on a network without internet.

The hotspot uses `192.168.50.1`; editor access is `http://192.168.50.1:8080/admin`. SSH and SCP use the Pi’s OS account, not the application account. Do not switch from an Ethernet-only connection just to use menus: clients on the same wired/router network can use the Pi’s normal address.

### Schedule timezone

Administrators can type or select an IANA timezone under **System → Schedule timezone**, then choose **Save timezone**. This changes how existing daily rules are interpreted, without changing their selected times. It does not switch Wi-Fi, change the OS timezone, or correct an inaccurate Pi clock. The setting is preserved across restarts/upgrades and included in system backups. The Schedule page links to this setting.

## Full backup and recovery onto replacement hardware

**Download system backup** exports:

- All menus, rotations, food safety settings, and the selected theme.
- Daily schedule rules, application timezone, and site name.
- Accounts, roles, enabled states, and password hashes.
- History and recent audit entries.
- Hotspot name and saved password, when configured.

The JSON file is private and unencrypted. Store it off the Pi. It excludes session cookies/keys, OS accounts, ordinary Wi-Fi credentials, SSH configuration, binaries, and the operating system.

To recover after hardware failure:

1. Flash a compatible stock OS and establish Ethernet or ordinary Wi-Fi and SSH.
2. Install Max’s Menu and create a temporary administrator through setup.
3. Sign in, open System, select the backup file, and choose **Preview backup**.
4. Review the summary, especially the administrator login to use afterward.
5. Type `RESTORE`, then select **Restore system backup**.
6. Sign in using an administrator and password from the backup.
7. If using a hotspot, apply its staged name/password separately while on normal Wi-Fi, then trial-switch and confirm.

Restore replaces application accounts/settings and invalidates restored sessions. It does not immediately change networking. The replacement Pi’s selected Wi-Fi interface, country, and hotspot enablement remain local hardware choices; the backup’s hotspot identity is staged for separate application. Ethernet-only replacements can retain the saved hotspot identity for later use without exposing controls they cannot support.

Before applying a restore, the Pi saves a private local recovery snapshot. This does not replace your off-device backup. If another user changes settings after your preview, restore is rejected until you preview again.
