"""Background worker for LLM-based image renaming.

Processes images in a background thread to keep UI responsive.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from operations.models import FolderStatistics, ImageAnalysis, ProcessingResult, RenameStatus
from operations.ports import AnalysisCachePort, ImageAnalyzerPort
from operations.process_folder import compute_statistics
from operations.process_image import process_single_image
from ui.models.ui_models import ItemStatus, RenameItem
from ui.worker_logic import apply_processing_result, mark_manually_edited


class _SignalProgressCallback:
    """Emits Qt signals during analysis cache-hit/miss events.

    Implements the ProgressCallback protocol structurally (duck typing).
    """

    def __init__(self, worker: "RenameWorker", item_index: int, item: RenameItem) -> None:
        self._worker = worker
        self._i = item_index
        self._item = item

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        """Emit cache-hit signal."""
        self._worker.item_status_changed.emit(
            self._i, "cache_hit", f"Analysis cached for {self._item.source_name}"
        )

    def on_cache_miss(self, path: Path) -> None:
        """Emit generating signal when LLM call is needed."""
        self._worker.item_status_changed.emit(
            self._i, "generating", f"Analyzing {self._item.source_name} (calling LLM)..."
        )

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        """No additional signal needed after analysis; handled by item_processed."""


class RenameWorker(QThread):
    """Background worker for LLM processing with detailed progress signals.

    Processes a batch of images, emitting signals for real-time UI updates.
    Delegates all business logic to process_single_image from the operations layer.
    """

    # Signals for fine-grained UI updates
    progress_updated = Signal(int, int)  # current, total
    item_status_changed = Signal(int, str, str)  # row_index, status, detail_message
    item_processed = Signal(int, RenameItem)  # row_index, result
    finished = Signal(object)  # summary stats (FolderStatistics)
    error_occurred = Signal(int, str)  # row_index, error_message

    def __init__(
        self,
        items: list[RenameItem],
        analyzer: ImageAnalyzerPort,
        cache: AnalysisCachePort,
    ):
        """Initialize worker.

        Args:
            items: List of RenameItem objects to process.
            analyzer: Image analyzer port for LLM-based analysis.
            cache: Analysis cache port for loading/saving results.
        """
        super().__init__()
        self.items = items
        self._analyzer = analyzer
        self._cache = cache
        self._stop_requested = False

    def run(self) -> None:
        """Process items, emitting signals for real-time UI updates."""
        planned_names: set[str] = set()
        results: list[ProcessingResult] = []

        for i, item in enumerate(self.items):
            if self._stop_requested:
                break

            if item.manually_edited:
                mark_manually_edited(item)
                synth = ProcessingResult(
                    source=item.source_name,
                    proposed=item.final_name,
                    final=item.final_name,
                    status=RenameStatus.RENAMED,
                    path=item.path,
                )
                results.append(synth)
                self.item_processed.emit(i, item)
                self.progress_updated.emit(i + 1, len(self.items))
                continue

            self.item_status_changed.emit(i, "assessing", f"Analyzing {item.source_name}...")

            progress_cb = _SignalProgressCallback(self, i, item)
            result = process_single_image(
                item.path,
                self._analyzer,
                self._cache,
                planned_names,
                progress_cb,
            )

            apply_processing_result(item, result)
            results.append(result)

            if item.status == ItemStatus.ERROR:
                self.error_occurred.emit(i, "Error during analysis")

            self.item_processed.emit(i, item)
            self.progress_updated.emit(i + 1, len(self.items))

        stats: FolderStatistics = compute_statistics(results)
        stats.cached = sum(1 for r in results if r.cached)
        self.finished.emit(stats)

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._stop_requested = True
