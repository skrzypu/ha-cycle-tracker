---
name: ha-package
description: Build a ready-to-copy Home Assistant package of the Cycle Tracker integration (zip and tar.gz) with checksums and install notes. Use when the user asks to prepare a package, bundle, archive, zip/tar, or "something to copy and upload to HA".
---

Build a clean, verifiable distribution package of this integration for manual
installation in Home Assistant. The package is for testing or release; it does
not install anything into HA and does not touch a running HA instance.

## Version

The version comes from `custom_components/cycle_tracker/manifest.json`. Never
guess it and never hard-code it in the skill.

If the user names a version and it differs from the manifest, ask first whether
to bump the manifest in the repository. Bumping the manifest is a repository
change (and changes the card cache-buster URL); building a package is not.
Record the final version in the report.

## What goes in

Only files under `custom_components/cycle_tracker/`. Inside the archive the
root is `cycle_tracker/` — NOT `custom_components/cycle_tracker/` — because
the documented install command extracts with
`tar -xzf <archive> -C /config/custom_components`. A `custom_components/`
prefix inside the archive would create a doubled directory there.

Always exclude:

- `__pycache__` directories
- `*.pyc`
- `.DS_Store`

Must be present in the archive:

- `cycle_tracker/manifest.json`
- `cycle_tracker/www/cycle-tracker-card.js`
- `cycle_tracker/translations/en.json`
- `cycle_tracker/translations/pl.json`
- `cycle_tracker/brand/icon.png`

Do not include tests, docs, OpenSpec files, `.venv` or the repository root
files. Do not include the previous package's install notes inside the archive.

## Where it goes

`scripts/build.py` in this directory implements the steps below. Run it with
`python3 .opencode/skills/ha-package/scripts/build.py`; it reads the manifest,
builds both archives, verifies them and writes the install note. Follow the
steps manually only if the script is unavailable.

Write both formats to `/tmp/opencode/` (pre-created, approved for external
access), using the version in the file name:

- `/tmp/opencode/ha-cycle-tracker-<version>.zip`
- `/tmp/opencode/ha-cycle-tracker-<version>.tar.gz`
- `/tmp/opencode/INSTALL_<version>.md`

Use Python's `zipfile` and `tarfile` with deterministic member ordering. Do not
use shell globbing that could pick up caches.

## Verify before reporting

1. List every archive member. Assert no cache/`.pyc` entries and that all five
   required entries above are present.
2. Read each archived member back and compare bytes with its source file under
   the repository. Zero mismatches.
3. Compute SHA-256 for each archive.
4. Write the install note next to the archives (not inside them) with: absolute
   archive paths, both checksums, the version, and these exact install steps:
   stop HA and back up `/config/custom_components/cycle_tracker/`, then
   `scp -O <tar> hassio@192.168.0.215:/tmp/`, then
   `tar -xzf /tmp/<tar-name> -C /config/custom_components`, then restart HA,
   plus a rollback step.
5. Note the card cache-buster: the Lovelace resource URL is
   `/cycle_tracker/cycle-tracker-card.js?v=<manifest version>`. If an HA
   instance already had that same version, the browser may serve a cached card;
   hard-refresh or clear site data.

## Report back

Give the exact paths, both SHA-256 values, the version, file count, and state
explicitly whether the repository was changed (version bump or nothing). Do not
claim HA was tested — this skill only builds the package.
