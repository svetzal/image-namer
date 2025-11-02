# Configuring Providers

Image Namer supports multiple AI providers for vision analysis. This guide covers configuration for Ollama and OpenAI.

## Overview

Image Namer uses AI vision models to analyze images and generate filenames. You can choose:

- **Ollama**: Local, privacy-friendly, free (recommended)
- **OpenAI**: Cloud-based, powerful models, requires API key

## Configuration Precedence

Settings are applied in this order (highest to lowest priority):

1. **CLI flags**: `--provider`, `--model`
2. **Environment variables**: `LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`
3. **Defaults**: `ollama` provider with `gemma3:27b` model

## Ollama Configuration

### Installation

1. **Download Ollama** from [ollama.com](https://ollama.com)
2. **Install** the application
3. **Start the service** (usually automatic)

### Pull a Model

Ollama requires models to be downloaded locally:

```bash
# Default model
ollama pull gemma3:27b

# Alternative models
ollama pull llama3:8b
ollama pull llava:7b
```

### Verify Installation

```bash
ollama list
```

You should see your downloaded models.

### Using Ollama (Default)

No configuration needed—just run Image Namer:

```bash
image-namer file photo.jpg --apply
```

This uses `ollama` + `gemma3:27b` by default.

### Using Different Ollama Models

Via CLI flag:

```bash
image-namer file photo.jpg --model llama3:8b --apply
```

Via environment variable:

```bash
export LLM_MODEL=llama3:8b
image-namer file photo.jpg --apply
```

### Ollama Configuration File

Ollama can be configured via environment variables. See [Ollama documentation](https://github.com/ollama/ollama/blob/main/docs/faq.md) for advanced settings.

### Troubleshooting Ollama

#### Connection Errors

If you see connection errors:

```bash
# Check if Ollama is running
ollama list

# If not running, start it
ollama serve
```

#### Model Not Found

```bash
$ image-namer file photo.jpg --model llama3:8b
Error: Model llama3:8b not found

# Pull the model first
ollama pull llama3:8b
```

#### Performance

Ollama runs models on your local hardware:

- **CPU-only**: Slower, but works everywhere
- **GPU acceleration**: Much faster if available

Check Ollama logs for GPU detection:

```bash
ollama serve
```

## OpenAI Configuration

### Get an API Key

1. **Sign up** at [platform.openai.com](https://platform.openai.com)
2. **Navigate** to API Keys
3. **Create** a new API key
4. **Copy** the key (starts with `sk-proj-...`)

### Set API Key

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export OPENAI_API_KEY='sk-proj-...'
```

Reload your shell:

```bash
source ~/.zshrc  # or ~/.bashrc
```

### Using OpenAI

Via CLI flags:

```bash
image-namer file photo.jpg --provider openai --model gpt-4o --apply
```

Via environment variables:

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export OPENAI_API_KEY='sk-proj-...'

image-namer file photo.jpg --apply
```

### Supported OpenAI Models

Vision-capable models:

- `gpt-4o` (recommended)
- `gpt-4-turbo`
- `gpt-4-vision-preview`

### OpenAI Costs

OpenAI charges per API request. Costs vary by model:

- **gpt-4o**: ~$0.01-0.02 per image
- **gpt-4-turbo**: Similar pricing

See [OpenAI Pricing](https://openai.com/pricing) for current rates.

**Use the cache** to minimize costs—Image Namer won't re-analyze unchanged images.

### Troubleshooting OpenAI

#### API Key Not Set

```bash
$ image-namer file photo.jpg --provider openai
OPENAI_API_KEY environment variable not set
```

Solution:

```bash
export OPENAI_API_KEY='sk-proj-...'
```

#### Invalid API Key

```bash
$ image-namer file photo.jpg --provider openai
Error: OpenAI API error: Invalid API key
```

Solution:
1. Check your API key at [platform.openai.com](https://platform.openai.com)
2. Ensure it's correctly copied (no extra spaces)

#### Rate Limit Errors

If processing many images quickly:

```
Error: OpenAI rate limit exceeded
```

Solutions:
- Wait a few minutes and retry
- Upgrade your OpenAI plan for higher limits
- Use Ollama instead (no rate limits)

#### Billing Issues

```
Error: Insufficient quota
```

Solution:
- Add billing information at [platform.openai.com](https://platform.openai.com/account/billing)

## Comparing Providers

| Feature | Ollama | OpenAI |
|---------|--------|--------|
| **Cost** | Free | ~$0.01-0.02 per image |
| **Privacy** | Local (no data sent) | Cloud (data sent to OpenAI) |
| **Speed** | Depends on hardware | Fast (cloud GPUs) |
| **Quality** | Good (depends on model) | Excellent |
| **Setup** | Download models (~4-8GB) | API key only |
| **Rate limits** | None | Yes (depends on plan) |

### When to Use Ollama

- You value privacy (data stays local)
- You process images regularly (one-time setup)
- You have decent hardware (GPU recommended but not required)
- You want zero ongoing costs

### When to Use OpenAI

- You need the best quality names
- You process images infrequently
- You don't want to download large models
- You're okay with cloud processing

## Advanced Configuration

### Per-Project Settings

Create a script in your project:

```bash
#!/bin/bash
# rename-images.sh

export LLM_PROVIDER=ollama
export LLM_MODEL=llama3:8b

image-namer folder images --recursive --apply --update-refs
```

### Multiple Providers

You can use different providers for different projects:

```bash
# Project A (local, privacy-sensitive)
cd ~/ProjectA
image-namer folder images --provider ollama --apply

# Project B (cloud, needs best quality)
cd ~/ProjectB
image-namer folder images --provider openai --model gpt-4o --apply
```

### Environment File

Create a `.env` file in your project:

```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=gemma3:27b
```

Source it before running:

```bash
source .env
image-namer folder images --apply
```

## Model Selection Guide

### Ollama Models

**Recommended**:
- `gemma3:27b`: Balanced speed and quality (default)
- `llama3:8b`: Faster, smaller, good quality

**Advanced**:
- `llava:7b`: Specialized vision model
- `llava:13b`: Better quality, slower

### OpenAI Models

**Recommended**:
- `gpt-4o`: Best quality, fast, cost-effective

**Alternative**:
- `gpt-4-turbo`: Similar to gpt-4o
- `gpt-4-vision-preview`: Older, may have different behavior

## Examples

### Default Configuration (Ollama)

```bash
image-namer file photo.jpg --apply
```

Uses: `ollama` + `gemma3:27b`

### Explicit Ollama with Different Model

```bash
image-namer file photo.jpg --provider ollama --model llama3:8b --apply
```

### OpenAI with Environment Variable

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export OPENAI_API_KEY='sk-proj-...'

image-namer file photo.jpg --apply
```

### Override Environment with CLI Flags

```bash
# Even with LLM_PROVIDER=openai in environment
image-namer file photo.jpg --provider ollama --apply
```

CLI flags always win.

## Next Steps

- [Understanding the Cache](cache-management.md) - Optimize performance
- [Batch Folder Processing](batch-folder.md) - Process multiple images
- [Configuration Reference](../reference/configuration.md) - Complete configuration details
