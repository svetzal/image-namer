"""Background worker for loading cached data without LLM calls.

Proactively loads cache to give user early feedback on what's already been processed.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from operations.cache import load_analysis_from_cache
from ui.models.ui_models import RenameItem, RenameStatus


class CacheLoaderWorker(QThread):
    """Background worker that loads cached data for images.

    Runs after folder scan to populate table with cached results without
    making LLM calls. This gives users immediate feedback on what's cached.
    """

    item_cache_loaded = Signal(int, RenameItem)  # row_index, item with cache data
    finished = Signal(int, int)  # cached_count, total_count

    def __init__(
        self,
        items: list[RenameItem],
        cache_root: Path,
        provider: str,
        model: str,
    ):
        """Initialize cache loader worker.

        Args:
            items: List of RenameItem objects to check cache for.
            cache_root: Path to cache directory (.image_namer).
            provider: LLM provider name (for cache keys).
            model: Model name (for cache keys).
        """
        super().__init__()
        self.items = items
        self.cache_root = cache_root
        self.provider = provider
        self.model = model
        self._stop_requested = False

    def run(self) -> None:
        """Load cached data for each item."""
        unified_cache_dir = self.cache_root / "cache" / "unified"
        cached_count = 0

        for i, item in enumerate(self.items):
            if self._stop_requested:
                break

            # Check if unified analysis is cached
            analysis = load_analysis_from_cache(
                unified_cache_dir, item.path, item.source_name, self.provider, self.model
            )

            if analysis:
                # Extract proposed name and reasoning from cached analysis
                proposed = analysis.proposed_name
                item.reasoning = analysis.reasoning  # Store LLM reasoning
                proposed_ext = proposed.extension if proposed.extension.startswith(".") else f".{proposed.extension}"
                if not proposed.extension:
                    proposed_ext = item.path.suffix

                proposed_filename = f"{proposed.stem}{proposed_ext}"
                item.proposed_name = proposed_filename

                # Handle based on current name suitability
                if analysis.current_name_suitable:
                    # Current name is suitable - only update if not manually edited
                    if not item.manually_edited:
                        item.final_name = item.source_name
                        item.update_status(RenameStatus.UNCHANGED, "Already suitable (cached)")
                    else:
                        item.update_status(RenameStatus.UNCHANGED, "Already suitable (filename locked by user)")
                else:
                    # Current name not suitable - use proposed name
                    if not item.manually_edited:
                        item.final_name = proposed_filename
                        item.update_status(RenameStatus.READY, "Ready (from cache)")
                    else:
                        item.update_status(RenameStatus.READY, "Ready (filename locked by user)")

                item.cached = True
                cached_count += 1
                self.item_cache_loaded.emit(i, item)

        self.finished.emit(cached_count, len(self.items))

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._stop_requested = True
