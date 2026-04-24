"""Metadata detail panel widget for Image Namer UI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

from ui.models.ui_models import RenameItem, RenameStatus


class MetadataPanel(QWidget):
    """Panel that displays detailed metadata for a selected RenameItem.

    Exposes ``update(item)`` and ``clear()``; all label widgets are internal.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize metadata panel."""
        super().__init__(parent)
        self.setMaximumHeight(200)

        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(QLabel("<b>Source:</b>"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self._meta_source = QLabel("(none)")
        self._meta_source.setWordWrap(True)
        layout.addWidget(self._meta_source, 0, 1)

        layout.addWidget(QLabel("<b>Current Suitable:</b>"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self._meta_suitable = QLabel("(none)")
        layout.addWidget(self._meta_suitable, 1, 1)

        layout.addWidget(QLabel("<b>Cached:</b>"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self._meta_cached = QLabel("(none)")
        layout.addWidget(self._meta_cached, 2, 1)

        layout.addWidget(QLabel("<b>Proposed:</b>"), 0, 2, Qt.AlignmentFlag.AlignRight)
        self._meta_proposed = QLabel("(none)")
        self._meta_proposed.setWordWrap(True)
        layout.addWidget(self._meta_proposed, 0, 3)

        layout.addWidget(QLabel("<b>Final:</b>"), 1, 2, Qt.AlignmentFlag.AlignRight)
        self._meta_final = QLabel("(none)")
        self._meta_final.setWordWrap(True)
        layout.addWidget(self._meta_final, 1, 3)

        layout.addWidget(QLabel("<b>Manually Edited:</b>"), 2, 2, Qt.AlignmentFlag.AlignRight)
        self._meta_edited = QLabel("(none)")
        layout.addWidget(self._meta_edited, 2, 3)

        layout.addWidget(
            QLabel("<b>Reasoning:</b>"),
            3, 0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        self._meta_reasoning = QLabel("(none)")
        self._meta_reasoning.setWordWrap(True)
        self._meta_reasoning.setMaximumHeight(60)
        layout.addWidget(self._meta_reasoning, 3, 1, 1, 3)

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

    def update(self, item: RenameItem) -> None:
        """Populate all fields from a RenameItem.

        Args:
            item: The item whose metadata to display.
        """
        self._meta_source.setText(item.source_name)

        if item.status == RenameStatus.UNCHANGED:
            self._meta_suitable.setText("Yes ✓")
        elif item.status in (RenameStatus.READY, RenameStatus.COLLISION):
            self._meta_suitable.setText("No")
        else:
            self._meta_suitable.setText("(pending)")

        self._meta_cached.setText("Yes 💾" if item.cached else "No")
        self._meta_proposed.setText(item.proposed_name if item.proposed_name else "(not yet generated)")
        self._meta_final.setText(item.final_name if item.final_name else item.source_name)
        self._meta_edited.setText("Yes 🔒" if item.manually_edited else "No")
        self._meta_reasoning.setText(item.reasoning if item.reasoning else "(not yet processed)")

    def clear(self) -> None:
        """Reset all fields to placeholder text."""
        for label in (
            self._meta_source,
            self._meta_suitable,
            self._meta_cached,
            self._meta_proposed,
            self._meta_final,
            self._meta_edited,
            self._meta_reasoning,
        ):
            label.setText("(none)")
