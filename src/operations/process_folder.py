"""Batch folder processing orchestration.

Contains pure functions for processing multiple image files and computing statistics.
No printing, no filesystem mutations beyond what's injected through ports.
"""

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
    """Process all image files in a list, tracking cross-file name collisions.

    Args:
        image_files: List of image file paths to process.
        analyzer: Image analyzer for generating analysis.
        cache: Analysis cache for loading/saving results.
        progress: Optional progress callback for cache-hit/miss notifications.

    Returns:
        List of ProcessingResult objects, one per input file.
    """
    planned_names: set[str] = set()
    return [
        process_single_image(img, analyzer, cache, planned_names, progress)
        for img in image_files
    ]


def compute_statistics(results: list[ProcessingResult]) -> FolderStatistics:
    """Compute status counts from a list of processing results.

    Args:
        results: List of ProcessingResult objects.

    Returns:
        FolderStatistics model with counts for each rename status.
    """
    return FolderStatistics(
        renamed=sum(1 for r in results if r.status == RenameStatus.RENAMED),
        unchanged=sum(1 for r in results if r.status == RenameStatus.UNCHANGED),
        collision=sum(1 for r in results if r.status == RenameStatus.COLLISION),
        error=sum(1 for r in results if r.status == RenameStatus.ERROR),
    )
