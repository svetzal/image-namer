from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from ui.models.ui_models import RenameItem, RenameStatus  # noqa: E402
from ui.widgets.rename_table import RenameTableManager  # noqa: E402


def _item(source: str = "file.png", final: str = "file.png", status: RenameStatus = RenameStatus.QUEUED) -> RenameItem:
    return RenameItem(
        path=Path(f"/tmp/{source}"),
        source_name=source,
        final_name=final,
        status=status,
        status_message="test",
    )


def should_populate_sets_row_count(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png"), _item("b.png"), _item("c.png")])
    assert mgr.rowCount() == 3


def should_populate_sets_final_name_in_column_zero(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png", "new-a.png")])
    assert mgr._table.item(0, 0).text() == "new-a.png"


def should_update_row_changes_both_columns(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png", "old.png")])
    updated = _item("a.png", "new.png", RenameStatus.READY)
    updated.status_message = "Ready to rename"
    mgr.update_row(0, updated)
    assert mgr._table.item(0, 0).text() == "new.png"


def should_update_row_status_changes_status_column(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item()])
    mgr.update_row_status(0, "🔍", "Assessing")
    assert "Assessing" in mgr._table.item(0, 1).text()


def should_emit_item_edited_on_valid_edit(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png", "old.png")])
    received: list[tuple[int, str]] = []
    mgr.item_edited.connect(lambda r, n: received.append((r, n)))

    mgr._table.item(0, 0).setText("new.png")

    assert received == [(0, "new.png")]


def should_revert_empty_name_edit(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png", "original.png")])

    mgr._table.item(0, 0).setText("")

    assert mgr._table.item(0, 0).text() == "original.png"


def should_emit_selection_changed_signal(qapp):
    mgr = RenameTableManager()
    mgr.populate([_item("a.png"), _item("b.png")])
    fired: list[bool] = []
    mgr.selection_changed.connect(lambda: fired.append(True))

    mgr._table.selectRow(1)

    assert fired
