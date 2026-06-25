"""Pure, Qt-agnostic business logic for background worker operations.

Extracts status mapping and item mutation out of the QThread workers so they
can be tested without any Qt dependency.
"""

from operations.models import ProcessingResult
from operations.models import RenameStatus
from ui import status_messages as msg
from ui.models.ui_models import ItemStatus, RenameItem
from ui.rename_status_ui import RENAME_STATUS_UI


def map_ops_status_to_ui(status: RenameStatus) -> ItemStatus:
    """Translate an operations-layer RenameStatus to the UI ItemStatus.

    Args:
        status: The operations-layer status value.

    Returns:
        The corresponding UI status value.
    """
    return RENAME_STATUS_UI[status].ui_status


def mark_manually_edited(item: RenameItem) -> None:
    """Handle an item whose filename was manually locked by the user.

    Marks the item ready without LLM processing.

    Args:
        item: The item to update in-place.
    """
    item.update_status(ItemStatus.READY, msg.READY_LOCKED)


def apply_processing_result(
    item: RenameItem,
    result: ProcessingResult,
) -> None:
    """Copy LLM processing result fields onto item.

    Mutates item in-place.  The caller is responsible for emitting any Qt
    signals (e.g. error_occurred) after this call.

    Args:
        item: The item to update in-place.
        result: The ProcessingResult returned by process_single_image.
    """
    item.reasoning = result.reasoning
    item.cached = result.cached
    item.proposed_name = result.proposed
    item.final_name = result.final

    info = RENAME_STATUS_UI[result.status]
    item.update_status(info.ui_status, info.fresh_message(result.final))


def apply_cached_result(item: RenameItem, result: ProcessingResult) -> None:
    """Apply a cached ProcessingResult onto an item from the cache-loader path.

    Handles the UNCHANGED vs other and manually_edited vs not matrix that
    determines final_name assignment and status messages.

    Args:
        item: The item to update in-place.
        result: The ProcessingResult built from cached analysis.
    """
    item.reasoning = result.reasoning
    item.proposed_name = result.proposed
    item.cached = True

    info = RENAME_STATUS_UI[result.status]

    if result.status == RenameStatus.UNCHANGED:
        if not item.manually_edited:
            item.final_name = result.final
            item.update_status(info.ui_status, info.cached_message)
        else:
            item.update_status(info.ui_status, info.locked_message)
    else:
        if not item.manually_edited:
            item.final_name = result.final
            item.update_status(info.ui_status, info.cached_message)
        else:
            item.update_status(info.ui_status, info.locked_message)
