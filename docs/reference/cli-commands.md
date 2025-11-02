# CLI Commands

Complete reference for all Image Namer CLI commands.

## Global Options

All commands support these global options:

| Option | Description | Default |
|--------|-------------|---------|
| `--provider [ollama\|openai]` | AI provider to use | `ollama` |
| `--model TEXT` | Model name | `gemma3:27b` |
| `--help` | Show help message | - |

## Commands

### `image-namer file`

Rename a single image file.

#### Syntax

```bash
image-namer file PATH [OPTIONS]
```

#### Arguments

- `PATH`: Path to the image file (required)

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview without making changes | ✅ Enabled |
| `--apply` | Actually rename the file | Disabled |
| `--update-refs` | Update markdown references | Disabled |
| `--no-update-refs` | Don't update markdown references | ✅ Enabled |
| `--refs-root PATH` | Root directory for markdown search | `.` (current directory) |
| `--provider [ollama\|openai]` | AI provider | `ollama` |
| `--model TEXT` | AI model | `gemma3:27b` |

#### Examples

```bash
# Preview rename (dry-run)
image-namer file photo.jpg

# Apply rename
image-namer file photo.jpg --apply

# Apply and update markdown references
image-namer file diagram.png --apply --update-refs

# Use OpenAI
image-namer file photo.jpg --provider openai --model gpt-4o --apply

# Specify markdown reference root
image-namer file ~/Pictures/photo.jpg --apply --update-refs --refs-root ~/Documents
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments or configuration |

---

### `image-namer folder`

Rename multiple images in a folder.

#### Syntax

```bash
image-namer folder PATH [OPTIONS]
```

#### Arguments

- `PATH`: Path to the folder (required)

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview without making changes | ✅ Enabled |
| `--apply` | Actually rename files | Disabled |
| `--recursive` | Process subdirectories | Disabled |
| `--update-refs` | Update markdown references | Disabled |
| `--no-update-refs` | Don't update markdown references | ✅ Enabled |
| `--refs-root PATH` | Root directory for markdown search | `.` (current directory) |
| `--provider [ollama\|openai]` | AI provider | `ollama` |
| `--model TEXT` | AI model | `gemma3:27b` |

#### Examples

```bash
# Preview folder (non-recursive, dry-run)
image-namer folder images/

# Apply to folder
image-namer folder images/ --apply

# Recursive processing
image-namer folder ~/Documents/notes --recursive --apply

# With markdown reference updates
image-namer folder images/ --apply --update-refs --refs-root .

# Use OpenAI
image-namer folder images/ --provider openai --model gpt-4o --apply
```

#### Behavior

- Processes only supported image formats
- Skips unsuitable files (non-images)
- Handles collisions automatically (adds `-2`, `-3`, etc.)
- Respects idempotency (skips already-suitable names)

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (all files processed) |
| 1 | General error |
| 2 | Invalid arguments or configuration |

---

### `image-namer generate`

Legacy command: Generate a proposed name without renaming.

!!! warning "Deprecated"
    This command is **deprecated** and may be removed in a future version. Use `image-namer file --dry-run` instead.

#### Syntax

```bash
image-namer generate PATH [OPTIONS]
```

#### Arguments

- `PATH`: Path to the image file (required)

#### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--provider [ollama\|openai]` | AI provider | `ollama` |
| `--model TEXT` | AI model | `gemma3:27b` |

#### Examples

```bash
# Generate name with Ollama
image-namer generate photo.jpg

# Generate name with OpenAI
image-namer generate photo.jpg --provider openai --model gpt-4o
```

#### Behavior

- Only shows the proposed name
- Does NOT rename the file
- Does NOT update markdown references
- Does NOT check idempotency

#### Migration

Replace `generate` with `file`:

```bash
# Old (deprecated)
image-namer generate photo.jpg

# New (recommended)
image-namer file photo.jpg
```

---

## Supported File Formats

Image Namer processes these image formats:

- `.png` - Portable Network Graphics
- `.jpg` / `.jpeg` - JPEG
- `.gif` - Graphics Interchange Format
- `.webp` - WebP
- `.bmp` - Bitmap
- `.tif` / `.tiff` - Tagged Image File Format

Other file types are skipped with a warning.

---

## Environment Variables

### `LLM_PROVIDER`

Set the default AI provider.

```bash
export LLM_PROVIDER=ollama  # or 'openai'
```

Overridden by `--provider` flag.

### `LLM_MODEL`

Set the default AI model.

```bash
export LLM_MODEL=gemma3:27b
```

Overridden by `--model` flag.

### `OPENAI_API_KEY`

OpenAI API key (required when using OpenAI provider).

```bash
export OPENAI_API_KEY='sk-proj-...'
```

---

## Configuration Precedence

Settings are applied in this order (highest to lowest priority):

1. **CLI flags**: `--provider`, `--model`
2. **Environment variables**: `LLM_PROVIDER`, `LLM_MODEL`
3. **Defaults**: `ollama` + `gemma3:27b`

### Example

```bash
# Set defaults via environment
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o

# Use defaults
image-namer file photo.jpg

# Override with CLI flags (uses Ollama despite environment)
image-namer file photo.jpg --provider ollama --model llama3:8b
```

---

## Common Patterns

### Dry-Run First, Then Apply

Always preview before applying:

```bash
# 1. Preview
image-namer folder images/

# 2. Review output

# 3. Apply if satisfied
image-namer folder images/ --apply
```

### Process Folder with References

```bash
image-namer folder images/ --recursive --apply --update-refs
```

### Different Providers per Project

```bash
# Project A: Local (Ollama)
cd ~/ProjectA
image-namer folder images/ --apply

# Project B: Cloud (OpenAI)
cd ~/ProjectB
image-namer folder images/ --provider openai --model gpt-4o --apply
```

### Batch Processing Script

```bash
#!/bin/bash
# rename-all.sh

for dir in ~/Documents/*/images; do
  echo "Processing $dir"
  image-namer folder "$dir" --apply --update-refs
done
```

---

## Error Handling

### Unsupported File Type

```bash
$ image-namer file document.pdf
Unsupported file type '.pdf'. Supported: ['.bmp', '.gif', '.jpeg', ...]
```

### File Not Found

```bash
$ image-namer file missing.jpg
Error: File not found: missing.jpg
```

### Permission Denied

```bash
$ image-namer file protected.jpg --apply
Error: Permission denied: protected.jpg
```

### OpenAI API Key Missing

```bash
$ image-namer file photo.jpg --provider openai
OPENAI_API_KEY environment variable not set
```

### Invalid Provider

```bash
$ image-namer file photo.jpg --provider invalid
Invalid provider: invalid
```

---

## Output Format

### Single File

```
╭─────────────────────────────────────────────────╮
│ Proposed Name                                   │
│ golden-retriever-puppy--running-in-park.jpg     │
╰─────────────────────────────────────────────────╯
```

### Folder (Table)

```
╭────────────────────────────────────────────────────────────────────╮
│ File Rename Preview                                                │
├─────────────────────────┬──────────────────────────────────────────┤
│ Original                │ Proposed                                 │
├─────────────────────────┼──────────────────────────────────────────┤
│ IMG_2345.jpg            │ golden-retriever--running-in-park.jpg    │
│ screenshot.png          │ web-app-login--username-password.png     │
╰─────────────────────────┴──────────────────────────────────────────╯

Summary: 2 files would be renamed, 0 unchanged, 0 conflicts
```

### Markdown References Updated

```
╭────────────────────────────────────────────────╮
│ Markdown References Updated                    │
├────────────────────────────────────────────────┤
│ notes/Architecture.md (2 replacements)         │
│ notes/Design.md (1 replacement)                │
╰────────────────────────────────────────────────╯
```

---

## Next Steps

- [Naming Rubric](naming-rubric.md) - Understand filename conventions
- [Configuration Reference](configuration.md) - Complete configuration details
- [How-To Guides](../how-to/single-file.md) - Step-by-step workflows
