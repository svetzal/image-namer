"""Apply rename operations from processing results via an injected FileRenamerPort."""

import logging
from pathlib import Path

from constants import FILESYSTEM_IO_ERRORS
from operations.batch_references import process_single_file_references
from operations.models import (
    FileCommandOutcome,
    ProcessingResult,
    RenameApplicationResult,
    RenameFailure,
    RenameOutcome,
    RenameStatus,
)
from operations.ports import FileRenamerPort, MarkdownFilePort

logger = logging.getLogger(__name__)


def apply_renames(
    results: list[ProcessingResult],
    renamer: FileRenamerPort,
) -> RenameApplicationResult:
    """Apply renames for results with RENAMED or COLLISION status.

    Only renames files where:
    - Status is RENAMED or COLLISION
    - A path is present
    - The final name differs from the current name
    """
    rename_pairs = [
        (result.path, result.path.with_name(result.final))
        for result in results
        if result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION)
        and result.path
        and result.path.with_name(result.final) != result.path
    ]
    applied = 0
    failures: list[RenameFailure] = []
    for src, dst in rename_pairs:
        try:
            renamer.rename(src, dst)
            applied += 1
        except FILESYSTEM_IO_ERRORS as e:
            logger.warning("Failed to rename %s -> %s: %s: %s", src, dst, type(e).__name__, e)
            failures.append(RenameFailure(source=str(src), destination=str(dst), error=str(e)))
    return RenameApplicationResult(applied=applied, failures=failures)


def apply_rename_with_references(
    old_path: Path,
    new_name: str,
    search_root: Path | None,
    renamer: FileRenamerPort,
    markdown_files: MarkdownFilePort | None,
    recursive: bool,
) -> RenameOutcome:
    """Rename a single file and optionally update markdown references.

    Short-circuits if the current filename already matches new_name. When
    markdown_files and search_root are provided, finds and updates all
    markdown references to the renamed file.
    """
    if old_path.name == new_name:
        return RenameOutcome(renamed=False, new_path=old_path, references_updated=0)

    new_path = old_path.parent / new_name
    try:
        renamer.rename(old_path, new_path)
    except FILESYSTEM_IO_ERRORS as e:
        logger.warning("Failed to rename %s -> %s: %s: %s", old_path, new_path, type(e).__name__, e)
        return RenameOutcome(renamed=False, new_path=old_path, references_updated=0)

    ref_result = None
    references_updated = 0
    if markdown_files is not None and search_root is not None:
        ref_result = process_single_file_references(
            old_path, new_name, search_root, markdown_files, dry_run=False
        )
        references_updated = ref_result.total_references

    return RenameOutcome(
        renamed=True, new_path=new_path, references_updated=references_updated, reference_result=ref_result
    )


def apply_single_file_command(
    path: Path,
    final_name: str,
    update_refs: bool,
    refs_root: Path | None,
    dry_run: bool,
    renamer: FileRenamerPort,
    markdown_files: MarkdownFilePort,
) -> FileCommandOutcome:
    """Orchestrate apply/dry-run logic for the single-file CLI command.

    Encapsulates dry-run branching, conditional adapter construction, and
    rename-failure detection so the CLI command body stays output-only.
    """
    search_root = refs_root if refs_root is not None else path.parent

    if dry_run:
        if update_refs and final_name != path.name:
            ref_result = process_single_file_references(
                path, final_name, search_root, markdown_files, dry_run=True
            )
            return FileCommandOutcome(reference_result=ref_result)
        return FileCommandOutcome()

    outcome = apply_rename_with_references(
        path,
        final_name,
        search_root if update_refs else None,
        renamer,
        markdown_files if update_refs else None,
        recursive=False,
    )
    rename_failed = final_name != path.name and not outcome.renamed
    return FileCommandOutcome(
        renamed=outcome.renamed,
        rename_failed=rename_failed,
        reference_result=outcome.reference_result,
    )
