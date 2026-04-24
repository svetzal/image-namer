"""Pure orchestration functions for UI rename actions.

These functions encapsulate the wiring between Qt-agnostic inputs and
operations-layer calls, making the delegation testable without Qt.
"""

from pathlib import Path

from operations.adapters import FilesystemMarkdownFiles, FilesystemRenamer
from operations.apply_renames import apply_rename_with_references
from ui.models.ui_models import BatchRenameResult, RenameItem, RenameStatus


def perform_rename_with_refs(
    old_path: Path,
    new_name: str,
    search_root: Path | None,
    update_refs: bool,
    recursive: bool,
) -> int:
    """Rename a file and optionally update markdown references.

    Constructs concrete adapters and delegates to apply_rename_with_references.

    Args:
        old_path: Current file path.
        new_name: Target filename.
        search_root: Root directory to search for markdown files.
        update_refs: Whether to update markdown references.
        recursive: Whether to search markdown subdirectories recursively.

    Returns:
        Number of markdown references updated.
    """
    renamer = FilesystemRenamer()
    markdown_files = FilesystemMarkdownFiles() if (update_refs and search_root is not None) else None
    outcome = apply_rename_with_references(
        old_path, new_name, search_root, renamer, markdown_files, recursive
    )
    return outcome.references_updated


def perform_batch_rename(
    items_to_rename: list[RenameItem],
    search_root: Path | None,
    update_refs: bool,
    recursive: bool,
) -> BatchRenameResult:
    """Rename a batch of files and optionally update markdown references.

    Mutates each item's status fields in-place and returns aggregate counts.

    Args:
        items_to_rename: Items to rename (each must have final_name set).
        search_root: Root directory to search for markdown files.
        update_refs: Whether to update markdown references.
        recursive: Whether to search markdown subdirectories recursively.

    Returns:
        BatchRenameResult with renamed_count, error_count, total_refs_updated.
    """
    result = BatchRenameResult()

    for item in items_to_rename:
        old_path = item.path
        new_name = item.final_name

        if old_path.name == new_name:
            continue

        try:
            refs_updated = perform_rename_with_refs(old_path, new_name, search_root, update_refs, recursive)
            result.renamed_count += 1
            result.total_refs_updated += refs_updated
            item.status = RenameStatus.COMPLETED
            item.status_message = "Successfully renamed"
            item.source_name = new_name
            item.path = old_path.parent / new_name
        except (OSError, PermissionError) as e:
            result.error_count += 1
            item.status = RenameStatus.ERROR
            item.status_message = f"Rename failed: {e}"
            item.error_message = str(e)

    return result
