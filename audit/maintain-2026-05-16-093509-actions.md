All done. Here's a summary of what happened:

**Updates applied (transitive dependencies only):**
- `numpy` 2.4.4 → 2.4.5 (patch)
- `openai` 2.36.0 → 2.37.0 (minor)

Both are indirect dependencies pulled in via `mojentic`. No direct dependencies in `pyproject.toml` needed version bumps — they were already current.

**Quality gates:** All green — 226 tests passed, `flake8` clean, `mypy` clean. Changes committed and pushed to `origin/main`.