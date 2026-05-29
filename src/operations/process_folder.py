"""Batch folder processing: pure functions for multiple images and statistics."""

from pathlib import Path

from operations.models import FolderStatistics, ProcessingResult, RenameStatus
from operations.ports import AnalysisCachePort, ImageAnalyzerPort, ProgressCallback
from operations.process_image import process_single_image


def process_folder(
    image_files: list[Path],
    analyzer: ImageAnalyzerPort,
    cache: AnalysisCachePort,
    progress: ProgressCallback | None = None,
) -> list[ProcessingResult]:
    """Process all image files in a list, tracking cross-file name collisions."""
    planned_names: set[str] = set()
    return [
        process_single_image(img, analyzer, cache, planned_names, progress)
        for img in image_files
    ]


def compute_statistics(results: list[ProcessingResult]) -> FolderStatistics:
    return FolderStatistics(
        renamed=sum(1 for r in results if r.status == RenameStatus.RENAMED),
        unchanged=sum(1 for r in results if r.status == RenameStatus.UNCHANGED),
        collision=sum(1 for r in results if r.status == RenameStatus.COLLISION),
        error=sum(1 for r in results if r.status == RenameStatus.ERROR),
    )
