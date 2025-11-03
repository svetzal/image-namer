# Using the Graphical Interface

The Image Namer GUI provides a visual workflow for renaming images with AI vision analysis.

## Installation

The GUI requires the optional `[gui]` dependency group:

```bash
# Install with pipx (recommended)
pipx install 'image-namer[gui]'

# Or with pip
pip install 'image-namer[gui]'
```

This installs PySide6 (Qt6 for Python) which provides the graphical interface.

## Launching the GUI

```bash
image-namer-ui
```

The main window will open with the following layout:

- **Left panel**: Image preview
- **Right panel**: Results table with final names and status
- **Bottom**: Metadata panel showing detailed information
- **Top toolbar**: Provider/model selection and options
- **Menu bar**: File operations and help

## Basic Workflow

### 1. Select Folder

Click **📁 Open Folder** or use **File → Open Folder...** (Ctrl+O):

- Choose a directory containing images
- The **Include subdirectories** checkbox controls recursive scanning (default: ON)
- Supported formats: PNG, JPG/JPEG, WebP, GIF, BMP, TIF/TIFF

The results table will populate with all discovered images showing their current filenames.

### 2. Configure AI Provider

Use the toolbar dropdowns to select:

- **Provider**: `ollama` (local) or `openai` (cloud)
- **Model**: Available models for selected provider
  - Ollama default: `gemma3:27b`
  - OpenAI: `gpt-4o`, `gpt-4o-mini`, etc.

Your selections are persisted between sessions.

### 3. Process Images

Click **🚀 Process** to start AI analysis:

- Progress bar shows processing status
- Images are analyzed in the background
- **Preview panel** shows selected image
- **Metadata panel** displays:
  - Source filename
  - Current suitability ("Yes" if name already good)
  - Cache status ("Yes" if cached result used)
  - Proposed name from AI
  - Final name (accounting for collisions)
  - Reasoning from AI model

The status column shows:
- ⚠️ Not processed yet
- ✓ Ready to rename
- ⚠️ Collision detected (suffix will be added)
- — Unchanged (name already suitable)
- ⚠️ Error (processing failed)

### 4. Review and Edit

Click on any row in the results table to:

- **View** the image in the preview panel
- **Read** detailed metadata about the analysis
- **Edit** the final name by double-clicking the cell

When you manually edit a name:
- The metadata panel shows "Manually Edited: Yes 🔒"
- The name is locked and won't be overwritten by re-processing

### 5. Apply Renames

When satisfied with the proposed names:

1. Optionally check **Update references** to update markdown files
2. Click **💾 Apply** button
3. Confirm the rename operation
4. Files are renamed on disk

The **Refresh** button rescans the current folder without re-processing.

## Toolbar Options

### Provider Selection

- **ollama**: Uses local Ollama server (default port 11434)
- **openai**: Uses OpenAI API (requires `OPENAI_API_KEY` environment variable)

### Model Selection

Available models depend on the selected provider:

**Ollama models** (examples):
- `gemma3:27b` - Default, good balance
- `llava:latest` - Vision model
- `llava:13b` - Larger vision model

**OpenAI models** (examples):
- `gpt-4o` - Latest multimodal
- `gpt-4o-mini` - Faster, cheaper
- `gpt-4-turbo` - Previous generation

### Include Subdirectories

When enabled (default), folder selection will recursively find all images in subdirectories.

### Update References

When enabled (default), renaming files will automatically update markdown references:

- Standard Markdown: `![alt](path)` and `[text](path)`
- Obsidian wiki links: `[[file.png]]`, `![[file.png]]`, `[[file.png|alias]]`

Alt text and aliases are preserved.

## Menu Bar

### File Menu

- **Open Folder... (Ctrl+O)**: Select directory to process
- **Clear Cache...**: Remove all cached assessments and name proposals
- **Quit (Ctrl+Q)**: Exit application

### Help Menu

- **About**: Show application information

## Keyboard Shortcuts

- **Ctrl+O**: Open Folder
- **Ctrl+Q**: Quit
- **Double-click** table cell: Edit final name
- **Arrow keys**: Navigate table rows (updates preview)

## Tips & Best Practices

### Performance

- **Cache is your friend**: The GUI automatically loads cached results
- **Process incrementally**: Select smaller folders for faster feedback
- **Use Ollama** for offline work and privacy

### Editing Names

- Double-click any Final Name cell to edit
- Edited names are marked with 🔒 to prevent overwriting
- Click **Refresh** to reload without re-processing

### Markdown References

- Enable "Update references" before clicking Apply
- The GUI searches for markdown files in the selected folder and parent directories
- References are updated in-place, preserving formatting

### Cache Management

Clear the cache when:
- Switching to a different model
- Want fresh analysis without cache bias
- Cache files are corrupted or outdated

Use **File → Clear Cache...** to remove all cached data.

## Troubleshooting

### "Provider not available" Error

**Ollama not running:**
```bash
# Start Ollama server
ollama serve
```

**OpenAI API key not set:**
```bash
export OPENAI_API_KEY='sk-proj-...'
```

### No Images Found

- Check folder path is correct
- Verify file extensions are supported (PNG, JPG, etc.)
- Enable "Include subdirectories" if images are in subfolders

### Processing Hangs

- Check Ollama server is responsive: `ollama list`
- For OpenAI, verify API key and network connection
- Large batches may take time - watch progress bar

### Preview Not Showing

- Image file may be corrupted
- File permissions may prevent reading
- Try refreshing the folder

## Example Session

1. Launch GUI: `image-namer-ui`
2. Select folder: Click **Open Folder**, choose `~/Pictures/screenshots`
3. Configure: Set provider to `ollama`, model to `gemma3:27b`
4. Process: Click **Process** button
5. Review: Browse table, check preview panel for each image
6. Edit: Double-click any name to customize
7. Apply: Check "Update references", click **Apply**, confirm

Your files are renamed and all markdown references are updated!

## Next Steps

- Try the [Command Line Interface](single-file.md) for scripting
- Learn about [Cache Management](cache-management.md)
- Explore [Markdown Reference Updates](markdown-refs.md)
