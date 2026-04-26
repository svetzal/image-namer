"""Single-image processing orchestration.

Contains the pure business logic for assessing, naming, and resolving collisions
for a single image file. I/O boundaries (cache, LLM analysis) are injected via
Protocol-based ports — errors are captured in ProcessingResult.
"""

from pathlib import Path

from operations.models import AnalysisResult, ProcessingResult, ProposedName, RenameStatus, ResolvedName
from operations.ports import AnalysisCachePort, ImageAnalyzerPort, ProgressCallback
from utils.fs import next_available_name


def get_or_generate_analysis(
    img_path: Path,
    current_name: str,
    analyzer: ImageAnalyzerPort,
    cache: AnalysisCachePort,
    progress: ProgressCallback | None = None,
) -> AnalysisResult:
    """Get analysis from cache or generate via analyzer.

    Returns an AnalysisResult. The cached field is True when the result was
    loaded from cache, False when freshly generated.
    """
    analysis = cache.load(img_path, current_name)
    if analysis is not None:
        if progress is not None:
            progress.on_cache_hit(img_path, analysis)
        return AnalysisResult(analysis=analysis, cached=True)

    if progress is not None:
        progress.on_cache_miss(img_path)
    analysis = analyzer.analyze(img_path, current_name)
    cache.save(img_path, current_name, analysis)
    if progress is not None:
        progress.on_analysis_complete(img_path, analysis)
    return AnalysisResult(analysis=analysis, cached=False)


def resolve_final_name(
    img_path: Path,
    proposed: ProposedName,
    planned_names: set[str],
) -> ResolvedName:
    """Resolve proposed name to a final filename, handling idempotency and collisions.

    Mutates ``planned_names`` by adding the resolved final filename when a rename
    is needed (RENAMED or COLLISION status).
    """
    proposed_stem = proposed.stem
    proposed_filename = proposed.filename_with_fallback(img_path.suffix)
    proposed_ext = proposed_filename[len(proposed_stem):]

    if img_path.stem == proposed_stem:
        return ResolvedName(
            proposed_filename=proposed_filename,
            final_name=img_path.name,
            status=RenameStatus.UNCHANGED,
        )

    final_name = next_available_name(img_path.parent, proposed_stem, proposed_ext, planned_names=planned_names)
    status = RenameStatus.RENAMED if final_name == proposed_filename else RenameStatus.COLLISION

    planned_names.add(final_name)
    return ResolvedName(proposed_filename=proposed_filename, final_name=final_name, status=status)


def process_single_image(
    img_path: Path,
    analyzer: ImageAnalyzerPort,
    cache: AnalysisCachePort,
    planned_names: set[str],
    progress: ProgressCallback | None = None,
) -> ProcessingResult:
    """Process a single image file to determine its new name.

    Uses a unified single-LLM-call strategy (assess + name in one call) with
    cache-first optimisation. All errors are captured in the result rather than raised.
    """
    current_name = img_path.name

    try:
        analysis_result = get_or_generate_analysis(
            img_path, current_name, analyzer, cache, progress
        )
    except (OSError, ConnectionError, TimeoutError, ValueError, RuntimeError):
        return ProcessingResult(
            source=img_path.name,
            proposed="ERROR",
            final=img_path.name,
            status=RenameStatus.ERROR,
        )

    if analysis_result.analysis.current_name_suitable:
        return ProcessingResult(
            source=img_path.name,
            proposed=img_path.name,
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
            reasoning=analysis_result.analysis.reasoning,
            cached=analysis_result.cached,
        )

    resolved = resolve_final_name(
        img_path, analysis_result.analysis.proposed_name, planned_names
    )

    if resolved.status == RenameStatus.UNCHANGED:
        return ProcessingResult(
            source=img_path.name,
            proposed=resolved.proposed_filename,
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
            reasoning=analysis_result.analysis.reasoning,
            cached=analysis_result.cached,
        )

    return ProcessingResult(
        source=img_path.name,
        proposed=resolved.proposed_filename,
        final=resolved.final_name,
        status=resolved.status,
        path=img_path,
        reasoning=analysis_result.analysis.reasoning,
        cached=analysis_result.cached,
    )
