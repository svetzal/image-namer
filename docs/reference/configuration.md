# Configuration

Complete configuration reference for Image Namer.

## Configuration Methods

Image Namer can be configured through:

1. **CLI Flags** (highest priority)
2. **Environment Variables** (medium priority)
3. **Defaults** (lowest priority)

CLI flags override environment variables, which override defaults.

## CLI Flags

### Global Flags

Available for all commands:

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--provider` | `ollama`, `openai` | `ollama` | AI provider to use |
| `--model` | Text | `gemma3:27b` | Model name |
| `--help` | - | - | Show help and exit |

### Command-Specific Flags

#### `file` and `folder` Commands

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--dry-run` | Boolean | `true` | Preview without changes |
| `--apply` | Boolean | `false` | Actually rename files |
| `--update-refs` | Boolean | `false` | Update markdown references |
| `--no-update-refs` | Boolean | `true` | Don't update markdown references |
| `--refs-root` | Path | `.` | Root directory for markdown search |

#### `folder` Command Only

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--recursive` | Boolean | `false` | Process subdirectories |

### Examples

```bash
# Use CLI flags
image-namer file photo.jpg --provider openai --model gpt-4o --apply

# Combine multiple flags
image-namer folder images/ --recursive --apply --update-refs --refs-root ~/Documents
```

## Environment Variables

### `LLM_PROVIDER`

Set the default AI provider.

**Values**: `ollama`, `openai`

**Default**: `ollama`

**Example**:
```bash
export LLM_PROVIDER=ollama
```

### `LLM_MODEL`

Set the default AI model name.

**Values**: Any model name supported by the provider

**Default**: `gemma3:27b`

**Example**:
```bash
export LLM_MODEL=llama3:8b
```

### `OPENAI_API_KEY`

OpenAI API key (required when using OpenAI provider).

**Format**: Starts with `sk-proj-` or `sk-`

**Required**: Only when `LLM_PROVIDER=openai`

**Example**:
```bash
export OPENAI_API_KEY='sk-proj-...'
```

### Setting Environment Variables

#### Bash/Zsh (Linux/macOS)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=gemma3:27b
export OPENAI_API_KEY='sk-proj-...'
```

Reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

#### Windows PowerShell

```powershell
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "gemma3:27b"
$env:OPENAI_API_KEY = "sk-proj-..."
```

For persistence, use `setx`:
```powershell
setx LLM_PROVIDER "ollama"
setx LLM_MODEL "gemma3:27b"
setx OPENAI_API_KEY "sk-proj-..."
```

#### Project-Specific `.env` File

Create `.env` in your project:

```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=gemma3:27b
```

Load before running:
```bash
source .env
image-namer folder images/ --apply
```

Or use `direnv` to auto-load:
```bash
# Install direnv
brew install direnv  # macOS
apt install direnv   # Linux

# Enable direnv
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc  # or ~/.bashrc

# Create .envrc
echo 'source .env' > .envrc

# Allow direnv
direnv allow
```

## Defaults

If no configuration is provided, Image Namer uses these defaults:

| Setting | Default Value |
|---------|---------------|
| Provider | `ollama` |
| Model | `gemma3:27b` |
| Dry-run | `true` (enabled) |
| Update refs | `false` (disabled) |
| Refs root | `.` (current directory) |
| Recursive | `false` (disabled) |

## Configuration Precedence

Settings are resolved in this order (highest to lowest priority):

```
1. CLI Flags (--provider, --model)
   ↓
2. Environment Variables (LLM_PROVIDER, LLM_MODEL)
   ↓
3. Defaults (ollama, gemma3:27b)
```

### Example

```bash
# Set environment
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o

# This uses OpenAI (from environment)
image-namer file photo.jpg

# This uses Ollama (CLI flag overrides environment)
image-namer file photo.jpg --provider ollama --model llama3:8b
```

## Provider Configuration

### Ollama

#### Installation

1. Download from [ollama.com](https://ollama.com)
2. Install and start the service
3. Pull a model:
   ```bash
   ollama pull gemma3:27b
   ```

#### Configuration

**No configuration required**—Ollama is the default provider.

**Custom model**:
```bash
export LLM_MODEL=llama3:8b
```

or

```bash
image-namer file photo.jpg --model llama3:8b
```

#### Supported Models

Any Ollama model with vision support:
- `gemma3:27b` (recommended)
- `llama3:8b`
- `llava:7b`
- `llava:13b`

See [Ollama model library](https://ollama.com/library) for more.

### OpenAI

#### Setup

1. Get API key from [platform.openai.com](https://platform.openai.com)
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY='sk-proj-...'
   ```

#### Configuration

**Provider**:
```bash
export LLM_PROVIDER=openai
```

**Model** (optional, defaults to `gemma3:27b` but OpenAI will use a vision-capable model):
```bash
export LLM_MODEL=gpt-4o
```

#### Supported Models

Vision-capable OpenAI models:
- `gpt-4o` (recommended)
- `gpt-4-turbo`
- `gpt-4-vision-preview`

See [OpenAI models](https://platform.openai.com/docs/models) for more.

## Configuration Profiles

Create shell scripts for different profiles:

### Local Profile (Ollama)

```bash
#!/bin/bash
# profile-local.sh

export LLM_PROVIDER=ollama
export LLM_MODEL=gemma3:27b

image-namer "$@"
```

Usage:
```bash
./profile-local.sh folder images/ --apply
```

### Cloud Profile (OpenAI)

```bash
#!/bin/bash
# profile-cloud.sh

export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export OPENAI_API_KEY='sk-proj-...'

image-namer "$@"
```

Usage:
```bash
./profile-cloud.sh folder images/ --apply
```

## Per-Project Configuration

### Project Script

Create a project-specific script:

```bash
#!/bin/bash
# rename-images.sh

# Project-specific config
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3:8b

# Run with project-specific options
image-namer folder docs/images \
  --recursive \
  --apply \
  --update-refs \
  --refs-root docs
```

### Makefile

```makefile
# Makefile

.PHONY: rename-images
rename-images:
	export LLM_PROVIDER=ollama && \
	export LLM_MODEL=gemma3:27b && \
	image-namer folder images/ --recursive --apply --update-refs
```

Usage:
```bash
make rename-images
```

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

**Cause**: Using OpenAI provider without setting API key

**Solution**:
```bash
export OPENAI_API_KEY='sk-proj-...'
```

### "Invalid provider: xyz"

**Cause**: Unsupported provider name

**Solution**: Use `ollama` or `openai`:
```bash
image-namer file photo.jpg --provider ollama
```

### Environment variables not working

**Cause**: Not exported or not reloaded

**Solutions**:

1. **Export** the variable (not just set):
   ```bash
   export LLM_PROVIDER=ollama  # ✅ Correct
   LLM_PROVIDER=ollama         # ❌ Wrong (not exported)
   ```

2. **Reload** shell config:
   ```bash
   source ~/.zshrc  # or ~/.bashrc
   ```

3. **Verify** it's set:
   ```bash
   echo $LLM_PROVIDER
   ```

### CLI flags not overriding environment

**Cause**: Likely a syntax error in the command

**Solution**: Check command syntax:
```bash
# ✅ Correct
image-namer file photo.jpg --provider ollama

# ❌ Wrong (missing argument)
image-namer file photo.jpg --provider
```

## Configuration Examples

### Example 1: Default (Ollama)

```bash
# No configuration needed
image-namer file photo.jpg --apply
```

Uses: `ollama` + `gemma3:27b`

### Example 2: Environment Variables

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3:8b

image-namer file photo.jpg --apply
```

Uses: `ollama` + `llama3:8b`

### Example 3: CLI Flags Override

```bash
export LLM_PROVIDER=openai

# Uses Ollama despite environment
image-namer file photo.jpg --provider ollama --apply
```

Uses: `ollama` + `gemma3:27b` (CLI flag wins)

### Example 4: Full Configuration

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export OPENAI_API_KEY='sk-proj-...'

image-namer folder ~/Documents/notes/images \
  --recursive \
  --apply \
  --update-refs \
  --refs-root ~/Documents/notes
```

Uses: `openai` + `gpt-4o`, processes recursively, updates markdown

## Best Practices

### ✅ Do

- Set environment variables in shell config for persistence
- Use CLI flags for one-off overrides
- Create project-specific scripts for complex workflows
- Use `--dry-run` (default) to preview before applying

### ❌ Don't

- Hardcode API keys in scripts (use environment variables)
- Mix configuration methods inconsistently (confusing)
- Override defaults without understanding precedence

## Next Steps

- [CLI Commands](cli-commands.md) - Complete command reference
- [Configuring Providers](../how-to/provider-config.md) - Detailed provider setup
- [Getting Started](../getting-started.md) - Quick start guide
