## Image File Renamer Project Overview

This project, simply called "Image Namer," aims to be a simple script that can look at a single file or a folder of files and rename them based on the actual image contents, as analyzed by a visual model.

The user should be able to select the provider (OpenAI or Ollama) and the visual model to be used. Default to Ollama and the gemma3:27b model.

## About Me

- Name: Stacey Vetzal
- Email: stacey@vetzal.com
- GitHub: https://github.com/svetzal/
- LinkedIn: https://www.linkedin.com/in/svetzal/
- Blog: https://stacey.vetzal.com/

## Tech Stack

- Python 3.13+
- PEP 621 compliant pyproject.toml file containing project metadat, dependencies, tool configurations (pytest, flake8, etc.)
- Key Dependencies:
  - PySide6: GUI framework
  - Mojentic: LLM abstraction and agent sdk (https://vetzal.com/mojentic/)
  - Typer: command-line argument processing
  - Rich: Rich and colourful terminal UI
  - PyTest: Testing (pytest, pytest-cov, pytest-mock)
  - Flake8: Linting (flake8, flake8-pyproject)
  - buldtools: project building
  - uv: dependency management

## Project Structure
```
src/
```

## Development Setup
Recommended: use uv (fast Python package manager). CI uses uv as well.

1. Install Python 3.13 or higher
2. Install uv (https://docs.astral.sh/uv/)
3. Create and activate virtual environment
   ```bash
   uv venv
   . .venv/bin/activate
   ```
4. Install dependencies (dev extras)
   ```bash
   uv pip install -e ".[dev]"
   ```
5. Optional: GUI extras
   ```bash
   uv pip install -e ".[gui]"
   ```

Alternative (pip):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Testing Guidelines
- Tests are co-located with implementation files (test file must be in the same folder as the implementation)
- We write tests as specifications, therefore you can find all the tests in the *_spec.py files
- Run tests: `pytest`
- Linting: `flake8 src`
- Code style:
  - Max line length: 120
  - Max complexity: 10
  - Follow google docstring style

### Testing Best Practices
- Use pytest for testing, with mocker if you require mocking
- Do not use unittest or MagicMock directly, use it through the mocker wrapper
- Use @fixture markers for pytest fixtures
- Break up fixtures into smaller fixtures if they are too large
- Separate test phases with a single blank line
  - Do not write Given/When/Then or Act/Arrange/Assert comments
- Do not write docstring comments on your should_ methods
- Do not use conditional statements in tests
- Each test must fail for one and only one clear reason

## Code Style Requirements
- Follow the existing project structure
- Write tests for new functionality
- Document using google-style docstrings
- Keep code complexity low, functions and methods short
- Use type hints for all functions and methods
- Favor declarative code styles over imperative code styles
- Use pydantic (not @dataclass) for data objects with strong types
- Favor list and dictionary comprehensions over for loops

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

### CHANGELOG.md Maintenance

1. Keep CHANGELOG.md up-to-date:
   - All notable changes should be documented under the [Next] section
   - Group changes into categories:
     - Added: New features
     - Changed: Changes in existing functionality
     - Deprecated: Soon-to-be removed features
     - Removed: Removed features
     - Fixed: Bug fixes
     - Security: Security vulnerability fixes
   - Each entry should be clear and understandable to end-users
   - Reference relevant issue/PR numbers where applicable

2. Before creating a release:
   - Move [Next] changes to the new version section (e.g., [1.0.0])
   - Add release date
   - Ensure entries are concise but descriptive
   - Write from the user's perspective
   - Include migration instructions for breaking changes
   - Document API changes thoroughly

---

## Python typing note (policy)
   - Update documentation to reflect the changes



---

## Python typing note (policy)
- Do NOT add `from __future__ import annotations` in modules.
- Rationale: this project requires Python 3.13+, where annotations are already stored as strings by default. The import is redundant and can cause inconsistency in runtime `__annotations__` introspection across modules. If backporting becomes necessary later, we can revisit.
