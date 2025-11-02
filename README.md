# Image Namer

**Rename image files based on their visual contents using AI vision models.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

Transform generic filenames like `IMG_2347.jpg` into descriptive names like `golden-retriever-puppy--running-in-park.jpg` using AI vision analysis.

## Features

- 🤖 **AI-powered naming** using Ollama (local) or OpenAI (cloud)
- 🏠 **Local-first** with Ollama for privacy
- ⚡ **Intelligent caching** to avoid redundant API calls
- 🔄 **Idempotent** - won't rename already-suitable files
- 📁 **Batch processing** with recursive folder support
- 📝 **Markdown reference updates** for Obsidian and standard markdown
- 🔍 **Dry-run mode** to preview changes safely
- 🎯 **Smart collision handling**

## Quick Start

### Installation (Recommended: pipx)

Install Image Namer using [pipx](https://pipx.pypa.io/) for a clean, isolated installation:

```bash
# Install pipx (if needed)
brew install pipx  # macOS
# or: python3 -m pip install --user pipx

# Install image-namer
pipx install git+https://github.com/svetzal/image-namer.git

# Verify installation
image-namer --help
```

**Why pipx?** It installs Python CLI tools in isolated environments, preventing dependency conflicts with other projects.

### Setup AI Provider

Image Namer requires an AI vision model. Choose one:

**Option 1: Ollama (Recommended - Free & Local)**
```bash
# Install from https://ollama.com
ollama pull gemma3:27b
```

**Option 2: OpenAI (Cloud - Requires API Key)**
```bash
export OPENAI_API_KEY='sk-proj-...'
```

### Basic Usage

```bash
# Preview rename (dry-run)
image-namer file photo.jpg

# Apply rename
image-namer file photo.jpg --apply

# Process entire folder
image-namer folder ~/Pictures/screenshots --apply

# Update markdown references
image-namer folder ~/Documents/notes/images --apply --update-refs
```

## Documentation

📚 **[Full Documentation](https://svetzal.github.io/image-namer/)** (comprehensive guides and reference)

Quick links:
- [Installation Guide](https://svetzal.github.io/image-namer/installation/) - Detailed setup instructions
- [Getting Started](https://svetzal.github.io/image-namer/getting-started/) - Your first rename
- [How-To Guides](https://svetzal.github.io/image-namer/how-to/single-file/) - Step-by-step workflows
- [CLI Reference](https://svetzal.github.io/image-namer/reference/cli-commands/) - Complete command docs

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/svetzal/image-namer.git
cd image-namer

# Install with development dependencies (using uv)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Testing

```bash
pytest                    # Run all tests with coverage
pytest -v --no-cov       # Verbose without coverage
flake8 src               # Lint code
```

### Documentation

```bash
# Install docs dependencies (included in [dev])
pip install -e ".[dev]"

# Serve docs locally
mkdocs serve

# Build docs locally
mkdocs build
```

**Note**: Documentation is automatically deployed to GitHub Pages when a new release is published. See `docs/GITHUB_PAGES_SETUP.md` for details.

## Requirements

- Python 3.13 or later
- AI provider: Ollama (local) or OpenAI (cloud)

## License

MIT License - see [LICENSE](LICENSE)

## Project Status

✅ **Version 0.1.0** - Core functionality complete:
- Single file and batch folder renaming
- Markdown reference updates (standard + Obsidian)
- Intelligent caching system
- Provider abstraction (Ollama/OpenAI)

See [SPEC.md](SPEC.md) for detailed implementation status and roadmap.
