Max’s Menu’s first public prerelease: a Raspberry Pi server for local digital menu boards, with no cloud subscription.

Download **maxs-menu.zip** below, rather than GitHub’s automatically generated source archives. See README for fresh installation and UPGRADING.md for existing RC1 installations.

Includes ten menus and permanent screen URLs; daily scheduling; full-width/two-column sections; optional prices and food safety footer; menu rotation; eleven local themes; administrator/employee accounts; history and full application backup/restore; Ethernet, ordinary Wi-Fi, and optional 2.4 GHz hotspot operation.

RC2 adds a readable live Schedule clock, administrator-controlled schedule timezone in System, and a yellow initial network-loading indicator. RC1 accounts, content, schedules, and network settings are retained during upgrade.

The maintainer reports that all RC2 acceptance tests passed. Automated checks and browser tests are documented in VALIDATION.md. Source code is MIT licensed; fonts retain their separate notices.

**Known limits:** the hotspot has no internet sharing or 5 GHz selection. On the tested Onn player, offline Wi-Fi startup required disabling Android internet validation through ADB; changing automatic time settings did not solve it. Scheduled menus require an accurate Pi clock. Earlier private-development builds are outside the supported upgrade path.
