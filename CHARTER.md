# Image Namer — Project Charter

## Purpose

Image Namer renames image files based on their visual contents using AI vision models (Ollama or OpenAI). It replaces opaque camera-generated filenames like `IMG_2347.jpg` with descriptive, content-based slugs like `golden-retriever-puppy--running-in-park.jpg`, and safely updates any Markdown references to the renamed files.

## Goals

- Produce accurate, descriptive filenames from image contents using multimodal vision models
- Default to local-first inference (Ollama) for privacy, with OpenAI as an alternative
- Provide both CLI and GUI interfaces for single-file and batch folder workflows
- Be idempotent — skip files that already have suitable names, cache LLM results to avoid redundant calls
- Safely update standard Markdown and Obsidian wiki-link references when files are renamed
- Support dry-run previews so users can review proposed changes before applying

## Non-Goals

- Processing non-image assets (video, PDF, audio)
- Multi-language filename generation — output is English slugs only
- Managing files across remote storage or cloud services
- Complex image editing, redaction, or transformation

## Target Users

- **Note-takers and knowledge workers** who accumulate images with meaningless filenames in Obsidian vaults or Markdown-based repositories
- **Developers and power users** who want batch renaming with caching, dry-run safety, and CLI scriptability
- **Integrators** who want to extend the tool with new providers or custom naming rules via the operations API
