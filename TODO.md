Done:

- ✅ create a CLI command called `generate` that simply proposes a new filename for a given image file
- ✅ add a tiny `sha256_file(path: Path) -> str` helper in `src/utils/fs.py` with a co-located `_spec.py`
- ✅ scaffold cache layout creator `ensure_cache_layout(repo_root: Path)` that makes `.image_namer/{cache/{analysis,names,refs},runs}` and writes `version` if missing
- ✅ introduce `RUBRIC_VERSION = 1` constant (single source of truth) referenced by cache key logic (no key gen yet)
 
Pending:


Deferred, don't do these yet:

- [ ] minimal `ProviderConfig` pydantic model with defaults and a `_spec.py` to assert env/flag precedence shape (behavior TBD)
- [ ] add `--dry-run / --apply` flags to CLI (wire to no-op placeholder)
- [ ] expose `--provider` and `--model` flags in the CLI with defaults `ollama` and `gemma3:27b` (no behavior change yet)
