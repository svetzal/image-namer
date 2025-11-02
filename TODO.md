Done:

- ✅ create a CLI command called `generate` that simply proposes a new filename for a given image file
- ✅ add a tiny `sha256_file(path: Path) -> str` helper in `src/utils/fs.py` with a co-located `_spec.py`
- ✅ scaffold cache layout creator `ensure_cache_layout(repo_root: Path)` that makes `.image_namer/{cache/{analysis,names,refs},runs}` and writes `version` if missing
- ✅ introduce `RUBRIC_VERSION = 1` constant (single source of truth) referenced by cache key logic (no key gen yet)
 
Pending:

- [ ] Implement `image-namer file` CLI subcommand (single-file rename) with `--dry-run/--apply`.
  - Validates supported image types; provider/model flags (default: ollama + gemma3:27b).
  - Calls vision naming, enforces idempotency, resolves collisions, and when `--apply` performs `Path.rename`.
  - Rich output panel/table showing source, proposed, final (post-collision), mode, and confidence when available.
  - Specs: happy path, unsupported type, invalid provider, idempotent no-op, collision suffixing.

- [ ] Add minimal collision resolver utility in `src/utils/fs.py`.
  - `next_available_name(dir: Path, stem: str, ext: str) -> str` using `-2`, `-3`, ... suffixes.
  - Specs: existing names 1..N, case-insensitivity on macOS.

- [ ] Basic idempotency check.
  - Heuristic: if current stem already equals proposed stem → treat as unchanged.
  - Leave full semantic check via LLM for a later milestone; cover with specs.

- [ ] Wire `--update-refs/--no-update-refs` and `--refs-root` flags for `file`.
  - Implement as a no-op placeholder that logs intention; add plumbing and specs.
  - Do not scan/modify Markdown yet.

- [ ] Align env vars for provider/model names.
  - Accept `IMGN_PROVIDER`/`IMGN_MODEL` in addition to existing `LLM_*` for backward compatibility.
  - Update README examples; add a spec asserting precedence shape (flags > env > defaults).

Deferred, don't do these yet:

- [ ] Full Markdown reference updater that patches `*.md` links/wiki links and reports replacements.
- [ ] JSON `--report` file and repo-local cache read/write paths.
- [ ] `image-namer folder` subcommand (flat by default) with `--recursive`, `--include/--exclude`.
- [ ] OpenAI provider polish and endpoint configuration.
