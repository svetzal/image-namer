All dependency updates completed successfully. Here's a summary of what changed:

## Dependency Updates — image-namer

### Packages Updated (3 packages)

| Package | Old Version | New Version | Type |
|---|---|---|---|
| `openai` | 2.31.0 → | 2.32.0 | patch |
| `pydantic` | 2.13.0 → | 2.13.1 | patch |
| `pydantic-core` | 2.46.0 → | 2.46.1 | patch |

All updates were **patch releases** within the existing version constraints — no changes to `pyproject.toml` were needed, only `uv.lock` was updated.

### Quality Gates — All Passed ✅

| Gate | Result |
|---|---|
| `uv run pytest` | 150 tests passed, 0 failed |
| `uv run flake8 src` | 0 warnings |
| `uv run mypy src` | No issues (33 source files) |

The project is healthy and up to date with the latest compatible versions.