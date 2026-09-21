# Previous experiment stage archive

Archived on 21 September 2026. The active experiment remains in `../../BACE/`; shared source data remain in `../../data/`; research documentation remains in `../../docs/`.

This directory retains the previous stage's code, configuration, tests, generation inputs and outputs, logs, PDF exports, Python environments, caches, and dependency lists. Entries were renamed on the same filesystem without rewriting their contents. The root credential file and BACE credential file were not moved.

Git tracks this archive's code, configuration, tests, dependency lists, PDF exports, README, and manifest. Generation inputs and outputs, logs, environments, and caches remain local and are excluded from the commit.

See `archive_manifest.json` for the original-to-archived path mapping, documentation link updates, and verification results. Directory modification times changed during filesystem renames; both original and archived metadata are recorded. Historical paths inside archived code, logs, and manifests are preserved. Archived virtual environments contain original absolute paths; restore their original locations or rebuild them before use.

To restore an entry, move it from this directory to its original workspace path after checking that the destination does not already exist. The archive manifest also records the documentation links to reverse if restoring the previous layout.
