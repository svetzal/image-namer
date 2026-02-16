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

    def _get_or_generate_analysis(self, item: RenameItem, i: int, unified_cache_dir: Path, stats: dict) -> object:
        """Get analysis from cache or generate using LLM.

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

    def _normalize_proposed_extension(self, proposed_ext: str, fallback_ext: str) -> str:
        """Normalize proposed extension to include leading dot.

        Args:
            proposed_ext: Extension from proposed name.
            fallback_ext: Fallback extension from original file.

        Returns:
            Normalized extension with leading dot.
        """
        if proposed_ext.startswith("."):
            return proposed_ext
        if not proposed_ext:
            return fallback_ext
        return f".{proposed_ext}"

    def _handle_suitable_name(self, item: RenameItem, i: int, stats: dict) -> None:
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
        self, item: RenameItem, proposed_stem: str, proposed_ext: str, proposed_filename: str, i: int, stats: dict
    ) -> None:
        """Determine final name considering manual edits, idempotency, and collisions.

        Args:
            item: RenameItem to process.
            proposed_stem: Proposed filename stem.
            proposed_ext: Proposed extension with leading dot.
            proposed_filename: Full proposed filename.
            i: Item index for collision resolution.
            stats: Statistics dict to update.
        """
        if item.manually_edited:
            item.update_status(RenameStatus.READY, "Ready (filename locked by user)")
            stats["renamed"] += 1
        elif item.path.stem == proposed_stem:
            item.update_status(RenameStatus.UNCHANGED, "Proposed name matches current")
            item.final_name = item.source_name
            stats["unchanged"] += 1
        else:
            final_filename = self._resolve_collision(item.path.parent, proposed_stem, proposed_ext, i)

            if final_filename != proposed_filename:
                item.update_status(RenameStatus.COLLISION, f"Collision resolved: {final_filename}")
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

                proposed_ext = self._normalize_proposed_extension(proposed.extension, item.path.suffix)
                proposed_filename = f"{proposed.stem}{proposed_ext}"
                item.proposed_name = proposed_filename

                if analysis.current_name_suitable:
                    self._handle_suitable_name(item, i, stats)
                    continue

                self._determine_final_name(item, proposed.stem, proposed_ext, proposed_filename, i, stats)

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

    def _resolve_collision(self, directory: Path, stem: str, ext: str, current_index: int) -> str:
        """Resolve filename collisions.

        Checks both filesystem and planned names from batch processing.

        Args:
            directory: Directory where file will be renamed.
            stem: Proposed filename stem.
            ext: File extension with leading dot.
            current_index: Index of current item being processed.

        Returns:
            Final filename (may be same as proposed, or with -2, -3, etc. suffix).
        """
        candidate = f"{stem}{ext}"

        # Check if this collides with existing file on disk
        if (directory / candidate).exists():
            # Make sure it's not the source file itself
            if current_index < len(self.items):
                source_name = self.items[current_index].source_name
                if candidate == source_name:
                    # Proposed name is same as source - no collision
                    self._planned_names.add(candidate)
                    return candidate

        # Check if already planned in this batch
        if candidate not in self._planned_names:
            # No collision - use as-is
            self._planned_names.add(candidate)
            return candidate

        # Collision detected - find next available with suffix
        suffix_num = 2
        while True:
            test_name = f"{stem}-{suffix_num}{ext}"
            if not (directory / test_name).exists() and test_name not in self._planned_names:
                self._planned_names.add(test_name)
                return test_name
            suffix_num += 1
