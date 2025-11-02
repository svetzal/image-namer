# Changelog

All notable changes to this project will be documented in this file.

## [Next]
### Added
- GitHub Actions CI: pytest with coverage and flake8 on push/PR (#15)
- MyPy configuration in `pyproject.toml` (strict mode) [quality of life]
- Environment variable support for defaults: `IMGN_PROVIDER`, `IMGN_MODEL` (#10)

### Changed
- Package metadata updated with correct author and URLs in `pyproject.toml` (#2, #3)
- Pytest discovery configured to pick up `should_*` tests in `*_spec.py` files (#1, #6)

### Fixed
- CLI now validates supported image extensions and exits gracefully on invalid inputs (#8)
- CLI adds error handling around LLM and gateway calls with friendly error messages (#7)
- Removed unused import in `generate_name_spec.py` to satisfy flake8 (#4)
- Added runtime Python version validation (requires Python 3.13+) (#12)

