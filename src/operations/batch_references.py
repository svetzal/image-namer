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


def _count_only_result(
    references: list[MarkdownReference],
    *,
    dry_run: bool,
) -> BatchReferenceResult | None:
    if not references:
        return BatchReferenceResult(total_references=0, files_updated=0)
    if dry_run:
        return BatchReferenceResult(
            total_references=len(references),
            files_updated=len({r.file_path for r in references}),
        )
    return None


def _collect_references(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
) -> CollectedReferences:
    """Collect markdown references and rename map for RENAMED/COLLISION results where name differs."""
    renamed = [
        (r.path, r.final) for r in results
        if r.status in (RenameStatus.RENAMED, RenameStatus.COLLISION)
        and r.path is not None
        and r.final != r.path.name
    ]
    rename_map = {path.name: final for path, final in renamed}
    all_refs = [
        ref
        for path, _final in renamed
        for ref in find_references(path, search_root, markdown_files, recursive=True)
    ]
    return CollectedReferences(references=all_refs, rename_map=rename_map)


def _update_single_file_references(
    path: Path,
    final_name: str,
    search_root: Path,
    markdown_files: MarkdownFilePort,
    *,
    dry_run: bool,
) -> BatchReferenceResult:
    refs = find_references(path, search_root, markdown_files, recursive=True)
    early = _count_only_result(refs, dry_run=dry_run)
    if early is not None:
        return early
    updates = update_references(refs, path.name, final_name, markdown_files)
    return BatchReferenceResult(
        total_references=sum(u.replacement_count for u in updates),
        files_updated=len(updates),
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
    return _update_single_file_references(path, final_name, search_root, markdown_files, dry_run=dry_run)


def process_batch_references(
    results: list[ProcessingResult],
    search_root: Path,
    markdown_files: MarkdownFilePort,
    *,
    dry_run: bool,
) -> BatchReferenceResult:
    """Count or apply markdown reference updates for a batch of results based on dry_run."""
    collected = _collect_references(results, search_root, markdown_files)
    early = _count_only_result(collected.references, dry_run=dry_run)
    if early is not None:
        return early

    all_updates = []
    for old_name, new_name in collected.rename_map.items():
        matching_refs = [r for r in collected.references if ref_matches_filename(r, old_name)]
        all_updates.extend(update_references(matching_refs, old_name, new_name, markdown_files))
    return BatchReferenceResult(
        total_references=sum(u.replacement_count for u in all_updates),
        files_updated=len({u.file_path for u in all_updates}),
    )
