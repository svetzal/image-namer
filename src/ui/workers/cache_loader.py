"""Background worker for loading cached data without LLM calls.

Proactively loads cache to give user early feedback on what's already been processed.
"""

from PySide6.QtCore import QThread, Signal

from operations.ports import AnalysisCachePort
from operations.process_image import build_processing_result
from ui.models.ui_models import RenameItem
from ui.worker_logic import apply_cached_result


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
        cache: AnalysisCachePort,
    ):
        """Initialize cache loader worker.

        Args:
            items: List of RenameItem objects to check cache for.
            cache: Analysis cache port for loading cached results.
        """
        super().__init__()
        self.items = items
        self._cache = cache
        self._stop_requested = False

    def run(self) -> None:
        """Load cached data for each item."""
        cached_count = 0
        planned_names: set[str] = set()

        for i, item in enumerate(self.items):
            if self._stop_requested:
                break

            analysis = self._cache.load(item.path, item.source_name)

            if analysis:
                result = build_processing_result(item.path, analysis, True, planned_names)
                apply_cached_result(item, result)
                cached_count += 1
                self.item_cache_loaded.emit(i, item)

        self.finished.emit(cached_count, len(self.items))

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._stop_requested = True
