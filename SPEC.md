# Image Namer — Product and Technical Specification (v1.0)

Last updated: 2025-11-02
**Implementation Status**: M1-M5 Complete ✅ — Version 1.0.0 Released 🎉

## 1. Vision
Rename image files based on their true visual contents using a multimodal vision model. The tool supports both command-line and a simple GUI, updates Markdown references safely, and produces an auditable report. Defaults favor local ML models: provider `ollama` with model `gemma3:27b`.

## 2. Goals and Non‑Goals
- Goals
  - ✅ Accurately rename one image file or all images in a folder using vision analysis.
  - ✅ Select provider and model at runtime; default to Ollama `gemma3:27b`.
  - ✅ Ensure idempotency and avoid churn (don't rename if a file already has a faithful name).
  - ✅ Update Markdown references to renamed files (standard and Obsidian wiki links) with safety.
  - ✅ Provide dry-run, collision handling, and a mapping report.
  - ❌ Offer a minimal PySide6 GUI for batch operations. (Moved to non-goals)

- Non‑Goals (v0.1)
  - Bulk processing across nested repositories or remote storages.
  - Non-image assets (video, PDF) — out of scope initially.
  - Complex image editing/redaction.
  - Multi-language UI; we assume English slugs for filenames.
  - PySide6 GUI — CLI is sufficient for v0.1

## 3. Personas
- ✅ Power user (CLI): Works in a notes/code repo, wants batch renaming with logs and repeatability.
- ⏸️ Knowledge worker (GUI): Uses a simple desktop window to pick a folder and run safe rename. (Future)
- ✅ Integrator (API/SDK): Wants to extend to new providers or add custom naming rules.

## 4. User Stories

### 4.1 Provider & Model Selection ✅
- As a user, I can choose the model provider (OpenAI or Ollama) and visual model to use.
  - Acceptance:
    - ✅ Default is `--provider ollama --model gemma3:27b`.
    - ✅ Configurable via CLI flags, env vars (`LLM_PROVIDER`, `LLM_MODEL`)

### 4.2 Single File Renaming ✅
- As a user, I can point to a single image and get a content-based new filename.
  - Acceptance:
    - ✅ The name follows the naming rubric (section 6) and keeps file extension.
    - ✅ If already faithful, no rename occurs (idempotent via assessment).

### 4.3 Folder Renaming (Flat) ✅
- As a user, I can process all supported images in a folder (non-recursive by default).
  - Acceptance:
    - ✅ Only supported image types are processed.
    - ✅ Optional `--recursive` to walk subdirectories (off by default).

### 4.4 Dry Run ✅
- As a user, I can preview the proposed renames without touching the filesystem.
  - Acceptance:
    - ✅ Emits a table of old -> new names and a summary (unchanged, proposed, conflicts).

### 4.5 Collision Handling ✅
- As a user, I can avoid conflicts when a proposed name already exists.
  - Acceptance:
    - ✅ The tool appends numeric suffixes (`-2`, `-3`, …) before the extension.
    - ✅ Idempotent: If the destination equals current name, do nothing.

### 4.6 Reference Updates (Markdown) ✅
- As a user, I want Markdown references updated when files are renamed.
  - Acceptance:
    - ✅ Supports standard Markdown images/links and Obsidian wiki links (with transclusions and aliases).
    - ✅ Preserves alt text and aliases; only updates the target path/basename.
    - ✅ A report lists which Markdown files were updated.
    - ✅ Handles URL-encoded paths and Unicode normalization

### 4.7 Error Handling ✅
- As a user, I want clear error messages when vision fails.
  - Acceptance:
    - ✅ Show user-friendly error and exit cleanly
    - ✅ No need for fallback naming schemes

### 4.8 Simple Output ✅
- As a user, I want clear output showing what happened.
  - Acceptance:
    - ✅ Rich-rendered panels/tables in CLI
    - ✅ Simple summary of changes made

## 5. Functional Requirements

### 5.1 Supported Formats ✅
- ✅ Input: png, jpg/jpeg, webp, gif (static), bmp, tif/tiff
- ✅ Output: Same extension preserved; only the basename changes.

### 5.2 Provider Abstraction ✅
- ✅ Use Mojentic as the LLM/agent abstraction.
- ✅ Providers: `ollama`, `openai`.
- ✅ Defaults: `ollama` + `gemma3:27b`.
- ✅ Config via:
  - CLI: `--provider`, `--model`
  - Env: `LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`

### 5.3 Vision Analysis Contract ✅
- ✅ Use Mojentic's LLMBroker with structured Pydantic output
- ✅ Return `ProposedName` with stem and extension
- ✅ Simple error handling (no complex confidence scores)

### 5.4 Naming Rubric ✅
- ✅ Slug format: lowercase, hyphens
- ✅ Baseline structure: `<primary-subject>--<specific-detail-or-context>.<ext>`
- ✅ Aim for ~5–8 words; prefer specificity
- ✅ Max length target: 80 chars
- ✅ Idempotency rules:
  - ✅ Pre-flight assessment checks if current name is already suitable
  - ✅ Skip generation entirely if assessment passes
  - ✅ Cache assessments separately from proposals

### 5.5 Collisions and Stability ✅
- ✅ If candidate name exists, append `-2`, `-3`, etc. before extension.
- ✅ Maintain a session map to avoid intra-run collisions.

### 5.6 Markdown Reference Updates ✅
- ✅ Targets: `*.md` files in the working directory (configurable root via `--refs-root`).
- ✅ Syntaxes handled:
  - Standard Markdown image: `![](/path/name.png)` and links `[text](/path/name.png)`
  - Obsidian wiki links: `[[name.png]]`, `![[name.png]]`, aliases `[[name.png|Alt]]`
- ✅ Preserve alt/alias text; only update filename/path portion.
- ✅ Report lists files updated and replacement counts per file.
- ✅ Handle URL-encoded paths and Unicode normalization

### 5.7 CLI Interface (Typer) ✅
- ✅ Commands:
  - `image-namer file IMAGE [--provider] [--model] [--dry-run/--apply] [--update-refs] [--refs-root]`
  - `image-namer folder DIR [--provider] [--model] [--dry-run/--apply] [--update-refs] [--refs-root] [--recursive]`
  - `image-namer generate IMAGE` (legacy, simple proposal only - **marked for deprecation**)
- ✅ Options:
  - `--provider [ollama|openai]` (default: `ollama`)
  - `--model TEXT` (default: `gemma3:27b`)
  - `--dry-run / --apply` (default: dry-run)
  - `--update-refs / --no-update-refs` (default: false)
  - `--refs-root PATH` (default: current working dir)
  - `--recursive` (folders only)

### 5.8 Configuration Precedence ✅
1) ✅ CLI flags
2) ✅ Environment variables
3) ✅ Tool defaults

### 5.9 Simple Output ✅
- ✅ Rich panels and tables for human-readable output
- ✅ Summary of actions taken
- ✅ Clear error messages

### 5.10 Errors & Edge Cases ✅
- ✅ Unsupported format → skip with warning
- ✅ LLM/vision errors → show clear error and exit
- ✅ Write permission denied → error handling in place
- ✅ Path normalization: URL decoding and Unicode normalization for markdown refs

### 5.11 Cache of Vision Results (Repository-local) ✅
- ✅ Purpose: Avoid repeated, slow LLM/vision calls by caching deterministic inputs and outputs per repo.
- ✅ Location: A hidden folder named `.image_namer/` at the repository root (i.e., the current working directory by default).
- ✅ Substructure:
  - `.image_namer/`
    - `version`: text file containing cache schema version (e.g., `1`)
    - `cache/`
      - `analysis/` — stores `NameAssessment` (is current filename suitable?)
      - `names/` — stores `ProposedName` (what should the new name be?)
    - ⏸️ `runs/` — per-run manifests for auditing (future enhancement)
    - ⏸️ `index.json` — quick lookup map (future optimization)
- ✅ Cache keys (fingerprints):
  - `content_sha256` of the image bytes
  - `provider` (e.g., `ollama` | `openai`)
  - `model` (e.g., `gemma3:27b`)
  - `rubric_version` (via `RUBRIC_VERSION` constant)
  - Composite cache key: `<sha256>__<provider>__<model>__v<rubric>`
- ✅ Files:
  - `analysis/<key>.json` — stores `NameAssessment` for current filename
  - `names/<key>.json` — stores `ProposedName` for new filename
- ✅ Read/Write policy:
  - **Two-tier caching**: Assessment first, then proposal only if needed
  - On processing an image:
    1. Check `analysis/<key>.json` for assessment of current name
    2. If suitable → skip generation entirely (major performance win)
    3. If unsuitable → check `names/<key>.json` for cached proposal
    4. If cache miss → call LLM and save result
  - Different provider/model → separate cache entry (keys coexist)
- ✅ Invalidation:
  - Changing image bytes → new `content_sha256` → bypass cache
  - Bump `RUBRIC_VERSION` when naming rules change
  - Different provider/model → separate cache entry
- ✅ Privacy & portability:
  - Cache is local to the repo, not uploaded
  - JSON files contain only hashes and minimal metadata (no image bytes)

### 5.12 Markdown Reference Root ✅
- ✅ Default `refs_root` is `.` (current working directory)
- ✅ Users can override via `--refs-root`
- ✅ Tool only scans/updates files under this root

## 6. Data Model (Pydantic) ✅
- ✅ `ProposedName`: stem, extension
- ✅ `NameAssessment`: suitable (bool) - for idempotency checking
- ✅ `MarkdownReference`: file_path, line_number, full_match, image_path
- ✅ `ReferenceUpdate`: file_path, replacement_count

## 7. Algorithms & Flow ✅
1) ✅ Validate input file(s)
2) ✅ For each image:
   - Check if supported format
   - **Pre-flight assessment**: Check if current filename is already suitable
     - Load from cache if available (`analysis/<key>.json`)
     - If suitable → mark as "unchanged" and skip generation
   - **Name generation** (only if assessment fails):
     - Load from cache if available (`names/<key>.json`)
     - If cache miss → Call LLM via Mojentic → get `ProposedName`
   - Check idempotency (current stem == proposed stem?)
   - Resolve collisions if needed (append -2, -3, etc.)
3) ✅ If `dry_run` → show what would happen and stop
4) ✅ If `--apply` → rename files
5) ✅ If `update_refs` → scan and update Markdown files
6) ✅ Show summary of what happened

## 8. Non‑Functional Requirements ✅
- ✅ Performance: Good enough for typical personal use (dozens of files); caching dramatically improves repeat runs
- ✅ Reliability: Dry-run by default, atomic renames via `Path.rename()`
- ✅ Security/Privacy: Local provider default (Ollama), cache stores only hashes (not image contents)
- ✅ Maintainability: Simple code, well-tested (94 tests), type-safe with Python 3.13+

## 9. Testing Strategy ✅
- ✅ Co-located `*_spec.py` tests alongside implementation
- ✅ Use `pytest`, `pytest-mock` fixtures
- ✅ Test coverage: collision resolution, idempotency, provider selection, dry-run vs apply, caching, markdown refs
- ✅ 94 passing tests with comprehensive coverage
- ✅ Keep complexity low (flake8 max-complexity: 10)

## 10. Milestones
- **M1** — ✅ Single-file rename with Ollama default (dry-run + apply)
- **M2** — ✅ Folder processing (flat and recursive)
- **M3** — ✅ Markdown reference updates (scan and patch)
- **M4** — ✅ Cache implementation for performance
- **M5** — ✅ Polish and release 1.0.0
  - ✅ Updated README to document all features
  - ✅ Created comprehensive CHANGELOG for v1.0.0
  - ✅ Version bump to 1.0.0
  - ✅ All tests passing (94 tests, 88% coverage)
  - ✅ Documentation deployed
  - 📝 Note: `generate` command remains for backward compatibility but `file --dry-run` is preferred

## 11. What We're NOT Building ✅
- ❌ GUI (PySide6) - CLI is sufficient for v0.1
- ✅ Complex confidence scoring - simple pass/fail works fine
- ✅ Configurable rubric - consistency is better (single `RUBRIC_VERSION`)
- ✅ Interactive prompts - standard CLI patterns work well
- ✅ Multiple output formats (JSON reports, etc.) - Rich output is enough
- ✅ `--endpoint`, `--api-key` flags - env vars work fine (`OPENAI_API_KEY`)
- ✅ Fallback naming schemes - clear error messages instead
- ❌ Per-run audit reports (`runs/` directory) - deferred to future version
- ❌ Cache index optimization (`index.json`) - current performance is acceptable
