"""Batch markdown reference update logic.

Pure functions for collecting and applying reference updates across multiple files.
"""

from pathlib import Path

from operations.find_references import find_references, ref_matches_filename
from operations.models import BatchReferenceResult, ProcessingResult, RenameStatus
from operations.update_references import update_references


def apply_batch_reference_updates(
    results: list[ProcessingResult],
    search_root: Path,
) -> BatchReferenceResult:
    """Find and apply markdown reference updates for renamed files.

    Collects all markdown references to renamed files and updates them.
    Only processes results with RENAMED or COLLISION status where the
    final name differs from the source.

    Args:
        results: List of processing results from folder processing.
        search_root: Root directory to search for markdown files.

    Returns:
        BatchReferenceResult with totals of what was updated.
    """
    all_refs = []
    rename_map: dict[str, str] = {}

    for result in results:
        if result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION) and result.path:
            if result.final != result.path.name:
                refs = find_references(result.path, search_root, recursive=True)
                all_refs.extend(refs)
                rename_map[result.path.name] = result.final

    if not all_refs:
        return BatchReferenceResult(total_references=0, files_updated=0)

    updates_by_file: dict[Path, int] = {}
    for old_name, new_name in rename_map.items():
        file_refs = [r for r in all_refs if ref_matches_filename(r, old_name)]
        if file_refs:
            file_updates = update_references(file_refs, old_name, new_name)
            for upd in file_updates:
                updates_by_file[upd.file_path] = (
                    updates_by_file.get(upd.file_path, 0) + upd.replacement_count
                )

    return BatchReferenceResult(
        total_references=sum(updates_by_file.values()),
        files_updated=len(updates_by_file),
    )


def count_batch_references(
    results: list[ProcessingResult],
    search_root: Path,
) -> BatchReferenceResult:
    """Count markdown references for renamed files without applying updates.

    Used for dry-run mode to preview what would be updated.

    Args:
        results: List of processing results from folder processing.
        search_root: Root directory to search for markdown files.

    Returns:
        BatchReferenceResult with counts of references that would be updated.
    """
    all_refs = []

    for result in results:
        if result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION) and result.path:
            if result.final != result.path.name:
                refs = find_references(result.path, search_root, recursive=True)
                all_refs.extend(refs)

    if not all_refs:
        return BatchReferenceResult(total_references=0, files_updated=0)

    unique_files = len({r.file_path for r in all_refs})
    return BatchReferenceResult(
        total_references=len(all_refs),
        files_updated=unique_files,
    )
