"""Bottom control panel widget with progress bar, status label, and action buttons."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class BottomControlPanel(QWidget):
    """Bottom panel owning progress bar, status label, and all action buttons.

    Exposes signals for button clicks; callers update display state via methods.
    """

    select_folder_clicked: "Signal" = Signal()
    refresh_clicked: "Signal" = Signal()
    preview_clicked: "Signal" = Signal()
    stop_clicked: "Signal" = Signal()
    apply_clicked: "Signal" = Signal()
    single_rename_clicked: "Signal" = Signal()

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize panel with progress bar, status label, and buttons."""
        super().__init__(parent)
        self.setMaximumHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        progress_layout = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Ready to process images")
        progress_layout.addWidget(self._status_label)
        layout.addLayout(progress_layout)

        button_layout = QHBoxLayout()

        self._select_folder_btn = QPushButton("📁 Open Folder")
        self._select_folder_btn.clicked.connect(self.select_folder_clicked)
        button_layout.addWidget(self._select_folder_btn)

        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.clicked.connect(self.refresh_clicked)
        button_layout.addWidget(self._refresh_btn)

        self._preview_btn = QPushButton("Analyze All")
        self._preview_btn.setEnabled(False)
        self._preview_btn.clicked.connect(self.preview_clicked)
        button_layout.addWidget(self._preview_btn)

        self._stop_btn = QPushButton("⏹ Stop")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self.stop_clicked)
        button_layout.addWidget(self._stop_btn)

        self._apply_btn = QPushButton("Analyze and Rename All")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self.apply_clicked)
        button_layout.addWidget(self._apply_btn)

        button_layout.addStretch()

        self._single_rename_btn = QPushButton("Rename")
        self._single_rename_btn.setEnabled(False)
        self._single_rename_btn.clicked.connect(self.single_rename_clicked)
        button_layout.addWidget(self._single_rename_btn)

        layout.addLayout(button_layout)

    def set_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)

    def set_status_text(self, msg: str) -> None:
        """Update status label."""
        self._status_label.setText(msg)

    def set_processing_state(self, processing: bool) -> None:
        """Toggle between idle (processing=False) and analyzing (processing=True) mode."""
        self._preview_btn.setEnabled(not processing)
        self._preview_btn.setVisible(not processing)
        self._stop_btn.setEnabled(processing)
        self._stop_btn.setVisible(processing)
        self._select_folder_btn.setEnabled(not processing)
        self._refresh_btn.setEnabled(not processing)

    def set_folder_loaded(self, enabled: bool) -> None:
        """Enable or disable the refresh and analyze buttons."""
        self._refresh_btn.setEnabled(enabled)
        self._preview_btn.setEnabled(enabled)

    def set_apply_enabled(self, enabled: bool) -> None:
        """Enable or disable the batch rename button."""
        self._apply_btn.setEnabled(enabled)

    def set_stop_enabled(self, enabled: bool) -> None:
        """Enable or disable the stop button."""
        self._stop_btn.setEnabled(enabled)

    def update_rename_button(self, old_name: str | None, new_name: str | None) -> None:
        """Update single-rename button label and enabled state.

        Enables the button with a descriptive label when old_name differs from new_name.
        Disables it with a generic label otherwise.
        """
        if not old_name or not new_name or old_name == new_name:
            self._single_rename_btn.setText("Rename")
            self._single_rename_btn.setEnabled(False)
        else:
            self._single_rename_btn.setText(f"Rename {old_name} to {new_name}")
            self._single_rename_btn.setEnabled(True)
