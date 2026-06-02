"""Tests for pure worker business logic in worker_logic.py."""

from pathlib import Path

from operations.models import ProcessingResult
from operations.models import RenameStatus as OpsRenameStatus
from ui.models.ui_models import AnalysisStats, RenameItem, RenameStatus
from ui.worker_logic import (
    apply_cached_result,
    apply_processing_result,
    map_ops_status_to_ui,
    mark_manually_edited,
)


def _make_item(source: str = "img.png", final: str = "img.png") -> RenameItem:
    return RenameItem(
        path=Path("/tmp") / source,
        source_name=source,
        final_name=final,
    )


def _make_result(
    status: OpsRenameStatus,
    *,
    proposed: str = "new-name.png",
    final: str = "new-name.png",
    cached: bool = False,
    reasoning: str = "some reasoning",
) -> ProcessingResult:
    return ProcessingResult(
        source="img.png",
        proposed=proposed,
        final=final,
        status=status,
        reasoning=reasoning,
        cached=cached,
    )


# ---------------------------------------------------------------------------
# map_ops_status_to_ui
# ---------------------------------------------------------------------------

def should_map_renamed_to_ready():
    assert map_ops_status_to_ui(OpsRenameStatus.RENAMED) == RenameStatus.READY


def should_map_unchanged_to_unchanged():
    assert map_ops_status_to_ui(OpsRenameStatus.UNCHANGED) == RenameStatus.UNCHANGED


def should_map_collision_to_collision():
    assert map_ops_status_to_ui(OpsRenameStatus.COLLISION) == RenameStatus.COLLISION


def should_map_error_to_error():
    assert map_ops_status_to_ui(OpsRenameStatus.ERROR) == RenameStatus.ERROR


def should_distinguish_unchanged_from_ready():
    assert map_ops_status_to_ui(OpsRenameStatus.UNCHANGED) != RenameStatus.READY


# ---------------------------------------------------------------------------
# mark_manually_edited
# ---------------------------------------------------------------------------

def should_set_ready_status_for_manually_edited_item():
    item = _make_item()
    stats = AnalysisStats()

    mark_manually_edited(item, stats)

    assert item.status == RenameStatus.READY
    assert item.status_message == "Ready (filename locked by user)"


def should_increment_renamed_for_manually_edited_item():
    item = _make_item()
    stats = AnalysisStats()

    mark_manually_edited(item, stats)

    assert stats.renamed == 1


# ---------------------------------------------------------------------------
# apply_processing_result
# ---------------------------------------------------------------------------

def should_copy_result_fields_onto_item():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.RENAMED, proposed="best.png", final="best.png", reasoning="good")

    apply_processing_result(item, result, stats)

    assert item.proposed_name == "best.png"
    assert item.final_name == "best.png"
    assert item.reasoning == "good"


def should_increment_cached_when_result_is_from_cache():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.RENAMED, cached=True)

    apply_processing_result(item, result, stats)

    assert item.cached is True
    assert stats.cached == 1


def should_set_ready_and_increment_renamed_for_renamed_status():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.RENAMED)

    apply_processing_result(item, result, stats)

    assert item.status == RenameStatus.READY
    assert stats.renamed == 1


def should_set_collision_and_increment_renamed_for_collision_status():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.COLLISION, final="new-name-2.png")

    apply_processing_result(item, result, stats)

    assert item.status == RenameStatus.COLLISION
    assert "new-name-2.png" in item.status_message
    assert stats.renamed == 1


def should_set_unchanged_and_increment_unchanged_for_unchanged_status():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.UNCHANGED)

    apply_processing_result(item, result, stats)

    assert item.status == RenameStatus.UNCHANGED
    assert stats.unchanged == 1


def should_set_error_and_increment_errors_for_error_status():
    item = _make_item()
    stats = AnalysisStats()
    result = _make_result(OpsRenameStatus.ERROR)

    apply_processing_result(item, result, stats)

    assert item.status == RenameStatus.ERROR
    assert stats.errors == 1


# ---------------------------------------------------------------------------
# apply_cached_result
# ---------------------------------------------------------------------------

def should_set_unchanged_cached_for_unchanged_status_not_manually_edited():
    item = _make_item()
    result = _make_result(OpsRenameStatus.UNCHANGED, final="img.png", reasoning="already good")

    apply_cached_result(item, result)

    assert item.status == RenameStatus.UNCHANGED
    assert item.status_message == "Already suitable (cached)"
    assert item.final_name == "img.png"
    assert item.cached is True
    assert item.reasoning == "already good"


def should_set_unchanged_locked_for_unchanged_status_manually_edited():
    item = _make_item()
    item.manually_edited = True
    original_final = item.final_name
    result = _make_result(OpsRenameStatus.UNCHANGED, final="img.png")

    apply_cached_result(item, result)

    assert item.status == RenameStatus.UNCHANGED
    assert item.status_message == "Already suitable (filename locked by user)"
    assert item.final_name == original_final


def should_set_ready_from_cache_for_non_unchanged_not_manually_edited():
    item = _make_item()
    result = _make_result(OpsRenameStatus.RENAMED, final="new-name.png")

    apply_cached_result(item, result)

    assert item.status == RenameStatus.READY
    assert item.status_message == "Ready (from cache)"
    assert item.final_name == "new-name.png"


def should_set_ready_locked_for_non_unchanged_manually_edited():
    item = _make_item()
    item.manually_edited = True
    original_final = item.final_name
    result = _make_result(OpsRenameStatus.RENAMED, final="new-name.png")

    apply_cached_result(item, result)

    assert item.status == RenameStatus.READY
    assert item.status_message == "Ready (filename locked by user)"
    assert item.final_name == original_final
