"""Single-image processing orchestration.

Contains the pure business logic for assessing, naming, and resolving collisions
for a single image file. I/O boundaries (cache, LLM analysis) are injected via
Protocol-based ports — errors are captured in ProcessingResult.
"""

from pathlib import Path

from operations.models import ImageAnalysis, ProcessingResult, ProposedName, RenameStatus
from operations.ports import AnalysisCachePort, ImageAnalyzerPort, ProgressCallback
from utils.fs import next_available_name


def get_or_generate_analysis(
    img_path: Path,
    current_name: str,
    analyzer: ImageAnalyzerPort,
    cache: AnalysisCachePort,
    provider: str,
    model: str,
    progress: ProgressCallback | None = None,
) -> tuple[ImageAnalysis, bool]:
    """Get analysis from cache or generate via analyzer.

    Args:
        img_path: Path to the image file.
        current_name: Current filename (used as cache key component).
        analyzer: Image analyzer for generating analysis on cache miss.
        cache: Analysis cache for loading/saving results.
        provider: LLM provider name for cache key.
        model: Model name for cache key.
        progress: Optional progress callback for cache-hit/miss notifications.

    Returns:
        Tuple of (ImageAnalysis result, cached flag). cached is True when the
        result was loaded from cache, False when freshly generated.

    Raises:
        Exception: Propagates any analyzer failure to the caller.
    """
    analysis = cache.load(img_path, current_name, provider, model)
    if analysis is not None:
        if progress is not None:
            progress.on_cache_hit(img_path, analysis)
        return analysis, True

    if progress is not None:
        progress.on_cache_miss(img_path)
    analysis = analyzer.analyze(img_path, current_name)
    cache.save(img_path, current_name, provider, model, analysis)
    if progress is not None:
        progress.on_analysis_complete(img_path, analysis)
    return analysis, False


def resolve_final_name(
    img_path: Path,
    proposed: ProposedName,
    planned_names: set[str],
) -> tuple[str, str, RenameStatus]:
    """Resolve proposed name to a final filename, handling idempotency and collisions.

    Mutates ``planned_names`` by adding the resolved final filename when a rename
    is needed (RENAMED or COLLISION status).

    Args:
        img_path: Path to the image file (used for idempotency check and collision detection).
        proposed: Proposed filename components from the LLM.
        planned_names: Set of already reserved filenames in the current batch.
            This set is mutated when a name is reserved.

    Returns:
        Tuple of (proposed_filename, final_filename, status) where:

        - proposed_filename: The raw LLM proposal as a full filename string.
        - final_filename: The collision-resolved filename that will be used.
        - status: UNCHANGED if no rename needed, RENAMED for clean rename,
          COLLISION if a suffix was added.
    """
    proposed_stem = proposed.stem
    proposed_filename = proposed.filename_with_fallback(img_path.suffix)
    proposed_ext = proposed_filename[len(proposed_stem):]

    if img_path.stem == proposed_stem:
        return proposed_filename, img_path.name, RenameStatus.UNCHANGED

    final_name = next_available_name(img_path.parent, proposed_stem, proposed_ext, planned_names=planned_names)
    status = RenameStatus.RENAMED if final_name == proposed_filename else RenameStatus.COLLISION

    planned_names.add(final_name)
    return proposed_filename, final_name, status


def process_single_image(
    img_path: Path,
    analyzer: ImageAnalyzerPort,
    cache: AnalysisCachePort,
    planned_names: set[str],
    provider: str,
    model: str,
    progress: ProgressCallback | None = None,
) -> ProcessingResult:
    """Process a single image file to determine its new name.

    Uses a unified single-LLM-call strategy (assess + name in one call) with
    cache-first optimisation. All errors are captured in the result rather than raised.

    Args:
        img_path: Path to the image file.
        analyzer: Image analyzer for generating analysis.
        cache: Analysis cache for loading/saving results.
        planned_names: Set of already planned filenames to avoid collisions.
            This set is mutated when a name is reserved.
        provider: LLM provider name for cache key.
        model: Model name for cache key.
        progress: Optional progress callback for cache-hit/miss notifications.

    Returns:
        ProcessingResult describing what happened.
    """
    current_name = img_path.name

    try:
        analysis, cached = get_or_generate_analysis(
            img_path, current_name, analyzer, cache, provider, model, progress
        )
    except (OSError, ConnectionError, TimeoutError, ValueError, RuntimeError):
        return ProcessingResult(
            source=img_path.name,
            proposed="ERROR",
            final=img_path.name,
            status=RenameStatus.ERROR,
        )

    if analysis.current_name_suitable:
        return ProcessingResult(
            source=img_path.name,
            proposed=img_path.name,
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
            reasoning=analysis.reasoning,
            cached=cached,
        )

    proposed_filename, final_name, status = resolve_final_name(
        img_path, analysis.proposed_name, planned_names
    )

    if status == RenameStatus.UNCHANGED:
        return ProcessingResult(
            source=img_path.name,
            proposed=proposed_filename,
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
            reasoning=analysis.reasoning,
            cached=cached,
        )

    return ProcessingResult(
        source=img_path.name,
        proposed=proposed_filename,
        final=final_name,
        status=status,
        path=img_path,
        reasoning=analysis.reasoning,
        cached=cached,
    )
