# Batch Folder Processing

Process multiple images in a folder efficiently with the `folder` command.

## Basic Usage

### Preview Folder (Non-Recursive)

By default, `image-namer folder` processes only the top-level folder without descending into subdirectories:

```bash
image-namer folder ~/Pictures/screenshots
```

Output:
```
╭────────────────────────────────────────────────────────────────────╮
│ File Rename Preview                                                │
├─────────────────────────┬──────────────────────────────────────────┤
│ Original                │ Proposed                                 │
├─────────────────────────┼──────────────────────────────────────────┤
│ screenshot-1.png        │ web-app-login--username-form.png         │
│ screenshot-2.png        │ sales-dashboard--quarterly-revenue.png   │
│ IMG_2345.jpg            │ golden-retriever--playing-in-park.jpg    │
╰─────────────────────────┴──────────────────────────────────────────╯

Summary: 3 files would be renamed, 0 unchanged, 0 conflicts
```

### Apply Folder Renames

Add `--apply` to actually rename the files:

```bash
image-namer folder ~/Pictures/screenshots --apply
```

## Recursive Processing

To process all images in subdirectories:

```bash
image-namer folder ~/Documents/project --recursive --apply
```

This walks the entire directory tree and processes every supported image.

### Example Directory Structure

```
project/
├── diagrams/
│   ├── architecture.png
│   └── database-schema.png
├── screenshots/
│   ├── ui-mockup.png
│   └── final-design.png
└── logo.png
```

```bash
image-namer folder project --recursive --apply
```

Renames all 5 images across all subdirectories.

## Filtering and Selection

### Supported Formats Only

Image Namer automatically skips unsupported files:

```bash
$ image-namer folder ~/Documents
Skipping: document.pdf (unsupported)
Skipping: notes.txt (unsupported)
Processing: diagram.png
Processing: screenshot.jpg
```

Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`

### Hidden Files and Directories

Image Namer processes hidden files (e.g., `.hidden-image.png`) but you can skip them by filtering at the shell level:

```bash
# Only visible files
image-namer folder ~/Pictures --apply
```

## Performance Considerations

### Caching Speeds Up Repeated Runs

First run (no cache):
```bash
$ time image-namer folder ~/Pictures/screenshots --apply
# Takes ~10-20 seconds for 10 images
```

Subsequent run (cached):
```bash
$ time image-namer folder ~/Pictures/screenshots --apply
# Takes ~1-2 seconds (all cached)
```

### Parallel Processing

Currently, Image Namer processes files sequentially. For large batches, this may take time. The cache significantly reduces re-run time.

## Collision Handling

When multiple images in a folder would get the same name, Image Namer automatically adds suffixes:

### Example: Multiple Similar Images

```
folder/
├── photo1.jpg (golden retriever in park)
├── photo2.jpg (golden retriever in park, different angle)
└── photo3.jpg (golden retriever in park, closeup)
```

After processing:
```
folder/
├── golden-retriever--running-in-park.jpg
├── golden-retriever--running-in-park-2.jpg
└── golden-retriever--running-in-park-3.jpg
```

The collision detection works both:
- **Against existing files** on disk
- **Against other files in the same batch** (intra-run collisions)

## Idempotency

Image Namer skips files that already have suitable names:

```bash
$ image-namer folder ~/Pictures
Processing: IMG_2345.jpg → golden-retriever--park.jpg
Skipping: web-dashboard--metrics.png (already suitable)
Skipping: architecture-diagram--microservices.png (already suitable)
```

This prevents unnecessary churn and API calls.

## Updating Markdown References

Update all markdown files that reference renamed images:

```bash
image-namer folder ~/Documents/notes/images --apply --update-refs --refs-root ~/Documents/notes
```

This:
1. Renames images in `~/Documents/notes/images/`
2. Updates markdown files in `~/Documents/notes/` that reference those images

### Example

Before:
```markdown
# My Notes

![Diagram](images/diagram.png)
![[images/screenshot.png]]
```

After running command:
```markdown
# My Notes

![Diagram](images/architecture-overview--microservices-api.png)
![[images/web-dashboard--sales-metrics.png]]
```

See [Updating Markdown References](markdown-refs.md) for detailed examples.

## Progress and Output

### Summary Statistics

After processing, Image Namer shows:

```
╭────────────────────────────────────────────────╮
│ Summary                                        │
├────────────────────────────────────────────────┤
│ Total files: 15                                │
│ Renamed: 10                                    │
│ Unchanged (already suitable): 3                │
│ Skipped (unsupported format): 2                │
│ Conflicts resolved: 1                          │
╰────────────────────────────────────────────────╯
```

### Detailed Table

For smaller batches, Image Namer shows a table of all changes:

```
╭────────────────────────────────────────────────────────────────────╮
│ File Rename Preview                                                │
├─────────────────────────┬──────────────────────────────────────────┤
│ Original                │ Proposed                                 │
├─────────────────────────┼──────────────────────────────────────────┤
│ IMG_2345.jpg            │ golden-retriever--running-in-park.jpg    │
│ screenshot.png          │ web-app-login--username-password.png     │
╰─────────────────────────┴──────────────────────────────────────────╯
```

## Advanced Options

### Different Provider/Model

```bash
image-namer folder ~/Pictures --provider openai --model gpt-4o --apply
```

### Set Defaults via Environment

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3:8b

image-namer folder ~/Pictures --apply
```

## Common Workflows

### Organize Downloaded Images

```bash
image-namer folder ~/Downloads --apply
```

### Process Project Screenshots

```bash
image-namer folder ~/Projects/my-app/screenshots --recursive --apply
```

### Organize Obsidian Attachments

```bash
image-namer folder ~/Documents/Obsidian/vault/attachments --apply --update-refs --refs-root ~/Documents/Obsidian/vault
```

### Bulk Rename Old Photos

```bash
# Preview first
image-namer folder ~/Pictures/Old\ Photos --recursive

# Apply if satisfied
image-namer folder ~/Pictures/Old\ Photos --recursive --apply
```

## Error Handling

### Permission Denied

If some files are not writable:

```
Error: Permission denied: /protected/image.png
Continuing with remaining files...
```

Image Namer continues processing other files.

### Disk Space

Renaming doesn't require additional disk space—it's an in-place operation.

### Interrupted Processing

If processing is interrupted (Ctrl+C), already-renamed files remain renamed. Re-run the command to continue:

```bash
# Interrupted after 5 files
^C

# Re-run to continue (already renamed files are skipped via cache)
image-namer folder ~/Pictures --apply
```

## Examples

### Screenshots Folder

```bash
# Organize all screenshots
image-namer folder ~/Desktop/screenshots --apply
```

### Project Documentation

```bash
# Rename all diagrams and update docs
image-namer folder ~/Projects/app/docs/images --recursive --apply --update-refs --refs-root ~/Projects/app/docs
```

### Photo Library Cleanup

```bash
# Preview first
image-namer folder ~/Pictures/Vacation\ 2024 --recursive

# Apply
image-namer folder ~/Pictures/Vacation\ 2024 --recursive --apply
```

## Next Steps

- [Updating Markdown References](markdown-refs.md) - Keep documentation in sync
- [Understanding the Cache](cache-management.md) - Optimize performance
- [CLI Commands Reference](../reference/cli-commands.md) - Complete command documentation
