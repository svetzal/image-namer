"""Pure, Qt-agnostic business logic for background worker operations.

Extracts status mapping, stats accumulation, and item mutation out of the
QThread workers so they can be tested without any Qt dependency.
"""

from operations.models import ProcessingResult
from operations.models import RenameStatus as OpsRenameStatus
from ui.models.ui_models import AnalysisStats, RenameItem, RenameStatus


def map_ops_status_to_ui(status: OpsRenameStatus) -> RenameStatus:
    """Translate an operations-layer RenameStatus to the UI RenameStatus.

    Args:
        status: The operations-layer status value.

    Returns:
        The corresponding UI status value.
    """
    mapping: dict[OpsRenameStatus, RenameStatus] = {
        OpsRenameStatus.RENAMED: RenameStatus.READY,
        OpsRenameStatus.UNCHANGED: RenameStatus.UNCHANGED,
        OpsRenameStatus.COLLISION: RenameStatus.COLLISION,
        OpsRenameStatus.ERROR: RenameStatus.ERROR,
    }
    return mapping[status]


def mark_manually_edited(item: RenameItem, stats: AnalysisStats) -> None:
    """Handle an item whose filename was manually locked by the user.

    Marks the item ready without LLM processing and counts it as a rename.

    Args:
        item: The item to update in-place.
        stats: Cumulative stats to increment.
    """
    item.update_status(RenameStatus.READY, "Ready (filename locked by user)")
    stats.renamed += 1


def apply_processing_result(
    item: RenameItem,
    result: ProcessingResult,
    stats: AnalysisStats,
) -> None:
    """Copy LLM processing result fields onto item and update stats.

    Mutates both item and stats in-place.  The caller is responsible for
    emitting any Qt signals (e.g. error_occurred) after this call.

    Args:
        item: The item to update in-place.
        result: The ProcessingResult returned by process_single_image.
        stats: Cumulative stats to increment.
    """
    item.reasoning = result.reasoning
    item.cached = result.cached
    item.proposed_name = result.proposed
    item.final_name = result.final

    if result.cached:
        stats.cached += 1

    if result.status == OpsRenameStatus.ERROR:
        stats.errors += 1
        item.update_status(RenameStatus.ERROR, "Error during analysis")
    elif result.status == OpsRenameStatus.UNCHANGED:
        item.update_status(RenameStatus.UNCHANGED, "Current name is already suitable")
        stats.unchanged += 1
    elif result.status == OpsRenameStatus.COLLISION:
        item.update_status(RenameStatus.COLLISION, f"Collision resolved: {result.final}")
        stats.renamed += 1
    else:
        item.update_status(RenameStatus.READY, "Ready to rename")
        stats.renamed += 1


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

    if result.status == OpsRenameStatus.UNCHANGED:
        if not item.manually_edited:
            item.final_name = result.final
            item.update_status(RenameStatus.UNCHANGED, "Already suitable (cached)")
        else:
            item.update_status(RenameStatus.UNCHANGED, "Already suitable (filename locked by user)")
    else:
        if not item.manually_edited:
            item.final_name = result.final
            item.update_status(RenameStatus.READY, "Ready (from cache)")
        else:
            item.update_status(RenameStatus.READY, "Ready (filename locked by user)")
