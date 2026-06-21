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

# I/O Error-Handling Policy
# Every I/O boundary must follow ONE of:
#   (a) catch the matching error tuple, log-and-recover (return a safe default / skip)
#   (b) catch the matching error tuple, log-and-exit cleanly at the CLI/GUI boundary
# Never crash with an unhandled traceback. Never `pass` silently.
#
# Use FILESYSTEM_IO_ERRORS for filesystem operations (sha256, mkdir, read, write).
# Use LLM_OPERATIONAL_ERRORS only for genuine LLM/network failures — not for
# cache write failures (those are filesystem I/O, not LLM errors).

LLM_OPERATIONAL_ERRORS: Final[tuple[type[Exception], ...]] = (
    OSError, ConnectionError, TimeoutError
)

FILESYSTEM_IO_ERRORS: Final[tuple[type[Exception], ...]] = (OSError, UnicodeError)
