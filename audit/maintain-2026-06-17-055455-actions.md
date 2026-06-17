All done. Here's a summary of what was updated:

| Package | Before | After | Type |
|---|---|---|---|
| `anthropic` | 0.109.1 | 0.109.2 | patch |
| `anyio` | 4.13.0 | 4.14.0 | minor |
| `openai` | 2.41.1 | 2.42.0 | minor |
| `tqdm` | 4.68.2 | 4.68.3 | patch |

All are transitive dependencies (via `mojentic`). No direct dependencies in `pyproject.toml` needed updating. All quality gates passed — **290 tests, 0 lint warnings, 0 mypy errors** — and the commit is pushed to `origin/main`.