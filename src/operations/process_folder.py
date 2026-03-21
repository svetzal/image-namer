"""Batch folder processing orchestration.

Contains pure functions for processing multiple image files and computing statistics.
No I/O side effects — no printing, no filesystem mutations.
"""

from pathlib import Path

from mojentic.llm import LLMBroker

from operations.models import ProcessingResult, RenameStatus
from operations.process_image import process_single_image


def process_folder(
    image_files: list[Path],
    llm: LLMBroker,
    cache_root: Path,
    provider: str,
    model: str,
) -> list[ProcessingResult]:
    """Process all image files in a list, tracking cross-file name collisions.

    Args:
        image_files: List of image file paths to process.
        llm: LLM broker for name generation.
        cache_root: Path to the cache root directory (.image_namer).
        provider: LLM provider name for cache key.
        model: Model name for cache key.

    Returns:
        List of ProcessingResult objects, one per input file.
    """
    planned_names: set[str] = set()
    return [
        process_single_image(img, llm, planned_names, cache_root, provider, model)
        for img in image_files
    ]


def compute_statistics(results: list[ProcessingResult]) -> dict[RenameStatus, int]:
    """Compute status counts from a list of processing results.

    Args:
        results: List of ProcessingResult objects.

    Returns:
        Dictionary mapping each RenameStatus to its count.
    """
    return {
        status: sum(1 for r in results if r.status == status)
        for status in RenameStatus
    }
