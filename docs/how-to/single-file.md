# Single File Rename

This guide covers everything about renaming individual image files.

## Basic Usage

### Preview a Rename (Dry Run)

By default, `image-namer file` shows what the new name would be without making changes:

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

### Apply the Rename

Add `--apply` to actually rename the file:

```bash
image-namer file screenshot.png --apply
```

The file `screenshot.png` is now renamed to `web-app-login-screen--username-password.png`.

## Provider and Model Selection

### Using Default (Ollama)

By default, Image Namer uses Ollama with `gemma3:27b`:

```bash
image-namer file photo.jpg --apply
```

### Using OpenAI

To use OpenAI instead:

```bash
image-namer file photo.jpg --provider openai --model gpt-4o --apply
```

!!! note "OpenAI API Key Required"
    Set `OPENAI_API_KEY` environment variable before using OpenAI:
    ```bash
    export OPENAI_API_KEY='sk-proj-...'
    ```

### Using Different Ollama Models

```bash
# Use Llama 3 8B model
ollama pull llama3:8b
image-namer file photo.jpg --provider ollama --model llama3:8b --apply
```

## Idempotency

Image Namer is **idempotent**—it won't rename a file if it already has a suitable name.

### Example: Already Suitable Name

```bash
image-namer file golden-retriever-puppy--running-in-park.jpg
```

Output:
```
File already has a suitable name. No rename needed.
```

This prevents unnecessary churn and repeated API calls.

### How It Works

1. Image Namer first **assesses** if the current filename is suitable
2. If suitable, it skips the rename (and caches the assessment)
3. If unsuitable, it generates a new name

## Collision Handling

If the proposed name already exists, Image Namer automatically adds a numeric suffix:

```bash
# If web-app-login.png already exists
image-namer file screenshot.png --apply
```

The file is renamed to:
- `web-app-login-2.png` (if `web-app-login.png` exists)
- `web-app-login-3.png` (if both exist)
- And so on...

## Updating Markdown References

If you have markdown files that reference the image, update them automatically:

```bash
image-namer file diagram.png --apply --update-refs
```

This updates:
- Standard markdown: `![Diagram](diagram.png)` → `![Diagram](system-architecture--microservices-overview.png)`
- Obsidian wiki links: `![[diagram.png]]` → `![[system-architecture--microservices-overview.png]]`

### Specify Reference Root

By default, Image Namer searches for markdown files in the current directory. To search elsewhere:

```bash
image-namer file ~/Pictures/diagram.png --apply --update-refs --refs-root ~/Documents/notes
```

This updates markdown files in `~/Documents/notes` that reference `diagram.png`.

## Supported File Formats

Image Namer supports these formats:

- `.png`
- `.jpg` / `.jpeg`
- `.gif`
- `.webp`
- `.bmp`
- `.tif` / `.tiff`

Other formats are rejected with an error.

## Working with Paths

### Absolute Paths

```bash
image-namer file /Users/john/Pictures/vacation-photo.jpg --apply
```

### Relative Paths

```bash
image-namer file ../images/logo.png --apply
```

### Current Directory

```bash
cd ~/Pictures
image-namer file vacation-photo.jpg --apply
```

## Performance and Caching

Image Namer caches results to avoid redundant AI calls.

### First Run (Cache Miss)

```bash
$ time image-namer file photo.jpg
# Takes ~2-5 seconds (AI inference)
```

### Subsequent Run (Cache Hit)

```bash
$ time image-namer file photo.jpg
# Takes ~0.1 seconds (cached)
```

The cache is stored in `.image_namer/cache/` and is keyed by:
- Image content hash (SHA-256)
- Provider + model
- Rubric version

See [Understanding the Cache](cache-management.md) for details.

## Advanced Options

### Override Configuration via Environment

Set defaults via environment variables:

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export OPENAI_API_KEY='sk-...'

# Now uses OpenAI by default
image-namer file photo.jpg --apply
```

CLI flags override environment variables:

```bash
# Uses Ollama despite LLM_PROVIDER=openai
image-namer file photo.jpg --provider ollama --apply
```

## Error Handling

### Unsupported File Type

```bash
$ image-namer file document.pdf
Unsupported file type '.pdf'. Supported: ['.bmp', '.gif', '.jpeg', ...]
```

### File Not Found

```bash
$ image-namer file missing.png
Error: File not found: missing.png
```

### Permission Denied

```bash
$ image-namer file /system/protected.png --apply
Error: Permission denied: /system/protected.png
```

### OpenAI API Error

```bash
$ image-namer file photo.jpg --provider openai
OPENAI_API_KEY environment variable not set
```

Solution:
```bash
export OPENAI_API_KEY='sk-proj-...'
```

## Examples

### Rename a Screenshot

```bash
image-namer file ~/Desktop/screenshot-2024-11-02.png --apply
```

Result: `web-dashboard--sales-metrics-chart.png`

### Rename a Photo

```bash
image-namer file vacation-photo.jpg --apply
```

Result: `mountain-landscape--sunset-over-alpine-lake.jpg`

### Rename a Diagram

```bash
image-namer file system-diagram.png --apply --update-refs --refs-root ~/Documents/notes
```

Result: `architecture-diagram--microservices-api-gateway.png` (and updates markdown files)

## Next Steps

- [Batch Folder Processing](batch-folder.md) - Rename multiple files at once
- [Updating Markdown References](markdown-refs.md) - Keep your notes in sync
- [Naming Rubric Reference](../reference/naming-rubric.md) - Understanding the naming convention
