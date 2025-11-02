# Changelog

All notable changes to this project will be documented in this file.

## [Next]
### Added
- New `image-namer file` subcommand to rename a single file with `--dry-run/--apply` (#TODO)
- Minimal collision resolver utility `next_available_name()` with macOS case-insensitive handling (#TODO)
- Idempotency heuristic: if current stem equals proposed stem, no rename occurs (#TODO)
- Placeholder flags `--update-refs/--no-update-refs` and `--refs-root` for future Markdown/wiki link updates (#TODO)
- Environment variable support for defaults: `LLM_PROVIDER`, `LLM_MODEL` (flags > env > defaults) (#10)

### Changed
- Documentation updated to include new `file` subcommand, refs flags, and environment variable precedence; recommend uv for setup (aligns with CI) (#16)
- Package metadata updated with correct author and URLs in `pyproject.toml` (#2, #3)
- Pytest discovery configured to pick up `should_*` tests in `*_spec.py` files (#1, #6)

### Fixed
- CLI now validates supported image extensions and exits gracefully on invalid inputs (#8)
- CLI adds error handling around LLM and gateway calls with friendly error messages (#7)
- Removed unused import in `generate_name_spec.py` to satisfy flake8 (#4)
- Added runtime Python version validation (requires Python 3.13+) (#12)

