"""Apply rename operations from processing results.

Pure function that determines which renames to apply, delegating
actual filesystem mutations to an injected FileRenamerPort.
"""

from pathlib import Path

from operations.batch_references import process_single_file_references
from operations.models import ProcessingResult, RenameOutcome, RenameStatus
from operations.ports import FileRenamerPort, MarkdownFilePort


def apply_renames(
    results: list[ProcessingResult],
    renamer: FileRenamerPort,
) -> int:
    """Apply renames for results with RENAMED or COLLISION status.

    Only renames files where:
    - Status is RENAMED or COLLISION
    - A path is present
    - The final name differs from the current name
    """
    count = 0
    for result in results:
        if (
            result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION)
            and result.path
        ):
            img_path = result.path
            final_path = img_path.with_name(result.final)
            if final_path != img_path:
                renamer.rename(img_path, final_path)
                count += 1
    return count


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
    renamer.rename(old_path, new_path)

    references_updated = 0
    if markdown_files is not None and search_root is not None:
        ref_result = process_single_file_references(
            old_path, new_name, search_root, markdown_files, dry_run=False
        )
        references_updated = ref_result.total_references

    return RenameOutcome(renamed=True, new_path=new_path, references_updated=references_updated)
