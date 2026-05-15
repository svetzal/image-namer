All done. Here's what was updated:

**10 packages bumped** (all minor/patch, all transitive):

| Package | Old | New |
|---|---|---|
| `anthropic` | 0.101.0 | 0.102.0 |
| `ast-serialize` | 0.3.0 | 0.4.0 |
| `idna` | 3.14 | 3.15 |
| `pymdown-extensions` | 10.21.2 | 10.21.3 |
| `PySide6` / `pyside6-addons` / `pyside6-essentials` / `shiboken6` | 6.11.0 | 6.11.1 |
| `requests` | 2.34.0 | 2.34.2 |
| `tiktoken` | 0.12.0 | 0.13.0 |

All direct dependencies in `pyproject.toml` were already at their latest versions — only transitive/indirect deps needed updating. All three quality gates passed cleanly: **222 tests**, **lint clean**, **mypy strict mode clean**.