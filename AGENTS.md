# AGENTS.md — Project Guidance for AI Coding Assistants

Why this project exists and what problem does it solve: @CHARTER.md

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
- `src/operations/models.py`: All Pydantic models (`ProposedName`, `ImageAnalysis`, `MarkdownReference`, etc.)

**Testing Focus**: Write tests for the `operations/` layer where `LLMBroker` can be easily mocked. CLI commands in `main.py` are kept simple and thin — do not write tests for them.

### Key Files

| File | Purpose |
|------|---------|
| `src/operations/models.py` | All Pydantic models |
| `src/operations/ports.py` | Protocol definitions for I/O boundaries (`AnalysisCachePort`, `ImageAnalyzerPort`, `FileRenamerPort`, `MarkdownFilePort`) |
| `src/operations/adapters.py` | Concrete implementations of ports (`FilesystemAnalysisCache`, `MojenticImageAnalyzer`, `FilesystemRenamer`, `FilesystemMarkdownFiles`) |
| `src/operations/apply_renames.py` | Apply rename operations from processing results via `FileRenamerPort` |
| `src/operations/pipeline_factory.py` | Factory for constructing gateway -> broker -> cache -> analyzer pipeline |
| `src/operations/cache.py` | Cache key generation, load/save for unified analysis results. Uses `constants.RUBRIC_VERSION` for cache invalidation |
| `src/operations/analyze_image.py` | Single-call LLM analysis: assesses suitability and proposes filename in one request |
| `src/operations/find_references.py` | Markdown reference scanner with URL decoding and Unicode space normalization; accepts `MarkdownFilePort` for I/O |
| `src/operations/update_references.py` | In-place file updater preserving alt text/aliases; accepts `MarkdownFilePort` for I/O |
| `src/operations/batch_references.py` | Batch markdown reference update orchestration; accepts `MarkdownFilePort` for I/O |
| `src/operations/text_utils.py` | Shared text normalization utilities (Unicode/whitespace); used by reference operations |
| `src/utils/fs.py` | `sha256_file()`, `ensure_cache_layout()`, `next_available_name()` (collision resolver with macOS case-insensitivity) |

### Cache-First Design

`.image_namer/cache/` stores LLM results keyed by `{image_sha256}__{filename}__{provider}__{model}__v{rubric_version}`. One cache type:

- `unified/`: Combined assessment + proposed filename (`ImageAnalysis`)

A single LLM call returns both whether the current name is suitable and the proposed replacement. Files that are already suitably named are skipped without any LLM call when cached. See `get_or_generate_analysis()` in `process_image.py` for the cache-first flow.

### Idempotency

Files with suitable names (stem matches proposed or assessment passes) skip renaming. Collision resolution appends `-2`, `-3` suffixes.

### LLM Integration (Mojentic)

All LLM interactions use Mojentic's `LLMBroker` with structured Pydantic output:

```python
from mojentic.llm import LLMBroker, MessageBuilder

messages = [MessageBuilder(prompt).add_image(path).build()]
result = llm.generate_object(messages, object_model=ImageAnalysis)
```

Pipeline construction is centralised in `build_analysis_pipeline()`:

```python
pipeline = build_analysis_pipeline(provider, model, cache_root)
result = process_single_image(path, pipeline.analyzer, pipeline.cache, set(), provider, model)
```

### Provider Configuration

- Defaults: `ollama` + `gemma3:27b` (local-first ML)
- OpenAI: Requires `OPENAI_API_KEY` env var
- Precedence: CLI flags → env vars (`LLM_PROVIDER`, `LLM_MODEL`) → defaults

### Data Flow (folder command)

1. Collect image files (`collect_image_files`)
2. For each image: `process_single_image()` → cache lookup → (on miss) unified LLM call → collision check → track planned name
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
- For I/O boundaries defined in `ports.py`, inject `Mock(spec=AnalysisCachePort)` and `Mock(spec=ImageAnalyzerPort)` directly — never use `mocker.patch()` on module-internal imports like `operations.process_image.load_analysis_from_cache`

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
2. If the operation requires I/O (filesystem, LLM, external API):
   - Define a Protocol in `src/operations/ports.py` for each I/O boundary
   - Create a concrete adapter class in `src/operations/adapters.py` wrapping the real implementation
   - Inject the port into the operation function rather than calling I/O functions directly
3. Create a pure function in `src/operations/{name}.py` accepting domain objects and port interfaces
4. Return a Pydantic model — never a raw dict
5. Co-locate `{name}_spec.py` with test fixtures from `conftest.py`; use `Mock(spec=PortClass)` for I/O boundaries
6. Wire into the CLI command in `main.py` by constructing the concrete adapters and passing them in (keep command logic thin)

## Release Process

To create a new release:

1. Ensure all quality gates pass:
   - `uv run pytest` (tests with coverage)
   - `uv run flake8 src` (linting)
   - `uv run mkdocs build` (documentation)
2. Update `CHANGELOG.md` — move `[Next]` entries to `[X.Y.Z]` with today's date
3. Bump the version in `pyproject.toml`
4. Commit: `git commit -m "Release vX.Y.Z"`
5. Tag: `git tag vX.Y.Z`
6. Push: `git push origin main --tags`
7. Create a GitHub release from the tag — CI handles PyPI publishing automatically
8. Local install (immediately, don't wait for PyPI): `uv tool install . --force`
