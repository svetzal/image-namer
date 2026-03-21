"""Project-wide constants for image-namer.

Keep constants in a single place to avoid duplication and drift.
"""

from typing import Final

# Single source of truth for rubric/cache version. Increment when cache schema changes.
RUBRIC_VERSION: int = 1

SUPPORTED_EXTENSIONS: Final[set[str]] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}
