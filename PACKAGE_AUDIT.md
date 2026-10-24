# Public package audit

Version: 1.0.0-rc2

- Clean source tree; no Git history is included.
- No populated runtime data, environment secrets, private backups, session keys, or live account files.
- No known private-prototype OS account/hostname, private hotspot name, or passwords found in the packaged files.
- No literal stored PBKDF2 account hashes found.
- Synthetic test credentials remain in tests only; they are not application defaults.
- The only bundled JSON file is the sample menu collection.
- Font license notices are retained.
- Relative documentation links resolve.
- Source exclusions are provided in .gitignore.

This is a package-content check, not a complete security audit. The MIT application license is included with its intended public copyright attribution; bundled fonts retain their separate notices. Perform the physical installation/player tests before public publication. Never commit a configured installation or old prototype archives.
