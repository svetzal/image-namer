"""Processing coordinator that manages folder scanning, LLM analysis, and rename operations.

Owns all business-logic orchestration and worker lifecycle. Never touches widgets or dialogs;
emits signals and returns values so MainWindow can handle presentation.
"""

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from operations.adapters import FilesystemAnalysisCache
from operations.gateway_factory import MissingApiKeyError
from operations.pipeline_factory import build_analysis_pipeline
from ui.models.ui_models import AnalysisStats, BatchRenameResult, RenameItem, RenameResult, RenameStatus
from ui.rename_actions import perform_batch_rename, perform_rename_with_refs
from ui.workers.cache_loader import CacheLoaderWorker
from ui.workers.rename_worker import RenameWorker
from utils.fs import collect_image_files, ensure_cache_layout


class ProcessingCoordinator(QObject):
    """Orchestrates folder scanning, cache loading, LLM analysis, and file renaming.

    State owned: current_folder, rename_items, active workers.
    Callers interact via method calls and by connecting to signals.
    """

    folder_scanned: "Signal" = Signal(list)       # list[RenameItem]
    cache_item_loaded: "Signal" = Signal(int, object)   # row, RenameItem
    cache_loading_finished: "Signal" = Signal(int, int)   # cached_count, total_count
    analysis_progress: "Signal" = Signal(int, int)        # current, total
    item_status_changed: "Signal" = Signal(int, str, str)  # row, status, message
    item_updated: "Signal" = Signal(int, object)          # row, RenameItem
    analysis_finished: "Signal" = Signal(object)
    error_occurred: "Signal" = Signal(int, str)           # row (-1 = setup error), message

    def __init__(self, parent: "QObject | None" = None) -> None:
        """Initialize coordinator with empty state."""
        super().__init__(parent)
        self.current_folder: Path | None = None
        self.rename_items: list[RenameItem] = []
        self._worker: RenameWorker | None = None
        self._cache_loader: CacheLoaderWorker | None = None

    # ------------------------------------------------------------------
    # Folder scanning
    # ------------------------------------------------------------------

    def scan_folder(self, folder: Path, recursive: bool) -> None:
        """Scan folder for images and emit folder_scanned with resulting items.

        Emits folder_scanned with an empty list when no images are found.
        """
        image_files = collect_image_files(folder, recursive)

        if not image_files:
            self.folder_scanned.emit([])
            return

        self.current_folder = folder
        self.rename_items = [
            RenameItem(
                path=img_path,
                source_name=img_path.name,
                final_name=img_path.name,
                status=RenameStatus.QUEUED,
                status_message="Waiting in queue...",
            )
            for img_path in image_files
        ]
        self.folder_scanned.emit(self.rename_items)

    # ------------------------------------------------------------------
    # Cache loading
    # ------------------------------------------------------------------

    def start_cache_loader(self, provider: str, model: str) -> None:
        """Start background worker that pre-populates items from the analysis cache."""
        if not self.rename_items or not self.current_folder:
            return

        cache_root = ensure_cache_layout(self.current_folder)
        cache = FilesystemAnalysisCache(
            cache_root / "cache" / "unified", provider=provider, model=model
        )
        self._cache_loader = CacheLoaderWorker(
            items=self.rename_items,
            cache=cache,
            provider=provider,
            model=model,
        )
        self._cache_loader.item_cache_loaded.connect(self._on_cache_item_loaded)
        self._cache_loader.finished.connect(self._on_cache_loading_finished)
        self._cache_loader.start()

    def _on_cache_item_loaded(self, row: int, item: RenameItem) -> None:
        if row < len(self.rename_items):
            self.rename_items[row] = item
        self.cache_item_loaded.emit(row, item)

    def _on_cache_loading_finished(self, cached_count: int, total_count: int) -> None:
        self.cache_loading_finished.emit(cached_count, total_count)

    # ------------------------------------------------------------------
    # LLM analysis
    # ------------------------------------------------------------------

    def start_analysis(self, provider: str, model: str) -> None:
        """Start LLM analysis worker.

        Emits error_occurred(-1, msg) on setup failure so callers can revert UI state.
        """
        if not self.rename_items:
            return

        cache_root = ensure_cache_layout(
            self.current_folder if self.current_folder else Path.cwd()
        )

        try:
            pipeline = build_analysis_pipeline(provider, model, cache_root)
        except MissingApiKeyError as e:
            self.error_occurred.emit(-1, str(e))
            return
        except (OSError, ConnectionError, ValueError, RuntimeError) as e:
            self.error_occurred.emit(-1, str(e))
            return

        self._worker = RenameWorker(
            items=self.rename_items,
            analyzer=pipeline.analyzer,
            cache=pipeline.cache,
            provider=provider,
            model=model,
        )
        self._worker.progress_updated.connect(self._on_worker_progress)
        self._worker.item_status_changed.connect(self._on_worker_status_changed)
        self._worker.item_processed.connect(self._on_worker_item_processed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.start()

    def stop_analysis(self) -> None:
        """Request graceful stop of the running analysis worker."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()

    def _on_worker_progress(self, current: int, total: int) -> None:
        self.analysis_progress.emit(current, total)

    def _on_worker_status_changed(self, row: int, status: str, message: str) -> None:
        self.item_status_changed.emit(row, status, message)

    def _on_worker_item_processed(self, row: int, item: RenameItem) -> None:
        if row < len(self.rename_items):
            self.rename_items[row] = item
        self.item_updated.emit(row, item)

    def _on_worker_error(self, row: int, error_msg: str) -> None:
        self.error_occurred.emit(row, error_msg)

    def _on_worker_finished(self, stats: AnalysisStats) -> None:
        self.analysis_finished.emit(stats)

    # ------------------------------------------------------------------
    # Rename operations
    # ------------------------------------------------------------------

    def get_items_to_rename(self) -> list[RenameItem]:
        """Return items whose final_name differs from source_name and are ready/collision."""
        return [
            item for item in self.rename_items
            if item.status in (RenameStatus.READY, RenameStatus.COLLISION)
            and item.final_name != item.source_name
        ]

    def rename_single(
        self, row: int, update_refs: bool, recursive: bool
    ) -> RenameResult:
        """Rename the item at row and optionally update markdown references.

        Returns:
            RenameResult with success=True and references_updated on success.
            RenameResult with success=False and error_message="no_change" when names are identical.
            RenameResult with success=False and error_message set on failure.
        """
        if not self.rename_items or row < 0 or row >= len(self.rename_items):
            return RenameResult(success=False, error_message="Invalid selection")

        item = self.rename_items[row]
        old_path = item.path
        old_name = item.source_name
        new_name = item.final_name or item.source_name

        if old_name == new_name or old_path == old_path.parent / new_name:
            return RenameResult(success=False, error_message="no_change")

        try:
            refs_updated = perform_rename_with_refs(
                old_path, new_name, self.current_folder, update_refs, recursive
            )
            item.status = RenameStatus.COMPLETED
            item.status_message = "Successfully renamed"
            item.source_name = new_name
            item.path = old_path.parent / new_name
            return RenameResult(success=True, references_updated=refs_updated)
        except (OSError, PermissionError) as e:
            item.status = RenameStatus.ERROR
            item.status_message = f"Rename failed: {e}"
            item.error_message = str(e)
            return RenameResult(success=False, error_message=str(e))

    def rename_batch(self, update_refs: bool, recursive: bool) -> BatchRenameResult:
        """Rename all ready items in batch and return aggregate counts."""
        items_to_rename = self.get_items_to_rename()
        return perform_batch_rename(
            items_to_rename, self.current_folder, update_refs, recursive
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Stop all running workers for clean application shutdown."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            if not self._worker.wait(3000):
                self._worker.terminate()
                self._worker.wait()

        if self._cache_loader and self._cache_loader.isRunning():
            self._cache_loader.stop()
            if not self._cache_loader.wait(1000):
                self._cache_loader.terminate()
                self._cache_loader.wait()
