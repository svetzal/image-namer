"""Tests for perform_batch_rename in rename_actions."""

from pathlib import Path

from ui.models.ui_models import RenameItem, RenameStatus
from ui.rename_actions import perform_batch_rename


def _make_item(tmp_path: Path, source: str = "old.png", final: str = "new.png") -> RenameItem:
    path = tmp_path / source
    path.touch()
    return RenameItem(
        path=path,
        source_name=source,
        final_name=final,
        status=RenameStatus.READY,
        status_message="Ready",
    )


def should_return_zero_counts_when_nothing_to_rename(tmp_path):
    item = _make_item(tmp_path, "same.png", "same.png")
    result = perform_batch_rename([item], tmp_path, update_refs=False, recursive=False)
    assert result.renamed_count == 0
    assert result.error_count == 0
    assert result.total_refs_updated == 0


def should_rename_item_and_update_status(tmp_path, mocker):
    item = _make_item(tmp_path, "old.png", "new.png")
    mocker.patch("ui.rename_actions.perform_rename_with_refs", return_value=0)

    result = perform_batch_rename([item], tmp_path, update_refs=False, recursive=False)

    assert result.renamed_count == 1
    assert result.error_count == 0
    assert item.status == RenameStatus.COMPLETED
    assert item.source_name == "new.png"


def should_count_references_updated(tmp_path, mocker):
    item = _make_item(tmp_path, "a.png", "b.png")
    mocker.patch("ui.rename_actions.perform_rename_with_refs", return_value=3)

    result = perform_batch_rename([item], tmp_path, update_refs=True, recursive=False)

    assert result.total_refs_updated == 3


def should_record_error_on_rename_failure(tmp_path, mocker):
    item = _make_item(tmp_path, "old.png", "new.png")
    mocker.patch("ui.rename_actions.perform_rename_with_refs", side_effect=OSError("disk full"))

    result = perform_batch_rename([item], tmp_path, update_refs=False, recursive=False)

    assert result.renamed_count == 0
    assert result.error_count == 1
    assert item.status == RenameStatus.ERROR
    assert "disk full" in (item.error_message or "")


def should_handle_multiple_items(tmp_path, mocker):
    item_a = _make_item(tmp_path, "a.png", "a-new.png")
    item_b = _make_item(tmp_path, "b.png", "b-new.png")
    mocker.patch("ui.rename_actions.perform_rename_with_refs", return_value=1)

    result = perform_batch_rename([item_a, item_b], tmp_path, update_refs=True, recursive=False)

    assert result.renamed_count == 2
    assert result.total_refs_updated == 2
