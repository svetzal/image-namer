"""Tests for pure worker business logic in worker_logic.py."""

from pathlib import Path

from operations.models import ProcessingResult
from operations.models import RenameStatus
from ui import status_messages as msg
from ui.models.ui_models import ItemStatus, RenameItem
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
    status: RenameStatus,
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

def should_map_every_rename_status_to_ui():
    for status in RenameStatus:
        map_ops_status_to_ui(status)


def should_map_renamed_to_ready():
    assert map_ops_status_to_ui(RenameStatus.RENAMED) == ItemStatus.READY


def should_map_unchanged_to_unchanged():
    assert map_ops_status_to_ui(RenameStatus.UNCHANGED) == ItemStatus.UNCHANGED


def should_map_collision_to_collision():
    assert map_ops_status_to_ui(RenameStatus.COLLISION) == ItemStatus.COLLISION


def should_map_error_to_error():
    assert map_ops_status_to_ui(RenameStatus.ERROR) == ItemStatus.ERROR


def should_distinguish_unchanged_from_ready():
    assert map_ops_status_to_ui(RenameStatus.UNCHANGED) != ItemStatus.READY


# ---------------------------------------------------------------------------
# mark_manually_edited
# ---------------------------------------------------------------------------

def should_set_ready_status_for_manually_edited_item():
    item = _make_item()

    mark_manually_edited(item)

    assert item.status == ItemStatus.READY
    assert item.status_message == msg.READY_LOCKED


# ---------------------------------------------------------------------------
# apply_processing_result
# ---------------------------------------------------------------------------

def should_copy_result_fields_onto_item():
    item = _make_item()
    result = _make_result(RenameStatus.RENAMED, proposed="best.png", final="best.png", reasoning="good")

    apply_processing_result(item, result)

    assert item.proposed_name == "best.png"
    assert item.final_name == "best.png"
    assert item.reasoning == "good"


def should_mark_item_cached_when_result_is_from_cache():
    item = _make_item()
    result = _make_result(RenameStatus.RENAMED, cached=True)

    apply_processing_result(item, result)

    assert item.cached is True


def should_set_ready_for_renamed_status():
    item = _make_item()
    result = _make_result(RenameStatus.RENAMED)

    apply_processing_result(item, result)

    assert item.status == ItemStatus.READY


def should_set_collision_status_for_collision():
    item = _make_item()
    result = _make_result(RenameStatus.COLLISION, final="new-name-2.png")

    apply_processing_result(item, result)

    assert item.status == ItemStatus.COLLISION
    assert "new-name-2.png" in item.status_message


def should_set_unchanged_status_for_unchanged():
    item = _make_item()
    result = _make_result(RenameStatus.UNCHANGED)

    apply_processing_result(item, result)

    assert item.status == ItemStatus.UNCHANGED


def should_set_error_status_for_error():
    item = _make_item()
    result = _make_result(RenameStatus.ERROR)

    apply_processing_result(item, result)

    assert item.status == ItemStatus.ERROR


# ---------------------------------------------------------------------------
# apply_cached_result
# ---------------------------------------------------------------------------

def should_set_unchanged_cached_for_unchanged_status_not_manually_edited():
    item = _make_item()
    result = _make_result(RenameStatus.UNCHANGED, final="img.png", reasoning="already good")

    apply_cached_result(item, result)

    assert item.status == ItemStatus.UNCHANGED
    assert item.status_message == msg.ALREADY_SUITABLE_CACHED
    assert item.final_name == "img.png"
    assert item.cached is True
    assert item.reasoning == "already good"


def should_set_unchanged_locked_for_unchanged_status_manually_edited():
    item = _make_item()
    item.manually_edited = True
    original_final = item.final_name
    result = _make_result(RenameStatus.UNCHANGED, final="img.png")

    apply_cached_result(item, result)

    assert item.status == ItemStatus.UNCHANGED
    assert item.status_message == msg.ALREADY_SUITABLE_LOCKED
    assert item.final_name == original_final


def should_set_ready_from_cache_for_non_unchanged_not_manually_edited():
    item = _make_item()
    result = _make_result(RenameStatus.RENAMED, final="new-name.png")

    apply_cached_result(item, result)

    assert item.status == ItemStatus.READY
    assert item.status_message == msg.READY_FROM_CACHE
    assert item.final_name == "new-name.png"


def should_set_ready_locked_for_non_unchanged_manually_edited():
    item = _make_item()
    item.manually_edited = True
    original_final = item.final_name
    result = _make_result(RenameStatus.RENAMED, final="new-name.png")

    apply_cached_result(item, result)

    assert item.status == ItemStatus.READY
    assert item.status_message == msg.READY_LOCKED
    assert item.final_name == original_final
