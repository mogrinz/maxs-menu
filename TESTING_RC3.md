# RC3 hardware acceptance checklist

Use the v1.0.0-rc3 installation ZIP from GitHub Releases. The maintainer has tested the new layouts, full-height dividers, and currency changes; use this checklist for your own hardware.

## Upgrade from RC2

1. Download a **System backup** and keep it off the Pi. Retain your RC2 ZIP.
2. Switch to Ethernet or ordinary Wi-Fi with internet; confirm that mode before upgrading.
3. Copy the supplied ZIP and run the commands in UPGRADING.md. Health must report `1.0.0-rc3`.
4. Confirm existing accounts, prices, layouts, themes, schedules, rotations, warning settings, and network settings remain intact. Menu 4/5 must retain their prior content, including an empty state.
5. Reload open browser pages to load the new scripts.

## Three-column samples and editor

1. In Edit Menus, choose an empty Menu 4. Click **Load three-column sample into this empty menu**, then Save & publish. Repeat for empty Menu 5. The button must be disabled on any nonempty Menu 4/5.
2. Open `/display/screen4` and `/display/screen5`. If schedules override those URLs, use the editor preview, which bypasses scheduling.
3. Confirm all three columns show their headings, sub-headings, items, and right-aligned prices. Thin dividers should extend through the content area, stopping above the food-safety footer when enabled. Beverage prices are placeholders.
4. Add an item to Column 3 and move it up/down. Rename and remove a column heading; removing a heading must retain its items.
5. Try Full Width, 2 Columns and 3 Columns sections together. Change 3 Columns to 2 Columns: all entries must remain, with Column 3 entries moved to Column 2. Check existing two-column headings and first-item alignment.
6. Try themes, food-safety footer, and rotations. Check from actual ordering distance; the editor reports crowded/overflowing menus. Three columns may be too narrow for detailed portrait menus.

## Currency

1. As an administrator, use **System → Item pricing**. Select EUR and German (Germany), check the preview, and save.
2. An already-open TV display should show euro formatting within about five seconds, without reload. Verify all menus and scheduled menus. Entered numeric amounts must not change.
3. Try GBP / English (UK), JPY / Japanese (no decimals), and KWD / English (UK) with an item price of `1.234` (three decimals). Return to your intended currency afterward.
4. Blank, zero, and negative prices must remain hidden. Item descriptions must remain unchanged.
5. Reload Edit Menus to check the selected currency code in price labels. An employee can edit prices but must not access System or change global pricing settings.
6. Reload/reboot and confirm settings persist. Export/restore a System backup and confirm currency, menus and three-column layouts survive. Menu-only downloads intentionally exclude global currency settings.

## Player and network regression

1. Test the Onn browser on the real TV with the selected theme, colors, three-column layout, and currency.
2. Test normal Wi-Fi/Ethernet, hotspot trial/confirmation, and player reconnect as usual. RC3 does not change networking.
3. Reboot the Pi and player and confirm both the menu and scheduling return. The Pi needs an accurate clock for schedules.
