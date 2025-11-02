# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-11-02

### Fixed
- Added `readme = "README.md"` to `pyproject.toml` so PyPI displays the full project description

## [1.0.0] - 2025-11-02

### Added
- **Core renaming functionality**
  - `image-namer file` command to rename a single image file with AI vision analysis
  - `image-namer folder` command to batch process all images in a directory
  - `--recursive` flag to process subdirectories in folder command
  - `--dry-run/--apply` modes for safe preview before applying changes
  - Support for PNG, JPG/JPEG, WebP, GIF, BMP, TIF/TIFF image formats

- **Intelligent features**
  - Pre-flight assessment to skip files with already-suitable names (avoid unnecessary LLM calls)
  - Smart caching system storing both assessments and name proposals (`.image_namer/cache/`)
  - Cache invalidation based on image hash, provider, model, and rubric version
  - Idempotency: files with names matching content are left unchanged
  - Collision handling with automatic `-2`, `-3` suffixes
  - macOS case-insensitive filesystem handling

- **Markdown reference updates**
  - `--update-refs` flag to automatically update markdown file references when renaming
  - `--refs-root` to specify root directory for reference scanning
  - Support for standard Markdown: `![alt](path)` and `[text](path)`
  - Support for Obsidian wiki links: `[[file.png]]`, `![[file.png]]`, `[[file.png|alias]]`
  - URL-encoded path handling and Unicode normalization (NFKC)
  - Preservation of alt text and aliases

- **AI provider support**
  - Default: Ollama with `gemma3:27b` model (local, privacy-focused)
  - OpenAI support via `OPENAI_API_KEY` environment variable
  - Mojentic integration for LLM abstraction with structured Pydantic outputs
  - Provider and model selection via CLI flags or environment variables

- **Configuration and environment**
  - Environment variable support: `LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`
  - Flag precedence: CLI flags > environment variables > defaults
  - Comprehensive error handling with user-friendly messages

- **Developer experience**
  - 94 comprehensive tests with 88% code coverage
  - Co-located `*_spec.py` test files following `should_*` naming convention
  - Flake8 linting with max-complexity: 10
  - Python 3.13+ requirement with runtime validation
  - Type-safe code with Pydantic models throughout

### Changed
- Package metadata updated with correct author information and URLs
- Documentation comprehensively updated for all features
- Test framework configured for pytest discovery with `*_spec.py` and `should_*` patterns

### Fixed
- CLI validates supported image extensions and exits gracefully on invalid inputs
- Proper error handling around LLM and gateway calls
- Deterministic file processing order (sorted) for consistent test behavior across platforms
- ANSI color code handling in test output assertions
- OPENAI_API_KEY validation moved to gateway creation (allows tests to run without API key)
- Exception handling prevents wrapping of typer.Exit codes

### Deprecated
- `generate` command is now superseded by `file --dry-run` for better consistency

## [0.1.0] - 2024-11-01 (Initial Development)

### Added
- Initial project structure with src-layout
- Basic CLI scaffolding with Typer
- Vision naming with Mojentic integration
- Preliminary cache implementation
