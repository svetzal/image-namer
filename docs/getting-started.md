# Getting Started

This guide will walk you through your first image rename with Image Namer.

## Prerequisites

Before starting, ensure you have:

1. ✅ [Installed Image Namer](installation.md)
2. ✅ An AI provider set up (Ollama or OpenAI)

## Provider Setup

Image Namer needs an AI vision model to analyze images. You can use either Ollama (local) or OpenAI (cloud).

### Option 1: Ollama (Recommended)

Ollama runs models locally on your machine—no data leaves your computer.

1. **Install Ollama**: Download from [ollama.com](https://ollama.com)
2. **Pull the default model**:
   ```bash
   ollama pull gemma3:27b
   ```
3. **Verify it's running**:
   ```bash
   ollama list
   ```

That's it! Image Namer will automatically use Ollama by default.

### Option 2: OpenAI

If you prefer cloud-based models:

1. **Get an API key** from [platform.openai.com](https://platform.openai.com)
2. **Set the environment variable**:
   ```bash
   export OPENAI_API_KEY='sk-proj-...'
   ```
3. **Use OpenAI when running commands**:
   ```bash
   image-namer file photo.jpg --provider openai --model gpt-4o
   ```

!!! tip "Save your API key"
    Add `export OPENAI_API_KEY='...'` to your `~/.zshrc` or `~/.bashrc` to persist it across terminal sessions.

## Your First Rename

Let's rename a single image file.

### 1. Preview the Rename (Dry Run)

By default, Image Namer shows you what **would** happen without making changes:

```bash
image-namer file screenshot.png
```

Output:
```
╭─────────────────────────────────────────────────╮
│ Proposed Name                                   │
│ web-app-login-screen--username-password.png     │
╰─────────────────────────────────────────────────╯
```

### 2. Apply the Rename

If you like the proposed name, apply it:

```bash
image-namer file screenshot.png --apply
```

The file is now renamed to `web-app-login-screen--username-password.png`.

### 3. Try Another Image

```bash
image-namer file vacation-photo.jpg --apply
```

## Understanding the Output

Image Namer follows a **naming rubric** to generate consistent filenames:

- **Format**: `<primary-subject>--<specific-detail>.<ext>`
- **Style**: Lowercase, hyphen-separated words
- **Length**: 5-8 words, max 80 characters
- **Examples**:
    - `golden-retriever-puppy--running-in-park.jpg`
    - `sales-chart--q4-2024-revenue-comparison.png`
    - `mountain-landscape--sunset-over-lake.webp`

See the [Naming Rubric](reference/naming-rubric.md) for complete details.

## Common Workflows

### Rename Multiple Files in a Folder

```bash
# Preview all images in a folder
image-namer folder ~/Pictures/screenshots

# Apply renames
image-namer folder ~/Pictures/screenshots --apply
```

### Recursive Folder Processing

```bash
# Process all images in folder and subfolders
image-namer folder ~/Documents/project --recursive --apply
```

### Update Markdown References

If you have markdown files linking to images, update them automatically:

```bash
image-namer folder ~/Documents/notes --apply --update-refs
```

This updates:
- Standard markdown: `![alt](old-name.png)` → `![alt](new-name.png)`
- Obsidian wiki links: `![[old-name.png]]` → `![[new-name.png]]`

## Configuration

### Using Different Providers/Models

```bash
# Use OpenAI with GPT-4o
image-namer file photo.jpg --provider openai --model gpt-4o --apply

# Use Ollama with a different model
image-namer file photo.jpg --provider ollama --model llama3:8b --apply
```

### Set Default Provider via Environment

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o

# Now this uses OpenAI by default
image-namer file photo.jpg --apply
```

## Understanding the Cache

Image Namer caches results to avoid redundant API calls. The cache is stored in `.image_namer/cache/` in your working directory.

**Key behaviors**:

- Same image + same provider + same model = cached result
- Changing the image content invalidates the cache
- Different providers/models have separate cache entries

Learn more in [Understanding the Cache](how-to/cache-management.md).

## Next Steps

- [Single File Rename Guide](how-to/single-file.md) - Detailed single-file workflow
- [Batch Folder Processing](how-to/batch-folder.md) - Process multiple images efficiently
- [Updating Markdown References](how-to/markdown-refs.md) - Keep your notes in sync
- [Configuring Providers](how-to/provider-config.md) - Advanced provider configuration

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

You're trying to use OpenAI without setting the API key. Either:
- Set the environment variable: `export OPENAI_API_KEY='sk-...'`
- Use Ollama instead (default): `image-namer file photo.jpg`

### "Unsupported file type"

Image Namer supports: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`

Other formats are not supported.

### Connection errors with Ollama

Ensure Ollama is running:
```bash
ollama list
```

If not running, start it:
```bash
ollama serve
```

### File already has a suitable name

If Image Namer says the name is already suitable, it means the current filename matches the naming rubric. This is the **idempotency feature**—it prevents unnecessary churn.
