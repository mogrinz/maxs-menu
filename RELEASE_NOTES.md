Max’s Menu v1.0.0-rc3 adds three-column layouts and configurable item currency.

- Three-column sections alongside existing full-width/two-column sections, multiple headings per column, and prices aligned to the right within each column.
- Thin vertical dividers extend through the full content area on menus made entirely of three-column sections, stopping above the optional food-safety footer. Mixed layouts retain section-height dividers.
- Sample Menus 4 and 5 on fresh installs. Upgrades preserve existing content: load a sample into an empty Menu 4/5 from Edit Menus, then Save & publish.
- System → Item pricing: administrator-controlled currency and number format. Existing installs keep USD / English (US). Currency selection changes formatting, not amounts; descriptions are left as written.
- Up to three decimal places for entered prices; display uses standard currency precision. Formatting works offline.
- Existing application/system backups remain supported, with new backups preserving pricing settings and three-column layouts.

Download **maxs-menu.zip** from this release’s Assets rather than the automatic source archives. Follow UPGRADING.md and TESTING_RC3.md. Before upgrading, download a System backup to your computer and switch to Ethernet or ordinary Wi-Fi with internet.

The networking implementation and OS/SSH configuration are unchanged in RC3. The existing offline-hotspot and accurate-Pi-clock limitations still apply. The maintainer has tested the new sample layouts, full-height dividers, and currency changes. Automated and browser checks are recorded in VALIDATION.md. Test your own hardware combination using TESTING_RC3.md.
