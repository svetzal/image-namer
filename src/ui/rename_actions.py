"""Pure orchestration functions for UI rename actions.

These functions encapsulate the wiring between Qt-agnostic inputs and
operations-layer calls, making the delegation testable without Qt.
"""

from pathlib import Path

from operations.adapters import FilesystemMarkdownFiles, FilesystemRenamer
from operations.apply_renames import apply_rename_with_references


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
