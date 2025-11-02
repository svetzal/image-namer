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
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux

# Install with dev dependencies
pip install -e ".[dev]"

# Install with GUI dependencies (future)
pip install -e ".[gui]"
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
