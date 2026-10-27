# Changes in 1.0.0-rc3

- Add opt-in three-column sections with per-entry column assignment and multiple headings per column.
- Add subtle full-height column dividers on entirely three-column menus; preserve the food-safety footer and use section-height rules in mixed layouts.
- Preserve all entries when changing to fewer columns; keep existing full-width/two-column behavior.
- Include three-column samples in Menus 4 and 5 on fresh installs; provide an explicit draft loader for empty Menu 4/5 after upgrades.
- Add administrator-only global currency and regional number format settings under System, with offline formatting and live display refresh.
- Support up to three price decimals, standard currency precision, and prices up to 9,999,999.999. No exchange-rate conversion.
- Preserve existing accounts, menus, themes, schedules, network settings, and RC2 backups. Pricing defaults to USD / en-US when absent.

# Release notes

## 1.0.0-rc2

Review package for the first GitHub prerelease. Supports fresh installation and upgrades from the public RC1 release; earlier private prototypes are outside the upgrade path.

- Schedule clock uses readable local date/time, weekday, AM/PM, and timezone, refreshed about every 15 seconds.
- Administrators can change the schedule timezone under System without changing OS time or networking.
- Initial network-settings loading status uses a yellow background and dark text; normal styling returns when loading completes.
- MIT license included; bundled fonts retain their own notices.
- Consistent `maxs-menu.zip` asset with a `maxs-menu` top-level folder, reproducible packaging script, and matching fresh-install/upgrade documentation.
- Upgrade script discovers and reuses the actual RC1 service directory, including version-named folders. Existing private state and RC1 controller configuration are retained.
- Added RC2-specific upgrade, timezone, permissions, and loading-state checks, plus a physical acceptance checklist.

Hotspot driver behavior, 5 GHz selection, internet sharing, and Android validation spoofing are unchanged.


## 1.0.0-rc1

First clean-install public-release candidate. Existing private prototype installations are outside the in-place upgrade path.

- Interactive setup for site name, timezone, chosen application administrator, and optional hotspot identity.
- No default application password and no hidden recovery user. Equal administrator roles and a documented local reset command replace special named accounts.
- Ten menus; stable Screen 1–10 public URLs and matching defaults.
- Daily scheduling with 30-minute dropdowns, editable/deletable rules, overnight support, and overlap rejection.
- Administrator-only per-menu rotation on Edit Menus, with rotated automatic fitting and direct published-menu previews.
- Starlight Café, Seaside Café, Autumn Harvest, Winter Hearth, and Spring Garden themes, bringing the total to eleven.
- Configurable hotspot name/interface/country; existing 2.4 GHz hostapd backend retained. Hotspot networking is optional.
- Full backup format version 2 includes public-release accounts, site settings, schedules, rotations, themes, content, history, and staged hotspot credentials.
- Upgrade mechanism retains local accounts, configuration, and menus, with a private timestamped backup and explicit rollback documentation.
- Complete installation, user guide, troubleshooting, upgrade, and video rehearsal documentation; source exclusions and GitHub unit-test workflow.

Hardware-specific Wi-Fi, 5 GHz hotspot support, Android reconnect policies, internet sharing, and captive-portal spoofing remain separate work. This candidate does not claim to resolve those issues.
