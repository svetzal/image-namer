# Image Namer

**Rename image files based on their visual contents using AI vision models.**

Image Namer is a Python CLI tool that analyzes images using multimodal vision models and generates meaningful, descriptive filenames. No more `IMG_2347.jpg` or `screenshot-23.png`—get names like `golden-retriever-puppy--running-in-park.jpg` or `sales-chart--2024-quarterly-results.png`.

## Key Features

- **Vision-based naming**: Uses AI models (Ollama/OpenAI) to analyze image content and generate descriptive filenames
- **Local-first**: Defaults to Ollama with `gemma3:27b` for privacy-conscious users
- **Intelligent caching**: Avoids repeated API calls by caching results per image content hash
- **Idempotent**: Won't rename files that already have suitable names
- **Batch processing**: Process entire folders with `--recursive` option
- **Markdown reference updates**: Automatically updates links in your markdown/Obsidian notes
- **Dry-run mode**: Preview changes before applying them
- **Smart collision handling**: Automatically resolves filename conflicts

## Quick Example

```bash
# Preview what a file would be renamed to
image-namer file vacation-photo.jpg

# Apply the rename
image-namer file vacation-photo.jpg --apply

# Process entire folder (dry-run by default)
image-namer folder ~/Pictures/screenshots

# Process folder recursively and update markdown references
image-namer folder ~/Documents/notes --recursive --apply --update-refs
```

## Use Cases

- **Knowledge management**: Rename screenshots and images in your Obsidian/Notion vaults
- **Photo organization**: Generate descriptive names for personal photos
- **Documentation**: Rename diagrams and screenshots in your project docs
- **Digital asset management**: Organize downloaded images with meaningful names

## Getting Started

1. [Install Image Namer](installation.md) using `pipx` (recommended)
2. [Set up your AI provider](getting-started.md#provider-setup) (Ollama or OpenAI)
3. [Run your first rename](getting-started.md#your-first-rename)

## Philosophy

Image Namer follows these principles:

- **Privacy-first**: Default to local models (Ollama) to keep your images private
- **Descriptive over generic**: Generate specific, searchable filenames
- **Safe by default**: Dry-run mode prevents accidental changes
- **Performance-conscious**: Cache results to avoid unnecessary API calls
- **Integration-friendly**: Update markdown references to maintain link integrity

## Documentation Structure

- **[Installation](installation.md)**: Get Image Namer installed on your system
- **[Getting Started](getting-started.md)**: Quick start guide and basic workflows
- **[How-To Guides](how-to/single-file.md)**: Step-by-step guides for specific tasks
- **[Reference](reference/cli-commands.md)**: Detailed command and configuration reference

## Requirements

- Python 3.13 or later
- An AI provider: Ollama (local) or OpenAI (cloud)

## License

MIT License - see [LICENSE](https://github.com/svetzal/image-namer/blob/main/LICENSE)
