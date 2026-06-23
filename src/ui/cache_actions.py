"""Pure orchestration functions for UI cache-clear actions.

These functions are Qt-agnostic and testable without Qt.
"""

from pathlib import Path

from constants import FILESYSTEM_IO_ERRORS
from operations.ports import CacheClearerPort
from ui.models.ui_models import CacheClearResult, CacheClearTarget


def resolve_cache_target(folder: Path | None, clearer: CacheClearerPort) -> CacheClearTarget:
    """Compute the cache directory path and whether it currently exists.

    Args:
        folder: The folder loaded in the UI, or None to fall back to cwd.
        clearer: Port providing cache layout and existence checks.

    Returns:
        CacheClearTarget with cache_dir and exists fields populated.
    """
    cache_root = clearer.ensure_layout(folder if folder is not None else Path.cwd())
    cache_dir = cache_root / "cache"
    return CacheClearTarget(cache_dir=cache_dir, exists=clearer.cache_exists(cache_dir))


def clear_cache(cache_dir: Path, clearer: CacheClearerPort) -> CacheClearResult:
    """Delete and recreate the cache directory via the port.

    Args:
        cache_dir: The directory to clear.
        clearer: Port providing the clear operation.

    Returns:
        CacheClearResult with success=True on success, or success=False with error_message.
    """
    try:
        clearer.clear(cache_dir)
        return CacheClearResult(success=True)
    except FILESYSTEM_IO_ERRORS as e:
        return CacheClearResult(success=False, error_message=str(e))
