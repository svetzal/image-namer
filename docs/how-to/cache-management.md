# Understanding the Cache

Image Namer caches AI analysis results to improve performance and reduce API costs. This guide explains how the cache works and how to manage it.

## Why Caching Matters

AI vision analysis is:
- **Slow**: 2-5 seconds per image (Ollama) or 1-2 seconds (OpenAI)
- **Expensive**: ~$0.01-0.02 per image for OpenAI
- **Deterministic**: Same image + same model = same result

The cache eliminates redundant analysis.

## Cache Location

The cache is stored in a hidden directory at the root of your working directory:

```
.image_namer/
├── version              # Cache schema version (currently "1")
└── cache/
    ├── analysis/        # Name assessments (is current name suitable?)
    └── names/           # Proposed new names
```

Example:

```
~/Documents/notes/
├── .image_namer/
│   ├── version
│   └── cache/
│       ├── analysis/
│       │   ├── abc123...def__ollama__gemma3:27b__v1.json
│       │   └── xyz789...uvw__openai__gpt-4o__v1.json
│       └── names/
│           ├── abc123...def__ollama__gemma3:27b__v1.json
│           └── xyz789...uvw__openai__gpt-4o__v1.json
├── images/
│   ├── photo1.jpg
│   └── photo2.png
└── notes.md
```

## How Caching Works

### Cache Keys

Each cached result is keyed by:

1. **Image content hash (SHA-256)**: Changes if image bytes change
2. **Provider**: `ollama` or `openai`
3. **Model**: e.g., `gemma3:27b` or `gpt-4o`
4. **Rubric version**: Changes when naming rules change (currently `v1`)

Example cache key:
```
a1b2c3d4e5f6...7890__ollama__gemma3:27b__v1.json
```

### Two-Tier Caching

Image Namer uses **two-tier caching** for efficiency:

#### 1. Assessment Cache (`analysis/`)

Stores whether the **current filename** is already suitable.

```json
{
  "suitable": true
}
```

If suitable, Image Namer skips name generation entirely.

#### 2. Name Cache (`names/`)

Stores the **proposed new name** if the current name is unsuitable.

```json
{
  "stem": "golden-retriever-puppy--running-in-park",
  "extension": ".jpg"
}
```

### Processing Flow

```
1. Check assessment cache
   ├─ Cache hit + suitable → Skip (no rename needed)
   └─ Cache miss OR unsuitable → Continue to step 2

2. Check name cache
   ├─ Cache hit → Use cached name
   └─ Cache miss → Call AI model, cache result
```

This two-tier approach is a **huge performance win**—files with suitable names are skipped immediately.

## Cache Performance

### First Run (Cold Cache)

```bash
$ time image-namer folder images/
# Processing 10 images
# Time: ~30 seconds (Ollama) or ~15 seconds (OpenAI)
```

### Subsequent Run (Warm Cache)

```bash
$ time image-namer folder images/
# Processing 10 images (all cached)
# Time: ~1 second
```

**99% speedup** on cached runs!

## Cache Invalidation

The cache is invalidated when:

### 1. Image Content Changes

Editing an image creates a new SHA-256 hash:

```bash
# Original image
image-namer file photo.jpg --apply
# Result: landscape-photo--sunset-over-mountains.jpg

# Edit the image (crop, adjust colors, etc.)

# Re-run
image-namer file landscape-photo--sunset-over-mountains.jpg --apply
# New analysis, may get different name
```

### 2. Provider or Model Changes

Different provider/model = different cache entry:

```bash
# First run with Ollama
image-namer file photo.jpg --provider ollama --model gemma3:27b

# Second run with OpenAI (different cache key)
image-namer file photo.jpg --provider openai --model gpt-4o
```

Both results are cached separately.

### 3. Rubric Version Changes

When Image Namer's naming rules change, the rubric version is bumped (e.g., `v1` → `v2`). This invalidates all cache entries.

## Managing the Cache

### View Cache Size

```bash
du -sh .image_namer/
# Example: 256K    .image_namer/
```

Each cached result is ~1KB (just metadata, no image data).

### Clear Cache

Delete the cache directory:

```bash
rm -rf .image_namer/
```

Next run will rebuild the cache.

### Clear Cache for Specific Provider/Model

```bash
cd .image_namer/cache/analysis
rm *__openai__gpt-4o__v1.json

cd ../names
rm *__openai__gpt-4o__v1.json
```

This clears only OpenAI GPT-4o cache entries.

### Cache Per Directory

The cache is **per working directory**. Different projects have separate caches:

```
~/ProjectA/
└── .image_namer/     # Cache for ProjectA

~/ProjectB/
└── .image_namer/     # Separate cache for ProjectB
```

This is intentional—cache is project-specific.

## Privacy and Security

### What's Stored in the Cache?

- **Image content hash** (SHA-256)
- **Provider and model names**
- **Proposed filename** or assessment result
- **Timestamps** (created, accessed)

### What's NOT Stored?

- **Image pixels/bytes**: Only the hash
- **File paths**: Only basenames
- **Personal data**: Only filenames

### Cache Privacy

The cache is stored locally and never uploaded. It's safe to commit to version control (but usually not necessary).

### Sharing Caches

You can share `.image_namer/` with your team to avoid redundant API calls:

```bash
# Add to .gitignore if you don't want to share
echo ".image_namer/" >> .gitignore

# Or commit to share
git add .image_namer/
git commit -m "Add image naming cache"
```

**Pros**: Team saves time and API costs
**Cons**: Cache size grows over time

## Advanced Scenarios

### Multiple Working Directories

If you process the same image in different directories, each gets its own cache:

```bash
cd ~/ProjectA
image-namer file ~/Pictures/photo.jpg
# Creates ~/ProjectA/.image_namer/

cd ~/ProjectB
image-namer file ~/Pictures/photo.jpg
# Creates ~/ProjectB/.image_namer/
```

Both caches are independent.

### Portable Cache

To reuse a cache across projects, symlink it:

```bash
mkdir -p ~/.image_namer_global
cd ~/ProjectA
ln -s ~/.image_namer_global .image_namer

cd ~/ProjectB
ln -s ~/.image_namer_global .image_namer
```

Now both projects share the same cache.

### CI/CD Caching

In CI pipelines, cache `.image_namer/` between runs:

```yaml
# .github/workflows/rename-images.yml
- uses: actions/cache@v3
  with:
    path: .image_namer
    key: image-namer-cache-${{ hashFiles('images/**') }}
```

This speeds up repeated CI runs.

## Cache Debugging

### View Cache Entry

```bash
cat .image_namer/cache/names/abc123...def__ollama__gemma3:27b__v1.json
```

Output:
```json
{
  "stem": "golden-retriever-puppy--running-in-park",
  "extension": ".jpg"
}
```

### Find Cache Entry for Specific Image

```bash
# Get image hash
shasum -a 256 photo.jpg
# Output: a1b2c3d4e5f6...7890  photo.jpg

# Find cache entry
ls .image_namer/cache/names/a1b2c3d4e5f6...7890__*
```

### Cache Statistics

```bash
# Count cached assessments
ls .image_namer/cache/analysis/ | wc -l

# Count cached names
ls .image_namer/cache/names/ | wc -l

# Total cache size
du -sh .image_namer/
```

## Best Practices

### ✅ Do

- Keep the cache in version control if your team shares a repo
- Clear the cache if you change naming preferences (but this requires a rubric version bump)
- Use the cache to minimize OpenAI costs

### ❌ Don't

- Manually edit cache files (corruption risk)
- Share cache across unrelated projects (bloat)
- Delete the cache unnecessarily (forces re-analysis)

## Troubleshooting

### Cache Not Working

If Image Namer seems to re-analyze cached images:

1. **Check image hash**: Ensure image bytes haven't changed
   ```bash
   shasum -a 256 photo.jpg
   ```
2. **Check provider/model**: Ensure you're using the same settings
   ```bash
   image-namer file photo.jpg --provider ollama --model gemma3:27b
   ```
3. **Check cache directory**: Ensure `.image_namer/` exists
   ```bash
   ls -la .image_namer/
   ```

### Cache Corruption

If you see errors like "invalid JSON":

```bash
# Clear and rebuild cache
rm -rf .image_namer/
image-namer folder images --apply
```

### Large Cache Size

If `.image_namer/` grows too large:

```bash
# Remove old entries (requires manual inspection)
find .image_namer/ -type f -mtime +90 -delete  # Older than 90 days
```

Or just clear the entire cache:

```bash
rm -rf .image_namer/
```

## Examples

### Check Cache Before/After

```bash
# Before
ls .image_namer/cache/names/

# Run command
image-namer file photo.jpg

# After (new cache entry created)
ls .image_namer/cache/names/
```

### Compare Providers

```bash
# Cache with Ollama
image-namer file photo.jpg --provider ollama --model gemma3:27b

# Cache with OpenAI (separate entry)
image-namer file photo.jpg --provider openai --model gpt-4o

# Both cached separately
ls .image_namer/cache/names/
```

### Measure Performance Improvement

```bash
# Clear cache
rm -rf .image_namer/

# First run (cold)
time image-namer folder images/

# Second run (warm)
time image-namer folder images/
```

## Next Steps

- [Batch Folder Processing](batch-folder.md) - Leverage caching for large batches
- [Configuring Providers](provider-config.md) - Optimize provider selection
- [Cache Structure Reference](../reference/cache-structure.md) - Technical cache details
