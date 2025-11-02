# Cache Structure

Technical reference for Image Namer's caching system.

## Overview

Image Namer uses a **repository-local cache** to store AI analysis results, avoiding redundant API calls.

**Location**: `.image_namer/` in your working directory

**Persistence**: Cache is persistent across runs and survives system reboots

**Scope**: Per-directory (each project has its own cache)

## Directory Structure

```
.image_namer/
├── version              # Cache schema version (plain text)
└── cache/
    ├── analysis/        # Name assessments (NameAssessment)
    │   ├── <key1>.json
    │   ├── <key2>.json
    │   └── ...
    └── names/           # Proposed names (ProposedName)
        ├── <key1>.json
        ├── <key2>.json
        └── ...
```

### `version` File

Contains the cache schema version as plain text:

```
1
```

This is used to detect incompatible cache formats.

### `cache/analysis/` Directory

Stores **name assessment results** (whether current filename is suitable).

### `cache/names/` Directory

Stores **proposed name results** (what the new filename should be).

## Cache Keys

Each cache entry is keyed by a composite identifier:

```
<sha256>__<provider>__<model>__v<rubric>
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `<sha256>` | SHA-256 hash of image bytes | `a1b2c3d4e5f6...7890` |
| `<provider>` | AI provider name | `ollama` or `openai` |
| `<model>` | Model name | `gemma3:27b` or `gpt-4o` |
| `v<rubric>` | Rubric version | `v1` |

### Example Key

```
a1b2c3d4e5f6789012345678901234567890abcdefabcdef1234567890abcd__ollama__gemma3:27b__v1
```

### File Extension

All cache entries have `.json` extension:

```
a1b2c3d4e5f6...7890__ollama__gemma3:27b__v1.json
```

## Cache Entry Formats

### Assessment Cache (`analysis/`)

Stores `NameAssessment` model:

```json
{
  "suitable": true
}
```

or

```json
{
  "suitable": false
}
```

**Purpose**: Determine if the current filename already follows the rubric.

### Name Cache (`names/`)

Stores `ProposedName` model:

```json
{
  "stem": "golden-retriever-puppy--running-in-park",
  "extension": ".jpg"
}
```

**Purpose**: Store the AI-generated proposed filename.

## Two-Tier Caching Strategy

Image Namer uses a **two-tier cache** for optimal performance:

### Tier 1: Assessment Cache

**Check first**: "Is the current filename already suitable?"

```python
assessment = load_from_cache("analysis/<key>.json")
if assessment.suitable:
    skip_rename()  # File already has good name
    return
```

**Benefit**: Avoid generating new names for files that are already well-named.

### Tier 2: Name Cache

**Check second**: "What should the new name be?"

```python
if assessment.unsuitable:
    proposed = load_from_cache("names/<key>.json")
    if proposed:
        use_cached_name(proposed)
    else:
        proposed = call_ai_model()
        save_to_cache("names/<key>.json", proposed)
```

**Benefit**: Avoid redundant AI calls for unsuitable filenames.

## Cache Lifecycle

### Write Flow

```
1. Process image
2. Compute SHA-256 hash
3. Build cache key (<hash>__<provider>__<model>__v<rubric>)
4. Check assessment cache
   ├─ Hit: Use cached assessment
   └─ Miss: Call AI, save result to analysis/<key>.json
5. If unsuitable, check name cache
   ├─ Hit: Use cached name
   └─ Miss: Call AI, save result to names/<key>.json
```

### Read Flow

```
1. Compute cache key
2. Check if cache file exists
   ├─ Exists: Load JSON, return result
   └─ Missing: Return None (cache miss)
```

### Invalidation

Cache entries are invalidated when:

1. **Image bytes change**: New SHA-256 hash → new cache key
2. **Provider changes**: Different provider → new cache key
3. **Model changes**: Different model → new cache key
4. **Rubric version bumps**: New rubric version → new cache key

## Cache Key Generation

### Python Implementation

```python
import hashlib
from pathlib import Path

def generate_cache_key(
    image_path: Path,
    provider: str,
    model: str,
    rubric_version: int
) -> str:
    # Compute SHA-256 of image bytes
    sha256 = hashlib.sha256()
    with open(image_path, "rb") as f:
        sha256.update(f.read())
    content_hash = sha256.hexdigest()

    # Build composite key
    return f"{content_hash}__{provider}__{model}__v{rubric_version}"
```

### Cache File Path

```python
from pathlib import Path

def assessment_cache_path(key: str) -> Path:
    return Path(".image_namer/cache/analysis") / f"{key}.json"

def name_cache_path(key: str) -> Path:
    return Path(".image_namer/cache/names") / f"{key}.json"
```

## Cache Storage Format

All cache entries use **JSON** with UTF-8 encoding.

### Writing

```python
import json
from pathlib import Path

def save_to_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

### Reading

```python
import json
from pathlib import Path

def load_from_cache(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

## Cache Size

### Per-Entry Size

- **Assessment**: ~50 bytes (just a boolean)
- **Proposed name**: ~100-200 bytes (stem + extension)

### Total Cache Size

For 100 images with 2 providers:
- Assessments: 100 × 2 × 50 bytes = 10 KB
- Names: 100 × 2 × 150 bytes = 30 KB
- **Total**: ~40 KB

Cache size is negligible for typical use cases.

## Cache Operations

### Initialize Cache

```bash
# Automatically created on first run
image-namer file photo.jpg
```

Creates:
```
.image_namer/
├── version
└── cache/
    ├── analysis/
    └── names/
```

### View Cache Entries

```bash
# List all assessments
ls .image_namer/cache/analysis/

# List all proposed names
ls .image_namer/cache/names/

# Count entries
ls .image_namer/cache/analysis/ | wc -l
ls .image_namer/cache/names/ | wc -l
```

### Read Cache Entry

```bash
# View assessment
cat .image_namer/cache/analysis/<key>.json

# View proposed name
cat .image_namer/cache/names/<key>.json
```

### Clear Cache

```bash
# Clear all cache
rm -rf .image_namer/

# Clear specific provider/model
rm .image_namer/cache/analysis/*__openai__gpt-4o__v1.json
rm .image_namer/cache/names/*__openai__gpt-4o__v1.json

# Clear old entries (older than 90 days)
find .image_namer/cache -type f -mtime +90 -delete
```

## Cache Isolation

### Per-Directory Isolation

Each working directory has its own cache:

```
~/ProjectA/
└── .image_namer/     # Cache for ProjectA

~/ProjectB/
└── .image_namer/     # Separate cache for ProjectB
```

### Per-Provider Isolation

Different providers/models have separate cache entries:

```
.image_namer/cache/names/
├── abc123...def__ollama__gemma3:27b__v1.json
├── abc123...def__ollama__llama3:8b__v1.json
├── abc123...def__openai__gpt-4o__v1.json
└── xyz789...uvw__ollama__gemma3:27b__v1.json
```

Same image (`abc123...def`) has 3 entries for 3 different models.

## Cache Sharing

### Git Repository

The cache can be committed to git:

```bash
# Add to version control
git add .image_namer/
git commit -m "Add image naming cache"
```

**Pros**:
- Team shares cache (saves time and API costs)
- Consistent naming across team

**Cons**:
- Cache size grows over time
- May cause merge conflicts if many images are processed

### Recommended: `.gitignore`

For most projects, exclude the cache:

```gitignore
# .gitignore
.image_namer/
```

Each developer maintains their own local cache.

### Shared Cache via Symlink

Share cache across multiple local projects:

```bash
# Create global cache
mkdir -p ~/.image_namer_global

# Link projects to global cache
cd ~/ProjectA
ln -s ~/.image_namer_global .image_namer

cd ~/ProjectB
ln -s ~/.image_namer_global .image_namer
```

Now both projects share the same cache.

## Cache Debugging

### Find Cache Entry for Image

```bash
# Compute SHA-256 of image
shasum -a 256 photo.jpg
# Output: a1b2c3d4e5f6...7890  photo.jpg

# Find matching cache entries
ls .image_namer/cache/*/a1b2c3d4e5f6...7890__*
```

### Verify Cache Key

```python
import hashlib

# Compute SHA-256
sha256 = hashlib.sha256()
with open("photo.jpg", "rb") as f:
    sha256.update(f.read())
print(sha256.hexdigest())
```

### Cache Statistics

```bash
# Total cache size
du -sh .image_namer/

# Number of assessments
ls .image_namer/cache/analysis/ | wc -l

# Number of proposed names
ls .image_namer/cache/names/ | wc -l

# List providers/models in cache
ls .image_namer/cache/names/ | sed 's/.*__\(.*\)__\(.*\)__v[0-9]*.json/\1 \2/' | sort -u
```

## Troubleshooting

### Cache Not Working

**Symptoms**: Image Namer re-analyzes every run despite cache

**Possible causes**:
1. Image bytes changed (new hash)
2. Different provider/model
3. Cache directory doesn't exist
4. Cache files corrupted

**Solutions**:

```bash
# Check if cache exists
ls .image_namer/cache/

# Check image hash
shasum -a 256 photo.jpg

# Verify provider/model in cache
ls .image_namer/cache/names/ | grep -i ollama
```

### Cache Corruption

**Symptoms**: JSON parsing errors

**Solution**:

```bash
# Clear and rebuild cache
rm -rf .image_namer/
image-namer folder images/ --apply
```

### Large Cache Size

**Symptoms**: `.image_namer/` is very large

**Causes**:
- Many images processed
- Multiple providers/models
- Old entries not cleaned up

**Solutions**:

```bash
# Remove old entries (90+ days)
find .image_namer/cache -type f -mtime +90 -delete

# Clear specific provider
rm .image_namer/cache/*__openai__*

# Clear entire cache
rm -rf .image_namer/
```

## Performance Impact

### Cache Hit (Warm Cache)

- **Latency**: ~0.1 seconds
- **API calls**: 0
- **Cost**: $0

### Cache Miss (Cold Cache)

- **Latency**: 2-5 seconds (Ollama) or 1-2 seconds (OpenAI)
- **API calls**: 1-2 (assessment + name generation)
- **Cost**: $0 (Ollama) or ~$0.01-0.02 (OpenAI)

**Speedup**: ~20-50x faster with warm cache

## Future Enhancements

### Per-Run Manifests (Not Yet Implemented)

Future versions may add per-run audit trails:

```
.image_namer/
└── runs/
    ├── 2024-11-02T14-30-00.json
    ├── 2024-11-02T15-45-00.json
    └── ...
```

### Cache Index (Not Yet Implemented)

Future versions may add a quick lookup index:

```
.image_namer/
└── index.json
```

This would speed up cache queries for large caches (1000+ entries).

## Next Steps

- [Understanding the Cache](../how-to/cache-management.md) - User-friendly cache guide
- [CLI Commands](cli-commands.md) - Commands that use the cache
- [Configuration](configuration.md) - Provider and model settings
