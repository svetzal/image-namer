# Installation

This guide will help you install Image Namer on your system.

## Choose Your Installation

Image Namer offers two interfaces:

- **CLI only** (lightweight): ~50MB with dependencies
- **CLI + GUI** (full experience): ~150MB including Qt6 libraries

## Recommended: pipx Installation

**pipx is the recommended installation method** for Image Namer. It installs Python CLI tools in isolated environments, preventing dependency conflicts with other Python projects on your system.

### 1. Install pipx

If you don't already have pipx:

=== "macOS"
    ```bash
    brew install pipx
    pipx ensurepath
    ```

=== "Linux"
    ```bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

=== "Windows"
    ```powershell
    python -m pip install --user pipx
    python -m pipx ensurepath
    ```

After installation, **restart your terminal** to ensure the PATH is updated.

### 2. Install Image Namer

**CLI Only (lightweight):**
```bash
pipx install image-namer
```

**CLI + GUI (recommended):**
```bash
pipx install 'image-namer[gui]'
```

The `[gui]` extra installs PySide6 (Qt6 for Python), which adds the graphical interface.

### 3. Verify Installation

**CLI:**
```bash
image-namer --help
```

**GUI (if installed with [gui]):**
```bash
image-namer-ui
```

## Alternative: pip Installation

!!! warning "Not Recommended"
    Installing with pip can cause dependency conflicts with other Python projects. Use pipx unless you have a specific reason not to.

**CLI only:**
```bash
pip install image-namer
```

**CLI + GUI:**
```bash
pip install 'image-namer[gui]'
```

## Development Installation

If you're contributing to Image Namer or want to modify the code:

### 1. Clone the Repository

```bash
git clone https://github.com/svetzal/image-namer.git
cd image-namer
```

### 2. Install with Development Dependencies

Using **uv** (recommended for development):

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install with GUI for testing
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,gui]"
```

Using **pip**:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev,gui]"
```

The `[dev]` extra includes testing tools (pytest, flake8, mypy) and documentation tools (mkdocs).
The `[gui]` extra includes PySide6 for the graphical interface.

## System Requirements

- **Python 3.13 or later**
- **AI Provider**: You'll need either:
    - **Ollama** (recommended): Local, privacy-friendly, free
    - **OpenAI API**: Cloud-based, requires API key and costs money

### Installing Ollama (Recommended)

Ollama runs AI models locally on your machine:

1. Download from [ollama.com](https://ollama.com)
2. Install the application
3. Pull the default model:
   ```bash
   ollama pull gemma3:27b
   ```

Ollama runs as a background service and provides a local API endpoint.

### Setting up OpenAI

If you prefer OpenAI:

1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. Set the environment variable:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

Add this to your `~/.zshrc`, `~/.bashrc`, or equivalent shell config for persistence.

## Upgrading

### pipx Installation

```bash
pipx upgrade image-namer
```

### pip Installation

```bash
pip install --upgrade git+https://github.com/svetzal/image-namer.git
```

### Development Installation

```bash
cd image-namer
git pull
uv pip install -e ".[dev,gui]"  # or: pip install -e ".[dev,gui]"
```

## Uninstalling

### pipx Installation

```bash
pipx uninstall image-namer
```

### pip Installation

```bash
pip uninstall image-namer
```

## Next Steps

- [Getting Started Guide](getting-started.md) - Set up your provider and run your first rename
- [Using the GUI](how-to/using-gui.md) - Visual workflow guide (if installed with [gui])
- [Configure Providers](how-to/provider-config.md) - Detailed provider configuration
