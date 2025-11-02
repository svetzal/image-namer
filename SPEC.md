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

### 4.7 Fallback When Vision Unavailable
- As a user, I want a safe fallback if vision is unavailable or decoding fails.
  - Acceptance:
    - Derives a name from nearest Markdown context with suffix `--context-derived`.
    - Never fabricates details not present in image.

### 4.8 Logs and Report
- As a user, I want a clear report mapping old -> new filenames and a list of updated references.
  - Acceptance:
    - Rich-rendered output in CLI; optional JSON report file.

### 4.9 GUI Batch Workflow (Minimal)
- As a user, I can pick a folder, choose provider/model, run dry-run, then apply changes.
  - Acceptance:
    - Same naming rules as CLI.
    - Progress and summary displayed; errors surfaced unobtrusively.

## 5. Functional Requirements

### 5.1 Supported Formats
- Input: png, jpg/jpeg, webp, gif (static), bmp, tif/tiff, heic (best-effort via pillow if feasible).
- Output: Same extension preserved; only the basename changes.

### 5.2 Provider Abstraction
- Use Mojentic as the LLM/agent abstraction.
- Providers: `ollama`, `openai`.
- Defaults: `ollama` + `gemma3:27b`.
- Config via:
  - CLI: `--provider`, `--model`, `--endpoint`, `--api-key` (where applicable).
  - Env: `IMGN_PROVIDER`, `IMGN_MODEL`, `IMGN_ENDPOINT`, `OPENAI_API_KEY`.

### 5.3 Vision Analysis Contract
- Given image bytes, return a structured `ImageAnalysis` object:
  - `primary_subject: str`
  - `specific_detail: str | None`
  - `key_terms: list[str]` (e.g., OCR words or notable entities)
  - `confidence: float` (0–1)
  - `fail_reason: str | None`

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
- Command: `image-namer` (entry point to be added later)
- Usage examples:
  - `image-namer file IMAGE [--provider ollama --model gemma3:27b] [--dry-run] [--update-refs --refs-root .]`
  - `image-namer folder DIR [--recursive] [--include "*.png,*.jpg"] [--exclude "*_thumb.*"] [--dry-run] [--update-refs]`
- Global options:
  - `--provider [ollama|openai]` (default: `ollama`)
  - `--model TEXT` (default: `gemma3:27b`)
  - `--endpoint URL` (optional)
  - `--api-key TEXT` (for OpenAI)
  - `--dry-run / --apply` (default dry-run true for safety on first run?)
  - `--update-refs / --no-update-refs` (default: true when inside a repo)
  - `--refs-root PATH` (default: current working dir)
  - `--report PATH` (write JSON report)
  - `--recursive` (folders)
  - `--include / --exclude` patterns (comma-separated)

### 5.8 GUI (PySide6) — Minimal v0.1
- Single-window app:
  - Folder chooser, provider select, model input
  - Dry-run button shows a table (old name, proposed name, reason, confidence)
  - Apply button executes renames and updates references
  - Status/progress with Rich-like styling or Qt widgets

### 5.9 Configuration Precedence
1) CLI flags
2) Environment variables
3) Config file (e.g., `.imagenamer.toml` future)
4) Tool defaults

### 5.10 Reports and Logging
- Rich tables in CLI for human-readable output.
- JSON report schema (see Data Models) written via `--report`.
- Summary counts: processed, unchanged, renamed, collisions, failed, references updated.

### 5.11 Errors & Edge Cases
- Unsupported format → skip with warning.
- Undecodable image → fallback behavior (section 4.7) or skip with reason.
- Write permission denied → record failure, continue batch.
- Reference update failures → partial success flagged in report.
- Path normalization across OS, preserve case-insensitivity on macOS where relevant.

### 5.12 Cache of Vision Results and Planning (Repository-local)
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

### 5.13 Repository Root Assumptions (Markdown References)
- Default working directory is assumed to be the root of the Markdown/code repository.
- By default, `refs_root` is `.` (the current working directory), and Markdown scanning occurs under this root.
- Users can override `refs_root` via CLI `--refs-root` and, later, via GUI controls.
- The tool does not traverse outside the chosen root when updating references.

## 6. Data Model (Pydantic)
- `ProviderConfig`: provider, model, endpoint, api_key
- `JobConfig`:
  - mode: `"file"|"folder"`
  - input_path: Path
  - recursive: bool
  - include_patterns: list[str]
  - exclude_patterns: list[str]
  - update_refs: bool
  - refs_root: Path
  - dry_run: bool
  - report_path: Path | None
  - provider: `ProviderConfig`
- `ImageAnalysis`: see 5.3
- `RenamePlan`:
  - src_path: Path
  - proposed_basename: str
  - reason: str
  - confidence: float
  - collision_resolved_basename: str | None
- `RenameResult`:
  - applied: bool
  - final_path: Path | None
  - error: str | None
- `ReferenceUpdate`:
  - file: Path
  - replacements: int
- `RunReport`:
  - plans: list[RenamePlan]
  - results: list[RenameResult]
  - references: list[ReferenceUpdate]
  - summary: dict[str, int]

## 7. Algorithms & Flow
1) Discover inputs (file or folder, filters, recursion).
2) For each image:
   - Decode/validate → if fail, fallback or skip.
   - Send to vision provider via Mojentic → get `ImageAnalysis`.
   - Build slug with rubric → candidate basename.
   - Check idempotency (is current faithful / matches intended?).
   - Resolve collisions in target directory.
   - Record `RenamePlan`.
3) If `dry_run` → render tables and stop.
4) Apply filesystem renames.
5) If `update_refs` → scan Markdown files under `refs_root` and patch targets.
6) Produce `RunReport` and optional JSON file.

## 8. Non‑Functional Requirements
- Performance: Reasonable for 100–1000 images per run; parallelize model calls optionally later.
- Reliability: No-destructive defaults (dry-run first). Atomic-ish renames where possible.
- Security/Privacy: Don’t log image contents; redact sensitive output. Local provider default (Ollama).
- Observability: Structured logs (json) toggle; human logs (Rich) by default.
- Maintainability: Low complexity functions; comprehensively tested with pytest; pydantic for types.

## 9. Testing Strategy
- Co-located `*_spec.py` tests alongside implementation.
- Classes/functions kept short with clear inputs/outputs.
- Use `pytest`, `pytest-mock` fixtures; no `unittest` directly.
- Suggested test groups:
  - Naming rubric and slugging rules (happy paths, truncation, sensitization).
  - Collision resolution.
  - Idempotency decisions (no-churn cases).
  - Reference updater on various Markdown syntaxes.
  - Dry-run vs apply behavior.
  - Provider selection and config precedence.
  - Fallback `--context-derived` behavior when vision absent.

## 10. Milestones
- M0 — Spec & scaffolding (this document, CLI skeleton, config types)
- M1 — Core CLI single-file rename with Ollama default (dry-run + apply)
- M2 — Folder processing, filters, recursive, collision handling, idempotency
- M3 — Markdown reference updates and reporting
- M4 — OpenAI provider support and configuration polish
- M5 — Minimal GUI (dry-run, apply)
- M6 — Hardening, tests coverage, and release 0.1.0

## 11. Open Questions
- HEIC/HEIF support: gated behind optional dependency?
- Default `--dry-run` true or false? We propose true for safety; confirm.
- JSON report schema versioning and future compatibility.

## 12. References
- example_prompt.md: Naming rubric, idempotency, references, audit.
- .junie/guidelines.md: Tech stack, testing/linting, release process.
