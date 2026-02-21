# AGENTS.md — Project Guidance for AI Coding Assistants

This file provides unified guidance for all AI coding assistants working with this repository.

## About the Author

- Name: Stacey Vetzal
- Email: stacey@vetzal.com
- GitHub: https://github.com/svetzal/
- LinkedIn: https://www.linkedin.com/in/svetzal/
- Blog: https://stacey.vetzal.com/

## Project Overview

**Image Namer** is a Python 3.13+ CLI tool that renames image files based on their visual contents using multimodal vision models (Ollama/OpenAI via Mojentic). It defaults to Ollama with `gemma3:27b` (local-first ML) and also supports OpenAI.

## Tech Stack

- **Python** 3.13+
- **PEP 621** compliant `pyproject.toml` for project metadata, dependencies, and tool configurations
- **Key Dependencies**:
  - Mojentic: LLM abstraction and agent SDK (https://vetzal.com/mojentic/)
  - Typer: CLI argument processing
  - Rich: Terminal UI
  - Pydantic: Data models and validation
  - PySide6: GUI framework (optional)
  - pytest, pytest-cov, pytest-mock: Testing
  - flake8, flake8-pyproject: Linting
  - uv: Dependency management

## Core Architecture

### Structure

The codebase follows a clean separation between CLI and business logic:

- `src/main.py`: Typer application with all CLI commands. Handles argument parsing, provider setup, and output formatting. Keep command logic thin.
- `src/operations/`: Core business logic. Pure functions that accept domain objects and `LLMBroker`, return Pydantic models.
- `src/operations/models.py`: All Pydantic models (`ProposedName`, `NameAssessment`, `MarkdownReference`, etc.)

**Testing Focus**: Write tests for the `operations/` layer where `LLMBroker` can be easily mocked. CLI commands in `main.py` are kept simple and thin — do not write tests for them.

### Key Files

| File | Purpose |
|------|---------|
| `src/operations/models.py` | All Pydantic models |
| `src/operations/cache.py` | Cache key generation, load/save for assessments and names. Uses `constants.RUBRIC_VERSION` for cache invalidation |
| `src/operations/generate_name.py` | Vision naming with rubric prompt (5-8 words, `<subject>--<detail>` structure, 80 char max) |
| `src/operations/assess_name.py` | Suitability assessment (checks if current filename matches rubric) |
| `src/operations/find_references.py` | Markdown reference scanner with URL decoding and Unicode space normalization |
| `src/operations/update_references.py` | In-place file updater preserving alt text/aliases |
| `src/utils/fs.py` | `sha256_file()`, `ensure_cache_layout()`, `next_available_name()` (collision resolver with macOS case-insensitivity) |

### Cache-First Design

`.image_namer/cache/` stores LLM results keyed by `{image_sha256}__{provider}__{model}__v{rubric_version}`. Two cache types:

- `analysis/`: Assessment of whether the current filename is suitable (`NameAssessment`)
- `names/`: Proposed new filenames (`ProposedName`)

Assessment always runs **before** name generation to avoid unnecessary LLM calls on already-suitable filenames. See `_process_single_image()` in `main.py` for the assessment → generation → collision flow.

### Idempotency

Files with suitable names (stem matches proposed or assessment passes) skip renaming. Collision resolution appends `-2`, `-3` suffixes.

### LLM Integration (Mojentic)

All LLM interactions use Mojentic's `LLMBroker` with structured Pydantic output:

```python
from mojentic.llm import LLMBroker, MessageBuilder

messages = [MessageBuilder(prompt).add_image(path).build()]
result = llm.generate_object(messages, object_model=ProposedName)
```

Gateway setup in commands:

```python
gateway = OllamaGateway() if provider == "ollama" else OpenAIGateway(api_key=os.environ["OPENAI_API_KEY"])
llm = LLMBroker(gateway=gateway, model=model)
```

### Provider Configuration

- Defaults: `ollama` + `gemma3:27b` (local-first ML)
- OpenAI: Requires `OPENAI_API_KEY` env var
- Precedence: CLI flags → env vars (`LLM_PROVIDER`, `LLM_MODEL`) → defaults

### Data Flow (folder command)

1. Collect image files (`_collect_image_files`)
2. For each image: `_process_single_image()` → assessment → (if unsuitable) → name generation → collision check → track planned name
3. Display table (`_display_results_table`) + stats
4. If `--update-refs`: find markdown references → update files → report
5. If `--apply`: rename files on disk

Markdown reference updates support standard syntax `![](path)` `[](path)` and Obsidian wiki links `[[file.png]]` `![[file.png|alias]]`. See `operations/find_references.py` for regex patterns.

### Naming Rubric

- Lowercase slug format with hyphens
- Structure: `<primary-subject>--<specific-detail>.<ext>`
- Target: 5-8 words, max 80 chars
- Must be idempotent (don't rename if already suitable)

### Known Complexity Points

**Collision resolution in batch**: `_process_single_image()` tracks a `planned_names` set across all files to avoid intra-run collisions. `_find_next_available_in_batch()` checks both disk and planned renames.

**URL decoding + Unicode normalization**: Obsidian uses URL-encoded paths with non-breaking spaces. `_ref_matches_filename()` handles `unquote()` + `unicodedata.normalize('NFKC')` for matching.

**Cache invalidation**: Any change to image bytes, provider, model, or `RUBRIC_VERSION` creates a new cache key. Assessment and name caches are separate to enable the "already suitable" optimization.

## Development Setup

Recommended: use **uv** (fast Python package manager). CI uses uv as well.

```bash
# Install uv: https://docs.astral.sh/uv/

# Install all dependencies (creates .venv automatically, uses lockfile)
uv sync

# Include optional GUI extras
uv sync --extra gui
```

## Build & Tooling

### Testing

```bash
uv run pytest                                        # all tests with coverage
uv run pytest src/operations/generate_name_spec.py  # specific file
uv run pytest -v --no-cov                           # verbose without coverage
uv run pytest --lf                                  # re-run last failed
```

### Linting

```bash
# Lint the codebase (max line length 120, max complexity 10)
uv run flake8 src
```

Configuration lives in `pyproject.toml` under `[tool.flake8]`. Requires the `flake8-pyproject` plugin (included in dev dependencies).

### Running the CLI

```bash
# Propose a filename for a single image
uv run image-namer file path/to/image.png

# Apply rename and update markdown references
uv run image-namer file path/to/image.png --apply --update-refs

# Process a folder
uv run image-namer folder path/to/dir --recursive --dry-run

# Use OpenAI instead of Ollama
uv run image-namer folder path/to/dir --provider openai --model gpt-4o
```

## Testing Conventions

- Test files use `*_spec.py` naming, co-located with implementation files
- Test function names: `should_*`
- Use **pytest** with the `mocker` fixture for mocking — never use `unittest.mock` directly
- Separate test phases with a single blank line (no Given/When/Then or Arrange/Act/Assert comments)
- No docstrings on test functions
- No conditional statements in tests
- Each test fails for exactly one reason

Shared fixtures live in `conftest.py`:

- `tmp_image_path`: Creates a real temp PNG for testing
- `fake_llm`: Mock `LLMBroker` that records calls and returns configurable responses

Example:

```python
def should_call_llm_with_rubric_prompt(mocker, tmp_image_path, fake_llm):
    mocker.patch("operations.generate_name.MessageBuilder", _FakeBuilder)
    result = generate_name(tmp_image_path, llm=fake_llm)
    assert fake_llm.calls[0][1] == ProposedName
```

## Code Style

- **Pydantic models** for all data structures (never `@dataclass`)
- **Type hints** on all functions and methods
- **Google-style docstrings**
- **No `from __future__ import annotations`** — this project requires Python 3.13+, where annotations are already stored as strings by default. The import is redundant and can cause inconsistency in runtime `__annotations__` introspection. If backporting becomes necessary, revisit.
- Favor declarative over imperative style
- Prefer comprehensions over `for` loops
- Keep functions short; complexity ≤ 10 (enforced by flake8)

## Adding New Commands

1. Add a command function to `src/main.py` using `@app.command()` decorator
2. Use Typer annotations for arguments and options
3. Keep command logic thin — only validation, setup, calling operations, and output formatting
4. Put business logic in `src/operations/` as pure functions
5. Write tests for the operations layer, not CLI commands

## Adding New Operations

1. Define Pydantic models in `src/operations/models.py`
2. Create a pure function in `src/operations/{name}.py` accepting domain objects + `LLMBroker`
3. Return a Pydantic model — never a raw dict
4. Co-locate `{name}_spec.py` with test fixtures from `conftest.py`
5. Wire into the CLI command in `main.py` (keep it thin)

## Release Process

### Tag Naming Convention

This project uses `RELEASE_X_Y_Z` format for version tags:

- Version 1.0.0 → Tag: `RELEASE_1_0_0`
- Version 1.2.3 → Tag: `RELEASE_1_2_3`
- Version 2.0.0 → Tag: `RELEASE_2_0_0`

### Pre-Release Checklist

- [ ] All tests passing: `uv run pytest -v`
- [ ] Linting passes: `uv run flake8 src`
- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated (move `[Next]` entries to the new version section, add date)
- [ ] Documentation built successfully: `uv run mkdocs build`
- [ ] Manual testing with real images completed
- [ ] README.md reflects current features

### CHANGELOG.md Maintenance

Keep CHANGELOG.md up-to-date using [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [1.0.0] - 2025-11-02

### Added
- New feature descriptions

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Deprecated
- Soon-to-be-removed features

### Removed
- Removed features

### Security
- Security vulnerability fixes
```

All notable changes go under `[Next]` while in development. Before a release, move `[Next]` entries to the new version section and add the release date. Write entries from the user's perspective; include migration instructions for breaking changes and reference relevant issue/PR numbers where applicable.

### Creating a Release

**1. Commit release changes:**

```bash
git add -A
git commit -m "Release vX.Y.Z

- Brief summary of major changes
- Reference to CHANGELOG for full details"
```

**2. Create and push the annotated tag:**

```bash
git tag -a RELEASE_X_Y_Z -m "Version X.Y.Z - Release Title

Major changes:
- Feature 1
- Feature 2

See CHANGELOG.md for full details."

git push origin main
git push origin RELEASE_X_Y_Z
```

**3. Create GitHub release:**

```bash
# Extract notes from CHANGELOG
gh release create RELEASE_X_Y_Z \
  --title "vX.Y.Z - Release Title" \
  --notes-file <(sed -n '/## \[X.Y.Z\]/,/## \[/p' CHANGELOG.md | sed '$d') \
  --latest

# Or interactive
gh release create RELEASE_X_Y_Z --generate-notes

# Verify
gh release view RELEASE_X_Y_Z
```

**Alternative (web interface):**

1. Go to https://github.com/svetzal/image-namer/releases/new
2. Select tag: `RELEASE_X_Y_Z`
3. Release title: `vX.Y.Z - Release Title`
4. Description: Copy from CHANGELOG.md section
5. Mark as "Latest release" and publish

**4. Post-release verification:**

- [ ] GitHub release published and visible
- [ ] Documentation deployed to GitHub Pages (automatic)
- [ ] Installation works: `pipx install git+https://github.com/svetzal/image-namer.git`
- [ ] Tag appears in git: `git tag -l`

### Semantic Versioning

- **MAJOR** (X.0.0): Incompatible API / breaking changes
- **MINOR** (0.X.0): New features, backward-compatible
- **PATCH** (0.0.X): Bug fixes, backward-compatible

### Hotfix Process

```bash
# Branch from the release tag
git checkout -b hotfix/X.Y.Z+1 RELEASE_X_Y_Z

# Fix, update CHANGELOG, then:
git commit -m "Hotfix: describe critical fix"
git tag -a RELEASE_X_Y_Z+1 -m "Hotfix vX.Y.Z+1"

git checkout main
git merge hotfix/X.Y.Z+1
git push origin main
git push origin RELEASE_X_Y_Z+1

gh release create RELEASE_X_Y_Z+1 --title "vX.Y.Z+1 - Hotfix" --notes "Critical fix for..."
```

**Important**: Never delete release tags. If a release has issues, create a new patch version.
