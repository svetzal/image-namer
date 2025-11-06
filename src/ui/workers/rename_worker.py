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

    def run(self) -> None:
        """Process items, emitting signals for real-time UI updates."""
        stats = {"renamed": 0, "unchanged": 0, "cached": 0, "errors": 0}

        unified_cache_dir = self.cache_root / "cache" / "unified"

        for i, item in enumerate(self.items):
            if self._stop_requested:
                break

            try:
                # Single unified analysis (replaces assess + generate)
                self.item_status_changed.emit(
                    i, "assessing", f"Analyzing {item.source_name}..."
                )

                analysis = load_analysis_from_cache(
                    unified_cache_dir, item.path, item.source_name, self.provider, self.model
                )

                if analysis is None:
                    # Cache miss - make single LLM call
                    self.item_status_changed.emit(
                        i, "generating", f"Analyzing {item.source_name} (calling LLM)..."
                    )

                    analysis = analyze_image(item.path, item.source_name, llm=self.llm)

                    save_analysis_to_cache(
                        unified_cache_dir,
                        item.path,
                        item.source_name,
                        self.provider,
                        self.model,
                        analysis,
                    )
                else:
                    # Cache hit for unified analysis
                    self.item_status_changed.emit(
                        i, "cache_hit", f"✓ Analysis cached for {item.source_name}"
                    )
                    stats["cached"] += 1
                    item.cached = True

                # Extract proposed name and reasoning from analysis
                proposed = analysis.proposed_name
                item.reasoning = analysis.reasoning  # Store LLM reasoning

                # Normalize proposed name
                proposed_ext = proposed.extension if proposed.extension.startswith(".") else f".{proposed.extension}"
                if not proposed.extension:
                    proposed_ext = item.path.suffix

                proposed_filename = f"{proposed.stem}{proposed_ext}"

                # Always update proposed_name
                item.proposed_name = proposed_filename

                # Handle suitable names (current name already good)
                if analysis.current_name_suitable:
                    # Only update if not manually edited
                    if not item.manually_edited:
                        item.final_name = item.source_name
                        item.update_status(RenameStatus.UNCHANGED, "Current name is already suitable")
                    else:
                        item.update_status(RenameStatus.UNCHANGED, "Current name suitable (filename locked by user)")
                    stats["unchanged"] += 1
                    self.item_processed.emit(i, item)
                    self.progress_updated.emit(i + 1, len(self.items))
                    continue

                # Only update final_name if not manually edited by user
                if item.manually_edited:
                    # User has locked this filename - preserve it
                    item.update_status(RenameStatus.READY, "Ready (filename locked by user)")
                    stats["renamed"] += 1
                elif item.path.stem == proposed.stem:
                    # Check idempotency
                    item.update_status(RenameStatus.UNCHANGED, "Proposed name matches current")
                    item.final_name = item.source_name
                    stats["unchanged"] += 1
                else:
                    # Check for collisions with existing files and already-planned names
                    final_filename = self._resolve_collision(
                        item.path.parent, proposed.stem, proposed_ext, i
                    )

                    if final_filename != proposed_filename:
                        item.update_status(RenameStatus.COLLISION, f"Collision resolved: {final_filename}")
                    else:
                        item.update_status(RenameStatus.READY, "Ready to rename")

                    item.final_name = final_filename
                    stats["renamed"] += 1

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
