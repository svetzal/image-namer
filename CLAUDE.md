# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About Me

- Name: Stacey Vetzal
- Email: stacey@vetzal.com
- GitHub: https://github.com/svetzal/
- LinkedIn: https://www.linkedin.com/in/svetzal/
- Blog: https://stacey.vetzal.com/

## Project Overview

Image Namer is a Python CLI tool that renames image files based on their visual contents using multimodal vision models. It defaults to Ollama with the `gemma3:27b` model but also supports OpenAI.

## Core Architecture

### Simplified Structure
The codebase follows a clean separation between CLI and business logic:

- `src/main.py`: Typer application with all CLI commands. Handles argument parsing, provider setup, and output formatting
- `src/operations/`: Core business logic. Pure functions that take domain objects and LLM brokers, return pydantic models
- `src/operations/models.py`: Pydantic models for all data structures (`ProposedName`, `NameAssessment`)

**Testing Focus**: Tests are written for the `operations/` layer where the LLMBroker can be easily mocked. CLI commands in `main.py` are kept simple and thin.

### LLM Integration Pattern
All LLM interactions use Mojentic (https://vetzal.com/mojentic/):

```python
from mojentic.llm import LLMBroker, MessageBuilder

# Build messages with images
messages = [
    MessageBuilder('prompt text')
        .add_image(path)
        .build()
]

# Generate structured output
result = llm.generate_object(messages, object_model=SomePydanticModel)
```

Gateway setup pattern in commands:
```python
if provider == "ollama":
    gateway = OllamaGateway()
else:
    gateway = OpenAIGateway(api_key=os.environ["OPENAI_API_KEY"])
llm = LLMBroker(gateway=gateway, model=model)
```

## Development Commands

### Environment Setup

Recommended: use uv (fast Python package manager). CI uses uv as well.

```bash
# Install uv: https://docs.astral.sh/uv/

# Create and activate virtual environment
uv venv
. .venv/bin/activate  # On macOS/Linux

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install with GUI dependencies (future)
uv pip install -e ".[gui]"
```

Alternative (pip):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest src/operations/generate_name_spec.py

# Run with verbose output
pytest -v

# Run without coverage report
pytest --no-cov
```

Test files use the `*_spec.py` naming convention and are co-located with implementation files.

### Linting
```bash
# Lint the codebase
flake8 src

# Configuration in pyproject.toml [tool.flake8]:
# - Max line length: 120
# - Max complexity: 10
# - Requires flake8-pyproject plugin (included in dev dependencies)
```

### Running the CLI
```bash
# Propose a filename for an image
image-namer generate path/to/image.png

# Use OpenAI instead of Ollama
image-namer generate path/to/image.png --provider openai --model gpt-4o

# Apply mode (when implemented)
image-namer generate path/to/image.png --apply
```

## Code Style Requirements

### Testing Best Practices
- Tests are specifications: Use `*_spec.py` files, name test functions `should_*`
- Use pytest with `mocker` fixture for mocking (NOT unittest.mock directly)
- Separate test phases with single blank line (no Given/When/Then comments)
- No docstrings on test methods
- No conditional statements in tests
- Each test fails for exactly one reason

### General Style
- Use pydantic models for data structures (NOT @dataclass)
- Type hints required on all functions and methods
- Google-style docstrings
- Favor declarative over imperative style
- Prefer comprehensions over for loops
- Keep functions short and complexity low

### Adding New Commands
1. Add command function to `src/main.py` using `@app.command()` decorator
2. Use Typer annotations for arguments and options
3. Keep command logic thin - just validation, setup, calling operations, and output
4. Put business logic in `src/operations/` as pure functions
5. Write tests for operations layer, not CLI commands

### Adding New Operations
1. Define pydantic models in `src/operations/models.py`
2. Create operation module in `src/operations/` (e.g., `src/operations/rename_file.py`)
3. Write pure functions that accept domain objects and LLMBroker
4. Return pydantic models, never raw dicts
5. Create co-located `*_spec.py` test file

## Key Design Patterns

### Provider Configuration
Default to Ollama + `gemma3:27b` for local-first ML. Support OpenAI via `OPENAI_API_KEY` environment variable.

### Naming Rubric (Future Implementation)
- Lowercase slug format with hyphens
- Structure: `<primary-subject>--<specific-detail>.<ext>`
- Target: 5-8 words, max 80 chars
- Must be idempotent (don't rename if already suitable)

### Markdown Reference Updates (Future)
When renaming files, update:
- Standard Markdown: `![alt](path)` and `[text](path)`
- Obsidian wiki links: `[[name.png]]`, `![[name.png]]`, `[[name.png|alias]]`

## Project Configuration

### Dependencies
- Runtime: typer, rich, pydantic, mojentic
- Dev: pytest, pytest-cov, pytest-mock, flake8
- GUI (optional): PySide6

### Python Version
Requires Python 3.13+

### Package Management
Uses PEP 621 compliant `pyproject.toml`. The project uses src-layout with entry point `image-namer = main:main`.


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

All changes should be documented under appropriate version headings using Keep a Changelog format:

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

Follow semantic versioning principles:
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

---

## Python typing note (policy)
- Do NOT add `from __future__ import annotations` in modules.
- Rationale: this project requires Python 3.13+, where annotations are already stored as strings by default. The import is redundant and can cause inconsistency in runtime `__annotations__` introspection across modules. If backporting becomes necessary later, we can revisit.
