"""Single-image processing orchestration.

Contains the pure business logic for assessing, naming, and resolving collisions
for a single image file. No I/O side effects — errors are captured in ProcessingResult.
"""

from pathlib import Path

from mojentic.llm import LLMBroker

from operations.analyze_image import analyze_image
from operations.cache import (
    load_analysis_from_cache,
    save_analysis_to_cache,
)
from operations.models import ImageAnalysis, ProcessingResult, ProposedName, RenameStatus


def normalize_extension(proposed_ext: str, fallback_ext: str) -> str:
    """Normalize extension to include leading dot.

    Args:
        proposed_ext: The proposed extension (may or may not have leading dot).
        fallback_ext: Fallback extension to use if proposed is empty.

    Returns:
        Extension with leading dot.
    """
    if not proposed_ext:
        return fallback_ext
    if proposed_ext.startswith("."):
        return proposed_ext
    return f".{proposed_ext}"


def find_next_available_in_batch(
    directory: Path,
    stem: str,
    ext: str,
    planned_names: set[str]
) -> str:
    """Find next available filename considering both disk and planned renames.

    Args:
        directory: Directory to check for existing files.
        stem: Base filename stem.
        ext: File extension with leading dot.
        planned_names: Set of already planned filenames.

    Returns:
        Next available filename (stem-2.ext, stem-3.ext, ...).
    """
    suffix_num = 2
    while True:
        test_name = f"{stem}-{suffix_num}{ext}"
        if not (directory / test_name).exists() and test_name not in planned_names:
            return test_name
        suffix_num += 1


def get_or_generate_analysis(
    img_path: Path,
    current_name: str,
    llm: LLMBroker,
    cache_dir: Path,
    provider: str,
    model: str,
) -> ImageAnalysis:
    """Get analysis from cache or generate via LLM.

    Args:
        img_path: Path to the image file.
        current_name: Current filename (used as cache key component).
        llm: LLM broker for analysis generation.
        cache_dir: Unified cache directory (cache/unified).
        provider: LLM provider name for cache key.
        model: Model name for cache key.

    Returns:
        ImageAnalysis result.

    Raises:
        Exception: Propagates any LLM or I/O failure to the caller.
    """
    analysis = load_analysis_from_cache(cache_dir, img_path, current_name, provider, model)
    if analysis is None:
        analysis = analyze_image(img_path, current_name, llm=llm)
        save_analysis_to_cache(cache_dir, img_path, current_name, provider, model, analysis)
    return analysis


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
    proposed_ext = normalize_extension(proposed.extension, img_path.suffix)
    proposed_filename = f"{proposed_stem}{proposed_ext}"

    if img_path.stem == proposed_stem:
        return proposed_filename, img_path.name, RenameStatus.UNCHANGED

    candidate = proposed_filename
    if (img_path.parent / candidate).exists() or candidate in planned_names:
        final_name = find_next_available_in_batch(
            img_path.parent, proposed_stem, proposed_ext, planned_names
        )
        status = RenameStatus.COLLISION
    else:
        final_name = candidate
        status = RenameStatus.RENAMED

    planned_names.add(final_name)
    return proposed_filename, final_name, status


def process_single_image(
    img_path: Path,
    llm: LLMBroker,
    planned_names: set[str],
    cache_root: Path,
    provider: str,
    model: str,
) -> ProcessingResult:
    """Process a single image file to determine its new name.

    Uses a unified single-LLM-call strategy (assess + name in one call) with
    cache-first optimisation. All errors are captured in the result rather than raised.

    Args:
        img_path: Path to the image file.
        llm: LLM broker for name generation.
        planned_names: Set of already planned filenames to avoid collisions.
            This set is mutated when a name is reserved.
        cache_root: Path to the cache root directory (.image_namer).
        provider: LLM provider name for cache key.
        model: Model name for cache key.

    Returns:
        ProcessingResult describing what happened.
    """
    unified_cache_dir = cache_root / "cache" / "unified"
    current_name = img_path.name

    try:
        analysis = get_or_generate_analysis(
            img_path, current_name, llm, unified_cache_dir, provider, model
        )
    except Exception:
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
        )

    return ProcessingResult(
        source=img_path.name,
        proposed=proposed_filename,
        final=final_name,
        status=status,
        path=img_path,
    )
