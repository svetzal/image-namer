"""Apply rename operations from processing results.

Pure function that determines which renames to apply, delegating
actual filesystem mutations to an injected FileRenamerPort.
"""

from pathlib import Path

from operations.find_references import find_references
from operations.models import ProcessingResult, RenameOutcome, RenameStatus
from operations.ports import FileRenamerPort, MarkdownFilePort
from operations.update_references import update_references


def apply_renames(
    results: list[ProcessingResult],
    renamer: FileRenamerPort,
) -> int:
    """Apply renames for results with RENAMED or COLLISION status.

    Only renames files where:
    - Status is RENAMED or COLLISION
    - A path is present
    - The final name differs from the current name

    Args:
        results: List of processing results.
        renamer: Port for performing actual file renames.

    Returns:
        Number of files renamed.
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

    Args:
        old_path: Current file path.
        new_name: Target filename.
        search_root: Root directory to search for markdown files.
        renamer: Port for performing file renames.
        markdown_files: Port for discovering and updating markdown files, or None.
        recursive: Whether to search markdown subdirectories recursively.

    Returns:
        RenameOutcome describing the rename and reference update results.
    """
    if old_path.name == new_name:
        return RenameOutcome(renamed=False, new_path=old_path, references_updated=0)

    new_path = old_path.parent / new_name
    renamer.rename(old_path, new_path)

    references_updated = 0
    if markdown_files is not None and search_root is not None:
        refs = find_references(old_path, search_root, markdown_files, recursive=recursive)
        if refs:
            updates = update_references(refs, old_path.name, new_name, markdown_files)
            references_updated = sum(u.replacement_count for u in updates)

    return RenameOutcome(renamed=True, new_path=new_path, references_updated=references_updated)
