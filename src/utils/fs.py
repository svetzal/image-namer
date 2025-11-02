"""Filesystem utilities for image-namer.

Contains small, focused helpers with low complexity and complete type hints.
"""


import hashlib
import sys
from pathlib import Path
from typing import Final

from constants import RUBRIC_VERSION

# Top-level cache directory name (dot folder in repo root)
CACHE_ROOT_NAME: Final[str] = ".image_namer"


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file's contents.

    Args:
        path: Path to the file to hash. Must exist and be readable.

    Returns:
        Hexadecimal SHA-256 digest string (lowercase, 64 chars).
    """
    h = hashlib.sha256()
    # Stream file in chunks to support large files without high memory usage
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

    Args:
        repo_root: Root directory of the repository/workspace.

    Returns:
        Path to the cache root directory (repo_root / ".image_namer").
    """
    cache_root = repo_root / CACHE_ROOT_NAME
    (cache_root / "cache" / "analysis").mkdir(parents=True, exist_ok=True)
    (cache_root / "cache" / "names").mkdir(parents=True, exist_ok=True)
    (cache_root / "cache" / "refs").mkdir(parents=True, exist_ok=True)
    (cache_root / "runs").mkdir(parents=True, exist_ok=True)

    version_file = cache_root / "version"
    if not version_file.exists():
        version_file.write_text(f"{RUBRIC_VERSION}\n", encoding="utf-8")

    return cache_root


def next_available_name(dir: Path, stem: str, ext: str) -> str:
    """Return a non-colliding filename for the given directory.

    Uses numeric suffixes ``-2``, ``-3``, ... appended to the provided ``stem``
    to avoid collisions with existing files. The first candidate is ``stem``
    itself, then ``stem-2``, ``stem-3``, etc.

    On macOS (Darwin), the check is case-insensitive to align with the default
    case-insensitive filesystem behavior.

    Args:
        dir: Directory to check for name collisions.
        stem: Desired filename stem (without extension).
        ext: File extension, with or without a leading dot.

    Returns:
        A filename (stem + extension) that does not exist in ``dir``.
    """
    # Normalize extension to include leading dot if provided and not empty
    if not ext:
        extension = ""
    else:
        extension = ext if ext.startswith(".") else f".{ext}"

    # Normalize list of existing filenames in the directory
    try:
        existing = {p.name for p in dir.iterdir()}
    except FileNotFoundError:
        existing = set()

    def normalize(name: str) -> str:
        return name.lower() if sys.platform == "darwin" else name

    existing_norm = {normalize(name) for name in existing}

    def candidate(n: int) -> str:
        s = stem if n == 1 else f"{stem}-{n}"
        return f"{s}{extension}"

    n = 1
    while True:
        name = candidate(n)
        if normalize(name) not in existing_norm:
            return name
        n += 1
