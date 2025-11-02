# Image Namer

Rename image files based on their visual contents using a multimodal model.

- Default provider: `ollama`
- Default model: `gemma3:27b`
- Tech stack: Python 3.13+, Typer CLI, Rich, Mojentic

## Install

1. Python 3.13+
2. Create and activate a virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install (dev extras include pytest/flake8):
   ```bash
   pip install -e ".[dev]"
   ```

## Usage

Single-image proposal (dry-run by default):
```bash
image-namer generate path/to/image.jpg
```

Select provider/model:
```bash
image-namer generate path/to/image.jpg --provider ollama --model gemma3:27b
image-namer generate path/to/image.jpg --provider openai --model gpt-4o
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
