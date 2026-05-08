"""Batch and single-file markdown reference update orchestration."""

from pathlib import Path

from operations.find_references import find_references, ref_matches_filename
from operations.models import (
    BatchReferenceResult,
    CollectedReferences,
    MarkdownReference,
    ProcessingResult,
    RenameStatus,
)
from operations.ports import MarkdownFilePort
from operations.update_references import update_references


def _collect_references(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> CollectedReferences:
    """Collect markdown references and rename map for RENAMED/COLLISION results where name differs."""
    all_refs: list[MarkdownReference] = []
    rename_map: dict[str, str] = {}

    for result in results:
        if result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION) and result.path:
            if result.final != result.path.name:
                refs = find_references(result.path, search_root, markdown_files, recursive=True)
                all_refs.extend(refs)
                rename_map[result.path.name] = result.final

    return CollectedReferences(references=all_refs, rename_map=rename_map)


def apply_batch_reference_updates(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> BatchReferenceResult:
    """Find and apply markdown reference updates for renamed files.

    Only processes results with RENAMED or COLLISION status where the
    final name differs from the source.
    """
    collected = _collect_references(results, search_root, markdown_files)

    if not collected.references:
        return BatchReferenceResult(total_references=0, files_updated=0)

    updates_by_file: dict[Path, int] = {}
    for old_name, new_name in collected.rename_map.items():
        file_refs = [r for r in collected.references if ref_matches_filename(r, old_name)]
        if file_refs:
            file_updates = update_references(file_refs, old_name, new_name, markdown_files)
            for upd in file_updates:
                updates_by_file[upd.file_path] = (
                    updates_by_file.get(upd.file_path, 0) + upd.replacement_count
                )

    return BatchReferenceResult(
        total_references=sum(updates_by_file.values()),
        files_updated=len(updates_by_file),
    )


def count_single_file_references(
    path: Path,
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> BatchReferenceResult:
    """Count markdown references to a single file without applying updates."""
    refs = find_references(path, search_root, markdown_files, recursive=True)
    if not refs:
        return BatchReferenceResult(total_references=0, files_updated=0)
    return BatchReferenceResult(
        total_references=len(refs),
        files_updated=len({r.file_path for r in refs}),
    )


def apply_single_file_reference_updates(
    path: Path,
    final_name: str,
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> BatchReferenceResult:
    """Find and apply markdown reference updates for a single renamed file."""
    refs = find_references(path, search_root, markdown_files, recursive=True)
    if not refs:
        return BatchReferenceResult(total_references=0, files_updated=0)
    updates = update_references(refs, path.name, final_name, markdown_files)
    return BatchReferenceResult(
        total_references=sum(u.replacement_count for u in updates),
        files_updated=len(updates),
    )


def count_batch_references(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> BatchReferenceResult:
    """Count markdown references for renamed files without applying updates.

    Used for dry-run mode to preview what would be updated.
    """
    collected = _collect_references(results, search_root, markdown_files)

    if not collected.references:
        return BatchReferenceResult(total_references=0, files_updated=0)

    unique_files = len({r.file_path for r in collected.references})
    return BatchReferenceResult(
        total_references=len(collected.references),
        files_updated=unique_files,
    )


def process_single_file_references(
    path: Path,
    final_name: str,
    search_root: Path,
    markdown_files: MarkdownFilePort,
    *,
    dry_run: bool,
) -> BatchReferenceResult:
    """Count or apply markdown reference updates for a single renamed file based on dry_run."""
    if dry_run:
        return count_single_file_references(path, search_root, markdown_files)
    return apply_single_file_reference_updates(path, final_name, search_root, markdown_files)


def process_batch_references(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
    *,
    dry_run: bool,
) -> BatchReferenceResult:
    """Count or apply markdown reference updates for a batch of results based on dry_run."""
    if dry_run:
        return count_batch_references(results, search_root, markdown_files)
    return apply_batch_reference_updates(results, search_root, markdown_files)
