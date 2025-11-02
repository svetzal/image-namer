# Updating Markdown References

When renaming images, you often need to update references to those images in markdown files. Image Namer can do this automatically.

## Basic Usage

Add `--update-refs` to any rename command:

```bash
# Single file
image-namer file diagram.png --apply --update-refs

# Folder
image-namer folder ~/Documents/notes/images --apply --update-refs
```

## How It Works

1. **Rename the image(s)** according to the command
2. **Scan for markdown files** in the reference root (default: current directory)
3. **Find all references** to the renamed image(s)
4. **Update the references** to use the new filename
5. **Report which files were modified**

## Supported Markdown Syntaxes

### Standard Markdown Images

```markdown
![Alt text](path/to/image.png)
```

After rename:
```markdown
![Alt text](path/to/new-name.png)
```

### Standard Markdown Links

```markdown
[Link text](path/to/image.png)
```

After rename:
```markdown
[Link text](path/to/new-name.png)
```

### Obsidian Wiki Links (Images)

```markdown
![[image.png]]
```

After rename:
```markdown
![[new-name.png]]
```

### Obsidian Wiki Links with Aliases

```markdown
![[image.png|My Image]]
[[image.png|Click here]]
```

After rename:
```markdown
![[new-name.png|My Image]]
[[new-name.png|Click here]]
```

**Alt text and aliases are preserved**—only the filename is updated.

## Specifying Reference Root

By default, Image Namer searches for markdown files in the **current working directory**. To search elsewhere, use `--refs-root`:

```bash
image-namer file ~/Pictures/diagram.png --apply --update-refs --refs-root ~/Documents/notes
```

This:
- Renames `~/Pictures/diagram.png`
- Searches for markdown files in `~/Documents/notes`
- Updates any references to `diagram.png`

### Example: Obsidian Vault

```
Obsidian/
├── vault/
│   ├── Notes/
│   │   ├── Architecture.md
│   │   └── Design.md
│   └── Attachments/
│       ├── diagram.png
│       └── screenshot.png
```

To rename images and update notes:

```bash
cd ~/Documents/Obsidian
image-namer folder vault/Attachments --apply --update-refs --refs-root vault
```

This updates all `.md` files in `vault/` that reference images in `Attachments/`.

## Path Handling

Image Namer handles various path formats:

### Relative Paths

```markdown
![](images/diagram.png)
![](./images/diagram.png)
![](../images/diagram.png)
```

All are updated correctly based on the file's location.

### Absolute Paths

```markdown
![](/Users/john/Documents/diagram.png)
```

Updated if the absolute path matches.

### URL-Encoded Paths

Obsidian sometimes encodes spaces and special characters:

```markdown
![[My%20Image%20File.png]]
```

Image Namer decodes these correctly:

```markdown
![[golden-retriever--running-in-park.png]]
```

### Unicode Normalization

Image Namer handles Unicode normalization (e.g., non-breaking spaces):

```markdown
![[image with spaces.png]]
```

Works even if the filesystem uses different Unicode representations.

## Output and Reporting

After updating references, Image Namer reports which files were modified:

```
╭────────────────────────────────────────────────╮
│ Markdown References Updated                    │
├────────────────────────────────────────────────┤
│ Notes/Architecture.md (2 replacements)         │
│ Notes/Design.md (1 replacement)                │
╰────────────────────────────────────────────────╯
```

### No References Found

If no markdown files reference the renamed images:

```
No markdown references found for renamed files.
```

This is normal if:
- The images aren't referenced anywhere
- The reference root doesn't contain the referencing files

## Safety and Idempotency

### Dry-Run Mode

Use dry-run to preview what would be updated **without changing anything**:

```bash
image-namer folder images --update-refs --refs-root .
```

This shows:
1. What images would be renamed
2. What markdown files would be updated

### Backup Recommendation

While Image Namer is safe, it's good practice to commit your changes to git before bulk updates:

```bash
# Commit before renaming
git add .
git commit -m "Before image rename"

# Run the rename
image-namer folder images --apply --update-refs

# Review changes
git diff

# Commit if satisfied
git add .
git commit -m "Renamed images and updated references"
```

### Idempotent Updates

Running the same command twice is safe:

```bash
# First run: renames files and updates refs
image-namer folder images --apply --update-refs

# Second run: no changes (files already renamed, refs already updated)
image-namer folder images --apply --update-refs
```

## Advanced Scenarios

### Multiple Markdown Formats

If your notes mix standard markdown and Obsidian syntax:

```markdown
# Architecture

Standard syntax:
![System Diagram](images/diagram.png)

Obsidian syntax:
![[images/diagram.png|System Diagram]]
```

Both are updated correctly:

```markdown
# Architecture

Standard syntax:
![System Diagram](images/architecture-overview--microservices.png)

Obsidian syntax:
![[images/architecture-overview--microservices.png|System Diagram]]
```

### Partial Path Matches

If markdown references use a shorter path:

```markdown
![](diagram.png)
```

And the image is at `~/Documents/notes/images/diagram.png`, Image Namer matches by **basename**:

```markdown
![](architecture-overview--microservices.png)
```

### Same Filename in Different Folders

If you have:
```
images/
├── folder1/
│   └── diagram.png
└── folder2/
    └── diagram.png
```

And markdown references:
```markdown
![](folder1/diagram.png)
![](folder2/diagram.png)
```

Image Namer updates only the matching path:
```markdown
![](folder1/architecture-overview--microservices.png)
![](folder2/database-schema--entity-relationships.png)
```

## Common Workflows

### Obsidian Vault Maintenance

```bash
cd ~/Documents/Obsidian/MyVault
image-namer folder Attachments --recursive --apply --update-refs --refs-root .
```

This:
1. Renames all images in `Attachments/`
2. Updates all notes in the vault that reference those images

### Documentation Project

```bash
cd ~/Projects/my-app
image-namer folder docs/images --apply --update-refs --refs-root docs
```

This:
1. Renames images in `docs/images/`
2. Updates markdown files in `docs/` (README, guides, etc.)

### Blog with Local Images

```bash
cd ~/Blog
image-namer folder static/images --apply --update-refs --refs-root content
```

This:
1. Renames images in `static/images/`
2. Updates markdown posts in `content/` that reference those images

## Troubleshooting

### "No markdown references found"

Possible causes:
1. **Wrong reference root**: Use `--refs-root` to specify the correct directory
2. **No markdown files**: The reference root doesn't contain `.md` files
3. **No references exist**: The images aren't referenced anywhere

### References Not Updated

Check:
1. **Path format**: Ensure markdown uses relative or absolute paths that match
2. **File location**: Ensure markdown files are under `--refs-root`
3. **Encoding**: Obsidian wiki links should work automatically

### Partial Updates

If some references are updated but not others:
- Check if different path formats are used (e.g., `./image.png` vs `image.png`)
- Ensure all markdown files are under the reference root

## Examples

### Single Image with References

```bash
# Current state
# - diagram.png
# - Architecture.md: ![](diagram.png)

image-namer file diagram.png --apply --update-refs

# Result
# - architecture-overview--microservices.png
# - Architecture.md: ![](architecture-overview--microservices.png)
```

### Folder with Mixed References

```bash
# Current state
# - images/screenshot1.png
# - images/screenshot2.png
# - Notes/page1.md: ![](images/screenshot1.png)
# - Notes/page2.md: ![[images/screenshot2.png]]

image-namer folder images --apply --update-refs --refs-root .

# Result
# - images/web-dashboard--metrics.png
# - images/mobile-app--login-screen.png
# - Notes/page1.md: ![](images/web-dashboard--metrics.png)
# - Notes/page2.md: ![[images/mobile-app--login-screen.png]]
```

## Next Steps

- [Single File Rename](single-file.md) - Rename individual images
- [Batch Folder Processing](batch-folder.md) - Process multiple images
- [CLI Commands Reference](../reference/cli-commands.md) - Complete command documentation
