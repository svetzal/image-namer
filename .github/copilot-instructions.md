# GitHub Copilot Instructions for image-namer

## Project Architecture

**image-namer** is a Python 3.13+ CLI tool that renames image files based on visual content using LLM vision models (Ollama/OpenAI via Mojentic).

### Key Structural Patterns

**Thin CLI, fat operations**: `src/main.py` contains Typer commands that validate inputs, configure providers, and format output. All business logic lives in `src/operations/` as pure functions that accept Pydantic models and `LLMBroker` instances.

**Cache-first by design**: `.image_namer/cache/` stores LLM results keyed by `{image_sha256}__{provider}__{model}__v{rubric_version}`. Two cache types:
- `analysis/`: Assessment of whether current filename is suitable (`NameAssessment`)
- `names/`: Proposed new filenames (`ProposedName`)

Assessment runs **before** name generation to avoid unnecessary LLM calls on already-suitable filenames. See `_process_single_image()` in `main.py` for the assessment → generation → collision flow.

**Idempotency everywhere**: Files with suitable names (stem matches proposed or assessment passes) skip renaming. Collision resolution appends `-2`, `-3` suffixes.

### LLM Integration (Mojentic)

All vision calls use Mojentic's `LLMBroker` with structured Pydantic output:

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

### Data Flow (folder command)

1. Collect image files (`_collect_image_files`)
2. For each image: `_process_single_image()` → assessment → (if unsuitable) → name generation → collision check → track planned name
3. Display table (`_display_results_table`) + stats
4. If `--update-refs`: find markdown references → update files → report
5. If `--apply`: rename files on disk

Markdown reference updates support standard syntax `![](path)` `[](path)` and Obsidian wiki links `[[file.png]]` `![[file.png|alias]]`. See `operations/find_references.py` for regex patterns.

## Testing Conventions (STRICT)

Tests use `*_spec.py` naming, live co-located with implementation. Function names: `should_*`

**pytest + mocker fixture** (never `unittest.mock`):
```python
def should_call_llm_with_rubric_prompt(mocker, tmp_image_path, fake_llm):
    mocker.patch("operations.generate_name.MessageBuilder", _FakeBuilder)
    result = generate_name(tmp_image_path, llm=fake_llm)
    assert fake_llm.calls[0][1] == ProposedName
```

Shared fixtures in `conftest.py`:
- `tmp_image_path`: Creates real temp PNG for testing
- `fake_llm`: Mock `LLMBroker` that records calls and returns configurable responses

**Style rules**:
- Separate phases with single blank line (no Given/When/Then comments)
- No docstrings on test functions
- No conditionals in tests
- Each test fails for exactly one reason

## Development Workflow

**Setup** (uv recommended, CI uses it):
```bash
uv venv && . .venv/bin/activate && uv pip install -e ".[dev]"
```

**Testing**:
```bash
pytest                           # Run all with coverage
pytest src/operations/cache_spec.py  # Run specific file
pytest -v --no-cov               # Verbose without coverage
```

**Linting** (config in `pyproject.toml`):
```bash
flake8 src  # Max line length 120, max complexity 10
```

**Running CLI**:
```bash
image-namer file path/to/image.png --apply --update-refs
image-namer folder path/to/dir --recursive --dry-run
```

## Code Style Requirements

- **Pydantic models** for all data structures (never `@dataclass`)
- **Type hints** on all functions/methods
- **Google-style docstrings**
- **No `from __future__ import annotations`** (Python 3.13+ only, annotations already deferred)
- Prefer comprehensions over loops
- Keep functions short (complexity ≤10 per flake8)

## Key Files & Patterns

`src/operations/models.py`: All Pydantic models (`ProposedName`, `NameAssessment`, `MarkdownReference`, etc.)

`src/operations/cache.py`: Cache key generation, load/save for both assessments and names. Uses `constants.RUBRIC_VERSION` for cache invalidation.

`src/utils/fs.py`: `sha256_file()`, `ensure_cache_layout()`, `next_available_name()` (collision resolver with macOS case-insensitivity)

`src/operations/generate_name.py`: Vision naming with rubric prompt (5-8 words, `<subject>--<detail>` structure, 80 char max)

`src/operations/assess_name.py`: Suitability assessment (checks if current filename matches rubric)

`src/operations/find_references.py`: Markdown reference scanner with URL decoding and Unicode space normalization

`src/operations/update_references.py`: In-place file updater preserving alt text/aliases

## Adding New Operations

1. Define Pydantic models in `operations/models.py`
2. Create pure function in `operations/{name}.py` taking domain objects + `LLMBroker`
3. Return Pydantic model (never raw dict)
4. Co-locate `{name}_spec.py` with fixtures from `conftest.py`
5. Wire into CLI command in `main.py` (keep logic thin)

## Provider Configuration

Defaults: `ollama` + `gemma3:27b` (local-first ML)
OpenAI: Requires `OPENAI_API_KEY` env var
Precedence: CLI flags → env vars (`LLM_PROVIDER`, `LLM_MODEL`) → defaults

## Known Complexity Points

**Collision resolution in batch**: `_process_single_image()` tracks `planned_names` set across all files to avoid intra-run collisions. `_find_next_available_in_batch()` checks both disk and planned renames.

**URL decoding + Unicode normalization**: Obsidian uses URL-encoded paths with non-breaking spaces. `_ref_matches_filename()` handles `unquote()` + `unicodedata.normalize('NFKC')` for matching.

**Cache invalidation**: Any change to image bytes, provider, model, or `RUBRIC_VERSION` creates new cache key. Assessment and name caches are separate to enable "already suitable" optimization.

## Current Status

Version 1.0.0 - Production Ready ✅

All M1-M5 milestones complete (SPEC.md):
- ✅ Single-file rename (`file` command)
- ✅ Folder processing (flat + `--recursive`)
- ✅ Markdown reference updates (standard + Obsidian wiki links)
- ✅ Cache implementation (assessment + name proposals)
- ✅ Polish, documentation, comprehensive testing

## Release Process

### Tag Naming Convention
This project uses `RELEASE_X_Y_Z` format for version tags:
- Version 1.0.0 → Tag: `RELEASE_1_0_0`
- Version 1.2.3 → Tag: `RELEASE_1_2_3`
- Version 2.0.0 → Tag: `RELEASE_2_0_0`

### Pre-Release Checklist
Before creating a release:
- [ ] All tests passing: `pytest -v`
- [ ] Linting passes: `flake8 src`
- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated with all changes
- [ ] Documentation built successfully: `mkdocs build`
- [ ] Manual testing with real images completed
- [ ] README.md reflects current features

### Creating a Release

**1. Update CHANGELOG.md**

All changes should be documented under appropriate version headings using [Keep a Changelog](https://keepachangelog.com/) format:

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

**2. Commit Release Changes**

```bash
# Commit all release changes
git add -A
git commit -m "Release vX.Y.Z

- Brief summary of major changes
- Reference to CHANGELOG for full details"
```

**3. Create and Push Git Tag**

```bash
# Create annotated tag (RELEASE_X_Y_Z convention)
git tag -a RELEASE_X_Y_Z -m "Version X.Y.Z - Release Title

Major changes:
- Feature 1
- Feature 2
- Feature 3

See CHANGELOG.md for full details."

# Push commits and tag
git push origin main
git push origin RELEASE_X_Y_Z
```

**4. Create GitHub Release (using gh CLI)**

Prerequisites:
```bash
# Install gh (if needed)
brew install gh  # macOS
# or: sudo apt install gh  # Linux

# Authenticate (one-time)
gh auth login

# Verify
gh auth status
```

Create release:
```bash
# Option 1: Extract notes from CHANGELOG
gh release create RELEASE_X_Y_Z \
  --title "vX.Y.Z - Release Title" \
  --notes-file <(sed -n '/## \[X.Y.Z\]/,/## \[/p' CHANGELOG.md | sed '$d') \
  --latest

# Option 2: Interactive mode
gh release create RELEASE_X_Y_Z --generate-notes

# Verify
gh release view RELEASE_X_Y_Z
```

**Alternative (Web Interface)**:
1. Go to https://github.com/svetzal/image-namer/releases/new
2. Select tag: `RELEASE_X_Y_Z`
3. Release title: `vX.Y.Z - Release Title`
4. Description: Copy from CHANGELOG.md section
5. Mark as "Latest release"
6. Publish

**5. Post-Release Verification**

- [ ] GitHub release published and visible
- [ ] Documentation deployed to GitHub Pages (automatic)
- [ ] Installation works: `pipx install git+https://github.com/svetzal/image-namer.git`
- [ ] Tag appears in git: `git tag -l`

### Semantic Versioning

Follow [SemVer](https://semver.org/):
- **MAJOR** (X.0.0): Incompatible API changes, breaking changes
- **MINOR** (0.X.0): New features, backward-compatible
- **PATCH** (0.0.X): Bug fixes, backward-compatible

### Hotfix Process

For critical issues requiring immediate release:

```bash
# Create hotfix branch from tag
git checkout -b hotfix/X.Y.Z+1 RELEASE_X_Y_Z

# Make fixes, update CHANGELOG
# ... fix code ...

# Commit and tag
git commit -m "Hotfix: describe critical fix"
git tag -a RELEASE_X_Y_Z+1 -m "Hotfix vX.Y.Z+1"

# Merge back to main
git checkout main
git merge hotfix/X.Y.Z+1
git push origin main
git push origin RELEASE_X_Y_Z+1

# Create release
gh release create RELEASE_X_Y_Z+1 --title "vX.Y.Z+1 - Hotfix" --notes "Critical fix for..."
```

**Important**: Never delete release tags. If a release has issues, create a new patch version.
