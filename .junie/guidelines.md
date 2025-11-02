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

1. Update CHANGELOG.md:
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

2. Creating a Release:
   - Ensure `pyproject.toml` indicates the next release version
   - Ensure all changes are documented in CHANGELOG.md
     - Move [Next] changes to the new version section (e.g., [1.0.0])
   - Follow semantic versioning:
     - MAJOR version for incompatible API changes
     - MINOR version for backward-compatible new functionality
     - PATCH version for backward-compatible bug fixes
   - Tag the release commit with the new version number (e.g., `git tag -a RELEASE_1_0_0 -m "Release v1.0.0"`)
   - Push the tag to the remote repository (e.g., `git push origin RELEASE_1_0_0`)
   - Using the gh command, create a new release on GitHub:
     - Use the new version number as the tag version
     - Use the same title as the tag version
     - Use the same description as the tag version
     - Attach the CHANGELOG.md file to the release

3. Best Practices:
   - Keep entries concise but descriptive
   - Write from the user's perspective
   - Include migration instructions for breaking changes
   - Document API changes thoroughly
   - Update documentation to reflect the changes



---

## Python typing note (policy)
- Do NOT add `from __future__ import annotations` in modules.
- Rationale: this project requires Python 3.13+, where annotations are already stored as strings by default. The import is redundant and can cause inconsistency in runtime `__annotations__` introspection across modules. If backporting becomes necessary later, we can revisit.
