# Changelog

## 0.1.0

First packaged release.

- Installable package with a `file-cleanup` command (`demo`, `scan`, `explore`, `suggest`, `apply`).
- `apply` reads the explorer's exported action plan or a mapping sheet, prints what is copied and what is left out, and supports `--undecided keep`.
- New `suggest` command: draft a plan from a JSON rules file.
- Resuming a copy checks the destination file (exists, same size), so copying the same plan to a second folder works.
- Destinations that look like OneDrive or SharePoint are refused unless `--allow-synced` is given.
- Library functions raise `CleanupError` instead of exiting, so the modules can be used from other code.
