Done. Two packages were updated in `uv.lock`:

| Package | Old | New | Type |
|---------|-----|-----|------|
| `filelock` | 3.29.3 | 3.29.4 | patch |
| `pytest` | 9.0.3 | 9.1.0 | minor |

All three quality gates pass cleanly — 283 tests (8 skipped), zero flake8 warnings, mypy reports no issues across 42 source files. The lockfile update is committed and pushed to `origin/main`.