"""Apply rename operations from processing results.

Pure function that determines which renames to apply, delegating
actual filesystem mutations to an injected FileRenamerPort.
"""

from operations.models import ProcessingResult, RenameStatus
from operations.ports import FileRenamerPort


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
