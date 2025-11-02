Done:

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

Next Up:

- [ ] Markdown reference updater
  - Scan `*.md` files under `--refs-root` when `--update-refs` is used
  - Update standard Markdown: `![alt](path)` and `[text](path)`
  - Update Obsidian wiki links: `[[name.png]]`, `![[name.png]]`, `[[name.png|alias]]`
  - Preserve alt text and aliases, only update filename
  - Report which files were updated and how many replacements

- [ ] Cache implementation
  - Store LLM results by image hash in `.image_namer/cache/`
  - Key: `sha256(image)__provider__model__rubric_version`
  - Avoid re-analyzing unchanged images
  - Simple JSON files per cache entry
