"""Background worker for LLM-based image renaming.

Processes images in a background thread to keep UI responsive.
"""

from pathlib import Path

from mojentic.llm import LLMBroker
from PySide6.QtCore import QThread, Signal

from operations.analyze_image import analyze_image
from operations.cache import (
    load_analysis_from_cache,
    save_analysis_to_cache,
)
from operations.models import ImageAnalysis, ProposedName
from operations.models import RenameStatus as OpsRenameStatus
from operations.process_image import normalize_extension, resolve_final_name
from ui.models.ui_models import RenameItem, RenameStatus


class RenameWorker(QThread):
    """Background worker for LLM processing with detailed progress signals.

    Processes a batch of images, emitting signals for real-time UI updates.
    Reuses all business logic from operations/ package.
    """

    # Signals for fine-grained UI updates
    progress_updated = Signal(int, int)  # current, total
    item_status_changed = Signal(int, str, str)  # row_index, status, detail_message
    item_processed = Signal(int, RenameItem)  # row_index, result
    finished = Signal(dict)  # summary stats
    error_occurred = Signal(int, str)  # row_index, error_message

    def __init__(
        self,
        items: list[RenameItem],
        llm: LLMBroker,
        cache_root: Path,
        provider: str,
        model: str,
    ):
        """Initialize worker.

        Args:
            items: List of RenameItem objects to process.
            llm: LLM broker for name generation.
            cache_root: Path to cache directory (.image_namer).
            provider: LLM provider name (for cache keys).
            model: Model name (for cache keys).
        """
        super().__init__()
        self.items = items
        self.llm = llm
        self.cache_root = cache_root
        self.provider = provider
        self.model = model
        self._stop_requested = False
        self._planned_names: set[str] = set()  # Track planned filenames to avoid collisions

    def _get_or_generate_analysis(
        self, item: RenameItem, i: int, unified_cache_dir: Path, stats: dict[str, int]
    ) -> ImageAnalysis:
        """Get analysis from cache or generate using LLM.

        Emits status signals before and after the operation so the UI can
        show real-time progress.

        Args:
            item: RenameItem to analyze.
            i: Item index for status updates.
            unified_cache_dir: Cache directory path.
            stats: Statistics dict to update.

        Returns:
            Analysis result from operations.analyze_image.
        """
        self.item_status_changed.emit(i, "assessing", f"Analyzing {item.source_name}...")

        analysis = load_analysis_from_cache(
            unified_cache_dir, item.path, item.source_name, self.provider, self.model
        )

        if analysis is None:
            self.item_status_changed.emit(i, "generating", f"Analyzing {item.source_name} (calling LLM)...")
            analysis = analyze_image(item.path, item.source_name, llm=self.llm)
            save_analysis_to_cache(
                unified_cache_dir, item.path, item.source_name, self.provider, self.model, analysis
            )
        else:
            self.item_status_changed.emit(i, "cache_hit", f"✓ Analysis cached for {item.source_name}")
            stats["cached"] += 1
            item.cached = True

        return analysis

    def _handle_suitable_name(self, item: RenameItem, i: int, stats: dict[str, int]) -> None:
        """Handle case where current name is already suitable.

        Args:
            item: RenameItem with suitable current name.
            i: Item index for signals.
            stats: Statistics dict to update.
        """
        if not item.manually_edited:
            item.final_name = item.source_name
            item.update_status(RenameStatus.UNCHANGED, "Current name is already suitable")
        else:
            item.update_status(RenameStatus.UNCHANGED, "Current name suitable (filename locked by user)")

        stats["unchanged"] += 1
        self.item_processed.emit(i, item)
        self.progress_updated.emit(i + 1, len(self.items))

    def _determine_final_name(
        self,
        item: RenameItem,
        proposed: ProposedName,
        proposed_filename: str,
        stats: dict[str, int],
    ) -> None:
        """Determine final name considering manual edits, idempotency, and collisions.

        Delegates to the shared ``resolve_final_name`` function for idempotency
        and collision logic, mapping operations status values to UI status values.

        Args:
            item: RenameItem to process.
            proposed: Proposed filename components from the LLM.
            proposed_filename: Full proposed filename string (for display).
            stats: Statistics dict to update.
        """
        if item.manually_edited:
            item.update_status(RenameStatus.READY, "Ready (filename locked by user)")
            stats["renamed"] += 1
            return

        _, final_filename, ops_status = resolve_final_name(
            item.path, proposed, self._planned_names
        )

        if ops_status == OpsRenameStatus.UNCHANGED:
            item.update_status(RenameStatus.UNCHANGED, "Proposed name matches current")
            item.final_name = item.source_name
            stats["unchanged"] += 1
        elif ops_status == OpsRenameStatus.COLLISION:
            item.update_status(RenameStatus.COLLISION, f"Collision resolved: {final_filename}")
            item.final_name = final_filename
            stats["renamed"] += 1
        else:
            item.update_status(RenameStatus.READY, "Ready to rename")
            item.final_name = final_filename
            stats["renamed"] += 1

    def run(self) -> None:
        """Process items, emitting signals for real-time UI updates."""
        stats = {"renamed": 0, "unchanged": 0, "cached": 0, "errors": 0}
        unified_cache_dir = self.cache_root / "cache" / "unified"

        for i, item in enumerate(self.items):
            if self._stop_requested:
                break

            try:
                analysis = self._get_or_generate_analysis(item, i, unified_cache_dir, stats)

                proposed = analysis.proposed_name
                item.reasoning = analysis.reasoning

                proposed_ext = normalize_extension(proposed.extension, item.path.suffix)
                proposed_filename = f"{proposed.stem}{proposed_ext}"
                item.proposed_name = proposed_filename

                if analysis.current_name_suitable:
                    self._handle_suitable_name(item, i, stats)
                    continue

                self._determine_final_name(item, proposed, proposed_filename, stats)

                self.item_processed.emit(i, item)
                self.progress_updated.emit(i + 1, len(self.items))

            except Exception as e:
                stats["errors"] += 1
                error_msg = str(e)
                item.update_status(RenameStatus.ERROR, f"Error: {error_msg}")
                item.error_message = error_msg
                self.error_occurred.emit(i, error_msg)
                self.item_processed.emit(i, item)

        self.finished.emit(stats)

    def stop(self) -> None:
        """Request graceful shutdown."""
        self._stop_requested = True
