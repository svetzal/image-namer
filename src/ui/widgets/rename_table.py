"""Rename table manager widget for Image Namer UI."""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ui.models.ui_models import RenameItem


class RenameTableManager(QWidget):
    """Widget that wraps a QTableWidget for displaying and editing rename items.

    Provides a clean API for populating and updating rows, and emits
    ``item_edited`` whenever the user commits a valid name change.
    ``selection_changed`` is forwarded from the underlying table.
    """

    item_edited: "Signal" = Signal(int, str)
    selection_changed: "Signal" = Signal()

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize the table manager."""
        super().__init__(parent)
        self._previous_final_names: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Final Name", "Status"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 400)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self.selection_changed.emit)
        self._table.itemChanged.connect(self._on_item_changed)

        layout.addWidget(self._table)

    def populate(self, items: list[RenameItem]) -> None:
        """Replace all table rows with the given items.

        Args:
            items: Items to display.
        """
        self._table.blockSignals(True)
        self._previous_final_names.clear()
        self._table.setRowCount(0)
        for item in items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(item.final_name))
            self._table.setItem(row, 1, self._status_item(item.status_icon, item.status_message))
            self._previous_final_names[row] = item.final_name
        self._table.blockSignals(False)

    def update_row(self, row: int, item: RenameItem) -> None:
        """Update both columns of a row from a RenameItem.

        Args:
            row: Table row index.
            item: Updated item.
        """
        self._table.blockSignals(True)
        self._table.setItem(row, 0, QTableWidgetItem(item.final_name))
        self._table.setItem(row, 1, self._status_item(item.status_icon, item.status_message))
        self._previous_final_names[row] = item.final_name
        self._table.blockSignals(False)

    def update_row_status(self, row: int, icon: str, message: str) -> None:
        """Update only the status column of a row.

        Args:
            row: Table row index.
            icon: Status icon emoji.
            message: Status message text.
        """
        self._table.blockSignals(True)
        self._table.setItem(row, 1, self._status_item(icon, message))
        self._table.blockSignals(False)

    def select_row(self, row: int) -> None:
        """Select a row programmatically.

        Args:
            row: Row index to select.
        """
        self._table.selectRow(row)

    def selectionModel(self) -> Any:
        """Return the underlying table's selection model."""
        return self._table.selectionModel()

    def rowCount(self) -> int:
        """Return the number of rows in the table."""
        return int(self._table.rowCount())

    @staticmethod
    def _status_item(icon: str, message: str) -> QTableWidgetItem:
        item = QTableWidgetItem(f"{icon} {message}")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        row = item.row()
        col = item.column()

        if col != 0:
            return

        new_name = item.text().strip()

        if not new_name:
            self._table.itemChanged.disconnect(self._on_item_changed)
            item.setText(self._previous_final_names.get(row, ""))
            self._table.itemChanged.connect(self._on_item_changed)
            return

        self._previous_final_names[row] = new_name
        self.item_edited.emit(row, new_name)
