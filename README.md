# Image Namer

Rename image files based on their visual contents using a multimodal model.

- Default provider: `ollama`
- Default model: `gemma3:27b`
- Tech stack: Python 3.13+, Typer CLI, Rich, Mojentic

## Install

Recommended: use uv (fast Python package manager)

1. Install Python 3.13+
2. Install uv (see https://docs.astral.sh/uv/)
3. Create a virtualenv and install with dev extras:
   ```bash
   uv venv
   . .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

Alternative (pip):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Single-image rename (dry-run by default):
```bash
# Preview (no changes)
image-namer file path/to/image.jpg

# Apply rename
image-namer file path/to/image.jpg --apply
```

Select provider/model (flags > env > defaults):
```bash
image-namer file path/to/image.jpg --provider ollama --model gemma3:27b
image-namer file path/to/image.jpg --provider openai --model gpt-4o
```

Environment variables for defaults:
```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=gemma3:27b
```

Reference updates (placeholder):
```bash
image-namer file path/to/image.jpg --update-refs --refs-root /path/to/repo
# Currently just logs intention; does not modify Markdown/wiki links yet.
```

Propose-only (legacy demo):
```bash
image-namer generate path/to/image.jpg
```

OpenAI requires `OPENAI_API_KEY` in the environment.

## Naming Rubric (Summary)
- 5–8 short words, hyphen-separated, lowercase
- Prefer structure: `<primary-subject>--<specific-detail>`
- Max length 80 chars
- Avoid sensitive/private information
- Use helpful discriminators (chart type, version, year, color, angle)
- Idempotent: if already suitable, keep the same name

## Development
- Run tests: `pytest`
- Lint: `flake8 src`

Tests are co-located with implementation files and use `*_spec.py` filenames.

## License
MIT License (see LICENSE).
