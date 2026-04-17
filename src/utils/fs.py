"""Filesystem utilities for image-namer.

Contains small, focused helpers with low complexity and complete type hints.
"""


import hashlib
import sys
from pathlib import Path
from typing import Final

from constants import RUBRIC_VERSION, SUPPORTED_EXTENSIONS

# Top-level cache directory name (dot folder in repo root)
CACHE_ROOT_NAME: Final[str] = ".image_namer"


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file's contents.

    Streams the file in chunks to support large files without high memory usage.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_cache_layout(repo_root: Path) -> Path:
    """Ensure the on-disk cache layout exists below the given repository root.

    Creates the following structure if missing:

    - .image_namer/
      - cache/
        - analysis/
        - names/
        - refs/
      - runs/
      - version (file; created if missing; contains the current RUBRIC_VERSION)

    The operation is idempotent: calling it multiple times is safe.
    """
    cache_root = repo_root / CACHE_ROOT_NAME
    (cache_root / "cache" / "analysis").mkdir(parents=True, exist_ok=True)
    (cache_root / "cache" / "names").mkdir(parents=True, exist_ok=True)
    (cache_root / "cache" / "refs").mkdir(parents=True, exist_ok=True)
    (cache_root / "cache" / "unified").mkdir(parents=True, exist_ok=True)
    (cache_root / "runs").mkdir(parents=True, exist_ok=True)

    version_file = cache_root / "version"
    if not version_file.exists():
        version_file.write_text(f"{RUBRIC_VERSION}\n", encoding="utf-8")

    return cache_root


def next_available_name(
    dir: Path,
    stem: str,
    ext: str,
    case_insensitive: bool | None = None,
    planned_names: set[str] | frozenset[str] = frozenset(),
) -> str:
    """Return a non-colliding filename for the given directory.

    Uses numeric suffixes ``-2``, ``-3``, ... appended to the provided ``stem``
    to avoid collisions with existing files. The first candidate is ``stem``
    itself, then ``stem-2``, ``stem-3``, etc.

    On macOS (Darwin), the check is case-insensitive to align with the default
    case-insensitive filesystem behavior.
    """
    # Normalize extension to include leading dot if provided and not empty
    if not ext:
        extension = ""
    else:
        extension = ext if ext.startswith(".") else f".{ext}"

    _case_insensitive = sys.platform == "darwin" if case_insensitive is None else case_insensitive

    # Normalize list of existing filenames in the directory
    try:
        existing = {p.name for p in dir.iterdir()}
    except FileNotFoundError:
        existing = set()

    def normalize(name: str) -> str:
        return name.lower() if _case_insensitive else name

    existing_norm = {normalize(name) for name in existing}
    planned_norm = {normalize(name) for name in planned_names}

    def candidate(n: int) -> str:
        s = stem if n == 1 else f"{stem}-{n}"
        return f"{s}{extension}"

    n = 1
    while True:
        name = candidate(n)
        if normalize(name) not in existing_norm and normalize(name) not in planned_norm:
            return name
        n += 1


def collect_image_files(path: Path, recursive: bool) -> list[Path]:
    if recursive:
        files = [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    else:
        files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(files)
