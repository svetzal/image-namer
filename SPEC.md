# Image Namer — Product and Technical Specification (v0.1 Draft)

Last updated: 2025-11-02

## 1. Vision
Rename image files based on their true visual contents using a multimodal vision model. The tool supports both command-line and a simple GUI, updates Markdown references safely, and produces an auditable report. Defaults favor local ML models: provider `ollama` with model `gemma3:27b`.

## 2. Goals and Non‑Goals
- Goals
  - Accurately rename one image file or all images in a folder using vision analysis.
  - Select provider and model at runtime; default to Ollama `gemma3:27b`.
  - Ensure idempotency and avoid churn (don’t rename if a file already has a faithful name).
  - Update Markdown references to renamed files (standard and Obsidian wiki links) with safety.
  - Provide dry-run, collision handling, and a mapping report.
  - Offer a minimal PySide6 GUI for batch operations.

- Non‑Goals (v0.1)
  - Bulk processing across nested repositories or remote storages.
  - Non-image assets (video, PDF) — out of scope initially.
  - Complex image editing/redaction.
  - Multi-language UI; we assume English slugs for filenames.

## 3. Personas
- Power user (CLI): Works in a notes/code repo, wants batch renaming with logs and repeatability.
- Knowledge worker (GUI): Uses a simple desktop window to pick a folder and run safe rename.
- Integrator (API/SDK): Wants to extend to new providers or add custom naming rules.

## 4. User Stories

### 4.1 Provider & Model Selection
- As a user, I can choose the model provider (OpenAI or Ollama) and visual model to use.
  - Acceptance:
    - Default is `--provider ollama --model gemma3:27b`.
    - Configurable via CLI flags, env vars, or a config file.

### 4.2 Single File Renaming
- As a user, I can point to a single image and get a content-based new filename.
  - Acceptance:
    - The name follows the naming rubric (section 6) and keeps file extension.
    - If already faithful, no rename occurs (idempotent).

### 4.3 Folder Renaming (Flat)
- As a user, I can process all supported images in a folder (non-recursive by default).
  - Acceptance:
    - Only supported image types are processed.
    - Optional `--recursive` to walk subdirectories (off by default).

### 4.4 Dry Run
- As a user, I can preview the proposed renames without touching the filesystem.
  - Acceptance:
    - Emits a table of old -> new names and a summary (unchanged, proposed, conflicts).

### 4.5 Collision Handling
- As a user, I can avoid conflicts when a proposed name already exists.
  - Acceptance:
    - The tool appends numeric suffixes (`-2`, `-3`, …) before the extension.
    - Idempotent: If the destination equals current name, do nothing.

### 4.6 Reference Updates (Markdown)
- As a user, I want Markdown references updated when files are renamed.
  - Acceptance:
    - Supports standard Markdown images/links and Obsidian wiki links (with transclusions and aliases).
    - Preserves alt text and aliases; only updates the target path/basename.
    - A report lists which Markdown files were updated.

### 4.7 Error Handling
- As a user, I want clear error messages when vision fails.
  - Acceptance:
    - Show user-friendly error and exit cleanly
    - No need for fallback naming schemes

### 4.8 Simple Output
- As a user, I want clear output showing what happened.
  - Acceptance:
    - Rich-rendered panels/tables in CLI
    - Simple summary of changes made

## 5. Functional Requirements

### 5.1 Supported Formats
- Input: png, jpg/jpeg, webp, gif (static), bmp, tif/tiff, heic (best-effort via pillow if feasible).
- Output: Same extension preserved; only the basename changes.

### 5.2 Provider Abstraction
- Use Mojentic as the LLM/agent abstraction.
- Providers: `ollama`, `openai`.
- Defaults: `ollama` + `gemma3:27b`.
- Config via:
  - CLI: `--provider`, `--model`
  - Env: `LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`

### 5.3 Vision Analysis Contract
- Use Mojentic's LLMBroker with structured Pydantic output
- Return `ProposedName` with stem and extension
- No need for complex confidence scores or failure reasons - simple errors are fine

### 5.4 Naming Rubric (from example_prompt.md)
- Slug format: lowercase, hyphens
- Baseline structure: `<primary-subject>--<specific-detail-or-context>.<ext>`
- Aim for ~5–8 words; prefer specificity; include discriminators (chart type, version, vendor, OCR key term) when useful.
- Max length target: 80 chars; truncate at word boundaries.
- Sensitive info: avoid unless plainly visible; generalize if needed.
- Idempotency rules:
  - Do not rename if current name already matches intended name.
  - Do not rename if current name is already a faithful description.
  - Avoid oscillation: once vision-based, don’t thrash names without strong reason.

### 5.5 Collisions and Stability
- If candidate name exists, append `-2`, `-3`, etc. before extension.
- Maintain a session map to avoid intra-run collisions.

### 5.6 Markdown Reference Updates
- Targets: `*.md` files in the working directory (configurable root).
- Syntaxes to handle:
  - Standard Markdown image: `![](/path/name.png)` and links `[text](/path/name.png)`
  - Obsidian wiki links: `[[name.png]]`, `![[name.png]]`, aliases `[[name.png|Alt]]`
- Preserve alt/alias text; only update filename/path portion.
- Report lists files updated and replacement counts per file.

### 5.7 CLI Interface (Typer)
- Commands:
  - `image-namer file IMAGE [--provider] [--model] [--dry-run/--apply] [--update-refs] [--refs-root]`
  - `image-namer folder DIR [--provider] [--model] [--dry-run/--apply] [--update-refs] [--refs-root] [--recursive]`
  - `image-namer generate IMAGE` (legacy, simple proposal only)
- Options:
  - `--provider [ollama|openai]` (default: `ollama`)
  - `--model TEXT` (default: `gemma3:27b`)
  - `--dry-run / --apply` (default: dry-run)
  - `--update-refs / --no-update-refs` (default: false)
  - `--refs-root PATH` (default: current working dir)
  - `--recursive` (folders only)

### 5.8 Configuration Precedence
1) CLI flags
2) Environment variables
3) Tool defaults

### 5.9 Simple Output
- Rich panels and tables for human-readable output
- Summary of actions taken
- Clear error messages

### 5.10 Errors & Edge Cases
- Unsupported format → skip with warning
- LLM/vision errors → show clear error and exit
- Write permission denied → show error and exit (single file) or skip and continue (batch)
- Path normalization across OS, preserve case-insensitivity on macOS where relevant

### 5.11 Cache of Vision Results (Repository-local)
- Purpose: Avoid repeated, slow LLM/vision calls by caching deterministic inputs and outputs per repo.
- Location: A hidden folder named `.image_namer/` at the repository root (i.e., the current working directory by default).
- Substructure:
  - `.image_namer/`
    - `version`: text file containing cache schema version (e.g., `1`)
    - `cache/`
      - `analysis/` — one JSON per image content hash and model config
      - `names/` — one JSON per image content hash and model config (final naming plan)
      - `refs/` — optional, per-run reference update summaries indexed by run id
    - `runs/` — per-run manifests for auditing and reporting
      - `<timestamp>--<short-run-id>.json` — serialized `RunReport`
    - `index.json` — a light-weight map for quick lookups (hash -> files)
- Cache keys (fingerprints):
  - `content_sha256` of the image bytes
  - `provider` (e.g., `ollama` | `openai`)
  - `model` (e.g., `gemma3:27b`)
  - `rubric_version` (bump if naming rules materially change)
  - Optional: `endpoint`, provider-specific parameters that affect output
  - Composite cache key example: `<sha256>__<provider>__<model>__v<rubric>`
- Files:
  - `analysis/<key>.json` — stores the `ImageAnalysis` payload and metadata:
    - `{ key, content_sha256, provider, model, rubric_version, created_at, confidence, primary_subject, specific_detail, key_terms, fail_reason }`
  - `names/<key>.json` — stores the naming decision (proposed basename and rationale):
    - `{ key, proposed_basename, reason, confidence, rubric_version }`
  - `runs/<timestamp>--<id>.json` — stores a `RunReport` for that invocation.
  - `index.json` — maps `content_sha256` and known file paths to last-seen keys and run ids to speed up lookups.
- Read/Write policy:
  - On processing an image, compute `content_sha256` and form the composite key.
  - If `analysis/<key>.json` exists, reuse it; otherwise call the model and write it.
  - If `names/<key>.json` exists and rubric version matches, reuse the naming plan; otherwise recompute from analysis and write.
  - If the provider or model differs, treat as a new key; cache entries coexist.
- Invalidation:
  - Changing the image bytes → new `content_sha256` → naturally bypasses cache.
  - Bump `rubric_version` when naming rules change to avoid stale names.
  - Periodic pruning of orphaned entries is optional and non-blocking.
- Privacy & portability:
  - Cache is local to the repo, not uploaded.
  - JSON entries avoid embedding full image bytes; only hashes and minimal metadata.

### 5.12 Markdown Reference Root
- Default `refs_root` is `.` (current working directory)
- Users can override via `--refs-root`
- Tool only scans/updates files under this root

## 6. Data Model (Pydantic)
- `ProposedName`: stem, extension (already exists)
- `NameAssessment`: suitable (bool) - for idempotency checking (already exists)
- Future needs can add models as required

## 7. Algorithms & Flow
1) Validate input file(s)
2) For each image:
   - Check if supported format
   - Call LLM via Mojentic → get `ProposedName`
   - Check idempotency (current stem == proposed stem?)
   - Resolve collisions if needed (append -2, -3, etc.)
3) If `dry_run` → show what would happen and stop
4) If `--apply` → rename files
5) If `update_refs` → scan and update Markdown files
6) Show summary of what happened

## 8. Non‑Functional Requirements
- Performance: Good enough for typical personal use (dozens of files)
- Reliability: Dry-run by default, atomic renames
- Security/Privacy: Local provider default (Ollama), don't log image contents
- Maintainability: Simple code, well-tested, type-safe

## 9. Testing Strategy
- Co-located `*_spec.py` tests alongside implementation
- Use `pytest`, `pytest-mock` fixtures
- Test: collision resolution, idempotency, provider selection, dry-run vs apply
- Keep complexity low

## 10. Milestones
- M1 — ✅ Single-file rename with Ollama default (dry-run + apply)
- M2 — Folder processing (flat and recursive)
- M3 — Markdown reference updates (scan and patch)
- M4 — Cache implementation for performance
- M5 — Polish and release 0.1.0

## 11. What We're NOT Building
- GUI (PySide6) - CLI is sufficient
- Complex confidence scoring - simple pass/fail is fine
- Configurable rubric - consistency is better
- Interactive prompts - standard CLI patterns work
- Multiple output formats (JSON reports, etc.) - Rich output is enough
- `--endpoint`, `--api-key` flags - env vars work fine
- Fallback naming schemes - just error clearly
