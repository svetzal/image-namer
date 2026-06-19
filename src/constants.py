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

SUPPORTED_PROVIDERS: Final[tuple[str, ...]] = ("ollama", "openai")
DEFAULT_MODELS: Final[dict[str, str]] = {"ollama": "gemma3:27b", "openai": "gpt-4o"}

LLM_OPERATIONAL_ERRORS: Final[tuple[type[Exception], ...]] = (
    OSError, ConnectionError, TimeoutError
)

FILESYSTEM_IO_ERRORS: Final[tuple[type[Exception], ...]] = (OSError, UnicodeError)
