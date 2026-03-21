"""Single-image processing orchestration.

Contains the pure business logic for assessing, naming, and resolving collisions
for a single image file. No I/O side effects — errors are captured in ProcessingResult.
"""

from pathlib import Path

from mojentic.llm import LLMBroker

from operations.assess_name import assess_name
from operations.cache import (
    load_assessment_from_cache,
    load_from_cache,
    save_assessment_to_cache,
    save_to_cache,
)
from operations.generate_name import generate_name
from operations.models import ProcessingResult, ProposedName, RenameStatus


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
        Next available filename.
    """
    suffix_num = 2
    while True:
        test_name = f"{stem}-{suffix_num}{ext}"
        if not (directory / test_name).exists() and test_name not in planned_names:
            return test_name
        suffix_num += 1


def process_single_image(
    img_path: Path,
    llm: LLMBroker,
    planned_names: set[str],
    cache_root: Path,
    provider: str,
    model: str,
) -> ProcessingResult:
    """Process a single image file to determine its new name.

    Runs assessment-first: if current filename is already suitable, skip generation.
    All errors are captured in the result rather than raised.

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
    analysis_cache_dir = cache_root / "cache" / "analysis"
    names_cache_dir = cache_root / "cache" / "names"

    current_name = img_path.name
    current_proposed = ProposedName(stem=img_path.stem, extension=img_path.suffix)

    assessment = load_assessment_from_cache(
        analysis_cache_dir, img_path, current_name, provider, model
    )

    if assessment is None:
        try:
            assessment = assess_name(img_path, current_proposed, llm=llm)
            save_assessment_to_cache(
                analysis_cache_dir, img_path, current_name, provider, model, assessment
            )
        except Exception:
            return ProcessingResult(
                source=img_path.name,
                proposed="ERROR",
                final=img_path.name,
                status=RenameStatus.ERROR,
            )

    if assessment.suitable:
        return ProcessingResult(
            source=img_path.name,
            proposed=img_path.name,
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
        )

    proposed = load_from_cache(names_cache_dir, img_path, provider, model)

    if proposed is None:
        try:
            proposed = generate_name(img_path, llm=llm)
            save_to_cache(names_cache_dir, img_path, provider, model, proposed)
        except Exception:
            return ProcessingResult(
                source=img_path.name,
                proposed="ERROR",
                final=img_path.name,
                status=RenameStatus.ERROR,
            )

    proposed_stem = proposed.stem
    proposed_ext = normalize_extension(proposed.extension, img_path.suffix)

    if img_path.stem == proposed_stem:
        return ProcessingResult(
            source=img_path.name,
            proposed=f"{proposed_stem}{proposed_ext}",
            final=img_path.name,
            status=RenameStatus.UNCHANGED,
            path=img_path,
        )

    candidate = f"{proposed_stem}{proposed_ext}"
    if (img_path.parent / candidate).exists() or candidate in planned_names:
        final_name = find_next_available_in_batch(
            img_path.parent, proposed_stem, proposed_ext, planned_names
        )
        status = RenameStatus.COLLISION
    else:
        final_name = candidate
        status = RenameStatus.RENAMED

    planned_names.add(final_name)

    return ProcessingResult(
        source=img_path.name,
        proposed=candidate,
        final=final_name,
        status=status,
        path=img_path,
    )
