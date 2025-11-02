# Image Namer - Development Log

**Status**: Version 1.0.0 Released 🎉

All planned features for v1.0.0 have been completed and tested.

## Completed Features (M1-M5)

- ✅ create a CLI command called `generate` that simply proposes a new filename for a given image file
- ✅ add a tiny `sha256_file(path: Path) -> str` helper in `src/utils/fs.py` with a co-located `_spec.py`
- ✅ scaffold cache layout creator `ensure_cache_layout(repo_root: Path)` that makes `.image_namer/{cache/{analysis,names,refs},runs}` and writes `version` if missing
- ✅ introduce `RUBRIC_VERSION = 1` constant (single source of truth) referenced by cache key logic (no key gen yet)
- ✅ Implement `image-namer file` CLI subcommand (single-file rename) with `--dry-run/--apply`
  - Validates supported image types; provider/model flags (default: ollama + gemma3:27b)
  - Calls vision naming, enforces idempotency, resolves collisions, and when `--apply` performs `Path.rename`
  - Rich output panel showing source, proposed, final (post-collision), mode
  - Specs: happy path, unsupported type, invalid provider, idempotent no-op, collision suffixing
- ✅ Add minimal collision resolver utility in `src/utils/fs.py`
  - `next_available_name(dir: Path, stem: str, ext: str) -> str` using `-2`, `-3`, ... suffixes
  - Specs: existing names 1..N, case-insensitivity on macOS (next_available_name_spec.py)
- ✅ Basic idempotency check
  - Heuristic: if current stem already equals proposed stem → treat as unchanged (main.py:103-107)
  - Covered with spec: should_be_idempotent_when_stem_matches
- ✅ Wire `--update-refs/--no-update-refs` and `--refs-root` flags for `file`
  - Implemented as a no-op placeholder that logs intention (main.py:131-134)
  - Has spec: should_log_placeholder_when_update_refs_flag_used (main_refs_spec.py)
- ✅ Align env vars for provider/model names
  - Uses `LLM_PROVIDER`/`LLM_MODEL` exclusively (removed confusing `IMGN_*` names)
  - README examples updated
  - Has spec asserting precedence: should_follow_flag_env_default_precedence (main_file_spec.py)

- ✅ `image-namer folder` command for batch processing
  - Processes all images in a directory (flat by default)
  - `--recursive` flag to walk subdirectories
  - Shows summary table of all renames with statistics
  - Reuses collision resolver and idempotency logic from `file` command
  - Tracks planned renames to avoid collisions between multiple files

- ✅ Markdown reference updater
  - Scan `*.md` files under `--refs-root` when `--update-refs` is used
  - Update standard Markdown: `![alt](path)` and `[text](path)`
  - Update Obsidian wiki links: `[[name.png]]`, `![[name.png]]`, `[[name.png|alias]]`
  - Preserve alt text and aliases, only update filename
  - Report which files were updated and how many replacements
  - Implementation: operations/find_references.py and operations/update_references.py
  - Comprehensive test coverage (32 tests across both operations)
  - Integrated into both `file` and `folder` commands

- ✅ Cache implementation
  - Store LLM results by image hash in `.image_namer/cache/names/`
  - Key format: `{sha256}__{provider}__{model}__v{rubric_version}.json`
  - Avoid re-analyzing unchanged images with same provider/model
  - Simple JSON files per cache entry using pydantic models
  - Integrated into both `file` and `folder` commands
  - Comprehensive test coverage (14 tests in cache_spec.py)
  - Automatically invalidates cache when image, provider, model, or rubric version changes

- ✅ Pre-flight suitability assessment (fix unnecessary rename attempts)
  - **Problem**: Files with already-suitable names were being processed through rename logic
    - Example: `pycharm-todo-list-implementation.png` → proposed same name → collision with `-2` suffix
    - Cache stored proposed names but not suitability assessments
    - Second runs still called LLM even though current names were already good
  - **Solution**: Added assessment step before name generation (per SPEC.md §5.4, §5.11)
    - Call `assess_name()` operation first to check if current filename is suitable
    - Skip name generation entirely if current name passes rubric and matches content
    - Cache both assessments AND proposals separately in `.image_namer/cache/`
    - Assessment cache: `.image_namer/cache/analysis/{key}.json` (stores `NameAssessment`)
    - Proposal cache: `.image_namer/cache/names/{key}.json` (stores `ProposedName`)
  - **Implementation completed**:
    - ✅ Created cache operations for assessments (`load_assessment_from_cache`, `save_assessment_to_cache`)
    - ✅ Modified `_process_single_image()` to assess current filename first
    - ✅ Only calls `generate_name()` if assessment returns `suitable: false`
    - ✅ Updated `file` command to follow same pattern
    - ✅ Added 15 comprehensive tests for assessment caching
    - ✅ Added 2 integration tests for skip logic (main_assessment_spec.py)
    - ✅ "unchanged" status now means "already suitable" (not just "stem matches")
  - **Outcome achieved**:
    - Second run with `--apply` shows all files as "unchanged" when names are already suitable
    - No collision warnings for files that don't need renaming
    - Fewer LLM calls overall (assessment before generation)
    - Total test coverage: 94 tests (29 cache tests, 2 assessment integration tests)

---

## M5 - Polish and Release 1.0.0 ✅ COMPLETE

**All tasks completed:**

- ✅ Updated README.md to document all current capabilities
  - ✅ Added `folder` command with `--recursive` flag examples
  - ✅ Documented caching behavior (`.image_namer/` directory, cache keys, invalidation)
  - ✅ Documented markdown reference updates (`--update-refs`, `--refs-root`)
  - ✅ Added performance notes (caching reduces LLM calls)
  - ✅ Updated feature checklist to show M1-M5 complete

- ✅ Verified error handling completeness (SPEC §5.10)
  - ✅ Unsupported format handling (via `_validate_file_type`)
  - ✅ LLM/vision errors (handled with try/except blocks)
  - ✅ Write permission errors (file/folder commands handle per-file errors)
  - ✅ Path normalization (handled in URL decoding logic)
  - ✅ OPENAI_API_KEY validation (moved to gateway creation for test compatibility)

- ✅ Fixed critical bugs discovered during CI testing
  - ✅ ANSI color code handling in test assertions (added `_strip_ansi()` helper)
  - ✅ Non-deterministic file processing order (added sorting to `_collect_image_files()`)
  - ✅ OPENAI_API_KEY environment variable handling (moved check to gateway creation)

- ✅ Comprehensive CHANGELOG.md created for v1.0.0
- ✅ Version bumped to 1.0.0 in pyproject.toml
- ✅ All 94 tests passing with 88% code coverage
- ✅ SPEC.md updated to reflect completion status

**Note on `generate` command:**
- Kept for backward compatibility (no breaking changes)
- `file --dry-run` provides equivalent functionality with better consistency
- May deprecate in future major version

---

## Future Considerations (Post-1.0.0)

These items are not planned for immediate implementation but could be considered for future versions:

- GUI interface (PySide6) - deferred, CLI-first approach is working well
- Per-run audit reports (`runs/` directory) - current output is sufficient
- Cache index optimization - current performance is acceptable
- Video/PDF support - scope creep, images are the focus
- Interactive prompts - standard CLI patterns work well
- Multiple output formats (JSON, etc.) - Rich output is sufficient
