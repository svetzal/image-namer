"""Main window for Image Namer UI.

Contains the primary application layout with table, toolbar, and controls.
"""

import os
from pathlib import Path

from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from operations.find_references import find_references
from operations.update_references import update_references
from ui.models.ui_models import RenameItem, RenameStatus
from ui.settings import get_setting, set_setting
from ui.workers.cache_loader import CacheLoaderWorker
from ui.workers.rename_worker import RenameWorker
from utils.fs import ensure_cache_layout


class ResizableImageLabel(QLabel):
    """QLabel subclass that emits signal when resized."""

    def __init__(self, parent=None):
        """Initialize resizable image label."""
        super().__init__(parent)
        self.main_window = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize event to rescale image.

        Args:
            event: Resize event.
        """
        super().resizeEvent(event)
        if self.main_window:
            self.main_window._rescale_current_image()


class MainWindow(QMainWindow):
    """Main application window for Image Namer.

    Layout:
    - Toolbar: Provider/model selectors
    - Center: Splitter with preview panel (left) and results table (right)
    - Bottom: Progress bar, status label, action buttons
    """

    # Supported image extensions (from main.py)
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}

    def __init__(self) -> None:
        """Initialize main window with layout and widgets."""
        super().__init__()

        self.setWindowTitle("Image Namer")
        self.resize(1200, 800)

        # Store state
        self.current_folder: Path | None = None
        self.rename_items: list[RenameItem] = []
        self.worker: RenameWorker | None = None
        self.cache_loader: CacheLoaderWorker | None = None  # Background cache loader
        self.current_pixmap: QPixmap | None = None  # Store original pixmap for rescaling
        self.resize_timer: QTimer | None = None  # Debounce resize events
        self.recursive_scan: bool = True  # Whether to scan subdirectories (default ON)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add toolbar
        self._create_toolbar()

        # Create splitter for preview + (table + metadata)
        # This will take all available vertical space (stretch=1)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)  # Make the divider handle more visible

        # Left: Preview panel
        self.preview_panel = self._create_preview_panel()
        splitter.addWidget(self.preview_panel)

        # Right: Container for table + metadata panel
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Table takes all available space
        self.results_table = self._create_results_table()
        right_layout.addWidget(self.results_table, stretch=1)

        # Metadata panel at bottom (fixed height)
        self.metadata_panel = self._create_metadata_panel()
        right_layout.addWidget(self.metadata_panel, stretch=0)

        splitter.addWidget(right_container)

        # Set splitter proportions (40% preview, 60% table+metadata for larger image view)
        # User can drag to adjust as needed
        splitter.setSizes([480, 720])

        # Allow collapsing, but set reasonable minimums
        splitter.setCollapsible(0, False)  # Don't allow preview to fully collapse
        splitter.setCollapsible(1, False)  # Don't allow table to fully collapse

        # Add splitter with stretch=1 to take all available vertical space
        main_layout.addWidget(splitter, stretch=1)

        # Bottom: Progress and controls (fixed height, stretch=0)
        self._create_bottom_panel(main_layout)

        # Menu bar
        self._create_menu_bar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def closeEvent(self, event) -> None:
        """Handle window close - stop workers if running.

        Args:
            event: Close event.
        """
        # Stop main worker
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait()

        # Stop cache loader
        if self.cache_loader and self.cache_loader.isRunning():
            self.cache_loader.stop()
            if not self.cache_loader.wait(1000):
                self.cache_loader.terminate()
                self.cache_loader.wait()

        event.accept()

    def _create_menu_bar(self) -> None:
        """Create menu bar with File, Edit, View, Help menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_folder_action = file_menu.addAction("&Open Folder...")
        open_folder_action.setShortcut("Ctrl+O")
        open_folder_action.triggered.connect(self._on_select_folder)

        file_menu.addSeparator()

        clear_cache_action = file_menu.addAction("Clear Cache...")
        clear_cache_action.triggered.connect(self._on_clear_cache)

        file_menu.addSeparator()

        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

    def _create_toolbar(self) -> None:
        """Create toolbar with provider/model selectors."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Load saved settings
        saved_provider = get_setting("provider", "ollama")

        # Provider selector
        toolbar.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "openai"])
        self.provider_combo.setCurrentText(saved_provider)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        toolbar.addWidget(self.provider_combo)
        toolbar.addSeparator()

        # Model selector
        toolbar.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self._update_model_list()

        # Load and set the saved model for current provider
        self._restore_model_for_provider(saved_provider)

        # Connect model change to save settings
        self.model_combo.currentTextChanged.connect(self._on_model_changed)

        toolbar.addWidget(self.model_combo)
        toolbar.addSeparator()

        # Recursive checkbox
        toolbar.addSeparator()
        self.recursive_checkbox = QCheckBox("Include subdirectories")
        self.recursive_checkbox.setChecked(True)  # Default ON
        self.recursive_checkbox.setToolTip("Scan subdirectories recursively when selecting a folder")
        self.recursive_checkbox.stateChanged.connect(self._on_recursive_changed)
        toolbar.addWidget(self.recursive_checkbox)

        # Update references checkbox
        toolbar.addSeparator()
        self.update_refs_checkbox = QCheckBox("Update references")
        self.update_refs_checkbox.setChecked(True)  # Default ON
        self.update_refs_checkbox.setToolTip("Update markdown references when renaming files")
        toolbar.addWidget(self.update_refs_checkbox)

    def _create_preview_panel(self) -> QWidget:
        """Create left preview panel.

        Returns:
            Widget containing image preview.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)

        # Image preview label (will hold scaled pixmap)
        # Use custom ResizableImageLabel to handle resize events
        self.preview_label = ResizableImageLabel()
        self.preview_label.main_window = self  # Connect back to main window for rescaling
        self.preview_label.setText("No image selected")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # No background color set - uses default window background
        self.preview_label.setMinimumSize(200, 200)  # Minimum size to prevent collapse
        self.preview_label.setScaledContents(False)

        layout.addWidget(self.preview_label, stretch=1)  # Stretch=1 means take all available space

        # Filename label (fixed height at bottom)
        self.preview_filename_label = QLabel("Selected: (none)")
        self.preview_filename_label.setWordWrap(True)
        self.preview_filename_label.setMaximumHeight(50)  # Fixed height for filename
        layout.addWidget(self.preview_filename_label, stretch=0)  # No stretch, fixed size

        return panel

    def _create_results_table(self) -> QTableWidget:
        """Create results table.

        Returns:
            Table widget with columns for Final and Status.
        """
        table = QTableWidget(0, 2)  # 0 rows, 2 columns
        table.setHorizontalHeaderLabels(["Final Name", "Status"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 400)  # Final name gets more space
        # Status column stretches

        # Allow editing via double-click only
        table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)

        # Enable row selection (single row at a time)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Connect selection change to preview update
        table.itemSelectionChanged.connect(self._on_table_selection_changed)

        # Connect item changed signal to handle manual edits
        table.itemChanged.connect(self._on_table_item_changed)

        return table

    def _create_metadata_panel(self) -> QWidget:
        """Create metadata panel to display detailed info about selected image.

        Returns:
            Widget containing metadata display in 2-column grid layout.
        """
        panel = QWidget()
        panel.setMaximumHeight(200)  # Fixed height, sized to content
        layout = QGridLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Create labels for metadata fields (2 columns)
        # Column 1: Source info
        layout.addWidget(QLabel("<b>Source:</b>"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.meta_source = QLabel("(none)")
        self.meta_source.setWordWrap(True)
        layout.addWidget(self.meta_source, 0, 1)

        layout.addWidget(QLabel("<b>Current Suitable:</b>"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.meta_suitable = QLabel("(none)")
        layout.addWidget(self.meta_suitable, 1, 1)

        layout.addWidget(QLabel("<b>Cached:</b>"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.meta_cached = QLabel("(none)")
        layout.addWidget(self.meta_cached, 2, 1)

        # Column 2: Proposed/Final info
        layout.addWidget(QLabel("<b>Proposed:</b>"), 0, 2, Qt.AlignmentFlag.AlignRight)
        self.meta_proposed = QLabel("(none)")
        self.meta_proposed.setWordWrap(True)
        layout.addWidget(self.meta_proposed, 0, 3)

        layout.addWidget(QLabel("<b>Final:</b>"), 1, 2, Qt.AlignmentFlag.AlignRight)
        self.meta_final = QLabel("(none)")
        self.meta_final.setWordWrap(True)
        layout.addWidget(self.meta_final, 1, 3)

        layout.addWidget(QLabel("<b>Manually Edited:</b>"), 2, 2, Qt.AlignmentFlag.AlignRight)
        self.meta_edited = QLabel("(none)")
        layout.addWidget(self.meta_edited, 2, 3)

        # Reasoning (spans full width)
        layout.addWidget(QLabel("<b>Reasoning:</b>"), 3, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.meta_reasoning = QLabel("(none)")
        self.meta_reasoning.setWordWrap(True)
        self.meta_reasoning.setMaximumHeight(60)
        layout.addWidget(self.meta_reasoning, 3, 1, 1, 3)  # Span columns 1-3

        # Set column stretches to make effective use of space
        layout.setColumnStretch(1, 1)  # Source column data stretches
        layout.setColumnStretch(3, 1)  # Proposed/Final column data stretches

        return panel

    def _create_bottom_panel(self, parent_layout: QVBoxLayout) -> None:
        """Create bottom panel with progress and action buttons.

        Args:
            parent_layout: Layout to add bottom panel to.
        """
        # Create container widget with fixed height for bottom controls
        bottom_widget = QWidget()
        bottom_widget.setMaximumHeight(100)  # Fixed maximum height
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(5, 5, 5, 5)

        # Progress bar and status
        progress_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to process images")
        progress_layout.addWidget(self.status_label)

        bottom_layout.addLayout(progress_layout)

        # Action buttons
        button_layout = QHBoxLayout()

        # Left group: bulk operations
        self.select_folder_btn = QPushButton("📁 Open Folder")
        self.select_folder_btn.clicked.connect(self._on_select_folder)
        button_layout.addWidget(self.select_folder_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        button_layout.addWidget(self.refresh_btn)

        self.preview_btn = QPushButton("Analyze All")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        button_layout.addWidget(self.preview_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)  # Hidden until processing starts
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        button_layout.addWidget(self.stop_btn)

        self.apply_btn = QPushButton("Analyze and Rename All")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._on_apply_clicked)
        button_layout.addWidget(self.apply_btn)

        # Middle stretch to push right-aligned single-item actions to the edge
        button_layout.addStretch()

        # Right group: single-item operation
        self.single_rename_btn = QPushButton("Rename")
        self.single_rename_btn.setEnabled(False)
        self.single_rename_btn.clicked.connect(self._on_single_rename_clicked)
        button_layout.addWidget(self.single_rename_btn)

        bottom_layout.addLayout(button_layout)

        # Add bottom widget with no stretch (stays fixed height)
        parent_layout.addWidget(bottom_widget, stretch=0)

    def _update_single_rename_button_label(self) -> None:
        """Update the right-aligned single-rename button label and enabled state.

        The button shows: "Rename [old name] to [new name]" when a single row is
        selected and the final name differs from the current source name. Otherwise,
        the button is disabled with a generic label.
        """
        # Default state
        self.single_rename_btn.setText("Rename")
        self.single_rename_btn.setEnabled(False)

        # Ensure a table and items exist
        if not hasattr(self, "results_table") or not self.rename_items:
            return

        selection_model = self.results_table.selectionModel()
        if not selection_model:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.rename_items):
            return

        item = self.rename_items[row]
        old_name = item.source_name
        new_name = item.final_name or item.source_name

        if not old_name or not new_name or old_name == new_name:
            # Nothing to do
            return

        # Update label and enable
        self.single_rename_btn.setText(f"Rename {old_name} to {new_name}")
        self.single_rename_btn.setEnabled(True)

    def _update_model_list(self) -> None:
        """Update model combo box based on selected provider.

        Dynamically fetches available models from the gateway.
        """
        provider = self.provider_combo.currentText() if hasattr(self, 'provider_combo') else "ollama"

        # Block signals during list update to prevent spurious saves
        self.model_combo.blockSignals(True)
        try:
            self.model_combo.clear()

            # Default models (used as fallback if gateway call fails)
            default_models = {
                "ollama": ["gemma3:27b"],
                "openai": ["gpt-4o"]
            }

            try:
                # Create gateway and fetch available models
                if provider == "ollama":
                    gateway = OllamaGateway()
                else:  # openai
                    api_key = os.environ.get("OPENAI_API_KEY")
                    if not api_key:
                        # Can't query without API key, use defaults
                        self.model_combo.addItems(default_models[provider])
                        return
                    gateway = OpenAIGateway(api_key=api_key)

                # Get available models from gateway
                models = gateway.get_available_models()

                if models:
                    self.model_combo.addItems(models)
                else:
                    # No models returned, use defaults
                    self.model_combo.addItems(default_models[provider])

            except Exception as e:
                # Error fetching models, use defaults
                self.status_bar.showMessage(f"Could not fetch models: {e}", 5000)
                self.model_combo.addItems(default_models[provider])
        finally:
            self.model_combo.blockSignals(False)

    def _restore_model_for_provider(self, provider: str) -> None:
        """Restore the last used model for the given provider.

        Args:
            provider: Provider name (ollama or openai).
        """
        # Get saved model for this provider
        saved_model = get_setting(f"model_{provider}")

        if saved_model:
            # Temporarily block signals to prevent triggering _on_model_changed during restoration
            self.model_combo.blockSignals(True)
            try:
                index = self.model_combo.findText(saved_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
            finally:
                self.model_combo.blockSignals(False)

    def _on_provider_changed(self, provider: str) -> None:
        """Handle provider selection change.

        Args:
            provider: Selected provider name.
        """
        # Save provider preference
        set_setting("provider", provider)

        self._update_model_list()

        # Restore the last used model for this provider
        self._restore_model_for_provider(provider)

        # Validate provider availability
        if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
            self.status_bar.showMessage(
                "⚠️ Warning: OPENAI_API_KEY not set in environment", 5000
            )

    def _on_model_changed(self, model: str) -> None:
        """Handle model selection change.

        Args:
            model: Selected model name.
        """
        # Save model preference for current provider
        if model:
            provider = self.provider_combo.currentText()
            set_setting(f"model_{provider}", model)

    def _on_table_selection_changed(self) -> None:
        """Handle table selection change to update preview and metadata."""
        selected_rows = self.results_table.selectionModel().selectedRows()

        if not selected_rows or not self.rename_items:
            self.preview_label.setText("No image selected")
            self.preview_filename_label.setText("Selected: (none)")
            self._clear_metadata_panel()
            # Update single-rename button state
            self._update_single_rename_button_label()
            return

        # Get selected row index
        row = selected_rows[0].row()

        if row >= len(self.rename_items):
            return

        # Get corresponding RenameItem
        item = self.rename_items[row]

        # Update filename label
        self.preview_filename_label.setText(f"Selected: {item.source_name}")

        # Update metadata panel
        self._update_metadata_panel(item)

        # Load and display image
        try:
            pixmap = QPixmap(str(item.path))

            if pixmap.isNull():
                self.preview_label.setText(f"Failed to load:\n{item.source_name}")
                self.current_pixmap = None
                # Update single-rename button state
                self._update_single_rename_button_label()
                return

            # Store original pixmap for rescaling on resize
            self.current_pixmap = pixmap

            # Scale and display
            self._rescale_current_image()

        except Exception as e:
            self.preview_label.setText(f"Error loading image:\n{e}")
            self.current_pixmap = None
        finally:
            # Update single-rename button state/label after selection changes
            self._update_single_rename_button_label()

    def _rescale_current_image(self) -> None:
        """Rescale the current image to fit the preview label's current size."""
        if not self.current_pixmap:
            return

        # Get available space in preview label
        available_size = self.preview_label.size()
        max_width = max(available_size.width() - 20, 200)  # Leave some padding
        max_height = max(available_size.height() - 20, 200)

        # Scale original pixmap to fit current size
        scaled_pixmap = self.current_pixmap.scaled(
            max_width, max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.preview_label.setPixmap(scaled_pixmap)

    def _update_metadata_panel(self, item: RenameItem) -> None:
        """Update metadata panel with information from RenameItem.

        Args:
            item: The RenameItem to display metadata for.
        """
        # Source info
        self.meta_source.setText(item.source_name)

        # Current name suitable (will be shown when we have analysis data)
        # For now, show based on status
        if item.status == RenameStatus.UNCHANGED:
            self.meta_suitable.setText("Yes ✓")
        elif item.status in (RenameStatus.READY, RenameStatus.COLLISION):
            self.meta_suitable.setText("No")
        else:
            self.meta_suitable.setText("(pending)")

        # Cached status
        self.meta_cached.setText("Yes 💾" if item.cached else "No")

        # Proposed name
        self.meta_proposed.setText(item.proposed_name if item.proposed_name else "(not yet generated)")

        # Final name
        self.meta_final.setText(item.final_name if item.final_name else item.source_name)

        # Manually edited
        self.meta_edited.setText("Yes 🔒" if item.manually_edited else "No")

        # Reasoning from LLM
        if item.reasoning:
            self.meta_reasoning.setText(item.reasoning)
        else:
            self.meta_reasoning.setText("(not yet processed)")

    def _clear_metadata_panel(self) -> None:
        """Clear all metadata panel fields."""
        self.meta_source.setText("(none)")
        self.meta_suitable.setText("(none)")
        self.meta_cached.setText("(none)")
        self.meta_proposed.setText("(none)")
        self.meta_final.setText("(none)")
        self.meta_edited.setText("(none)")
        self.meta_reasoning.setText("(none)")

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle manual edits to table items.

        Only allows editing the Final column (column 0). Reverts edits to other columns.
        Updates the corresponding RenameItem's final_name.

        Args:
            item: The table item that was changed.
        """
        row = item.row()
        col = item.column()

        # Only allow editing column 0 (Final)
        if col != 0:
            # Revert the edit by temporarily disconnecting signal
            self.results_table.itemChanged.disconnect(self._on_table_item_changed)

            # Restore original value
            if row < len(self.rename_items):
                rename_item = self.rename_items[row]
                if col == 1:
                    # Status column - restore
                    item.setText(f"{rename_item.status_icon} {rename_item.status_message}")

            # Reconnect signal
            self.results_table.itemChanged.connect(self._on_table_item_changed)
            return

        # Column 0 (Final) - update RenameItem
        if row < len(self.rename_items):
            new_final_name = item.text().strip()

            # Validate filename
            if not new_final_name:
                # Revert to previous value
                self.results_table.itemChanged.disconnect(self._on_table_item_changed)
                item.setText(self.rename_items[row].final_name)
                self.results_table.itemChanged.connect(self._on_table_item_changed)
                self.status_bar.showMessage("Final filename cannot be empty", 3000)
                return

            # Update the RenameItem and mark as manually edited
            self.rename_items[row].final_name = new_final_name
            self.rename_items[row].manually_edited = True
            self.status_bar.showMessage(f"Updated final name for row {row + 1} (locked)", 2000)

            # Update single-rename button label/state as the final name changed
            self._update_single_rename_button_label()

    def _on_recursive_changed(self, state: int) -> None:
        """Handle recursive checkbox change.

        Args:
            state: Checkbox state (Qt.CheckState).
        """
        self.recursive_scan = (state == Qt.CheckState.Checked.value)

        # If folder is already loaded, offer to re-scan
        if self.current_folder:
            mode = "recursive" if self.recursive_scan else "flat"
            self.status_bar.showMessage(
                f"Recursive mode {'enabled' if self.recursive_scan else 'disabled'}. "
                f"Click Refresh to re-scan in {mode} mode.",
                5000
            )

    def _on_clear_cache(self) -> None:
        """Handle Clear Cache menu action."""
        # Find cache directory
        if self.current_folder:
            cache_root = ensure_cache_layout(self.current_folder)
        else:
            cache_root = ensure_cache_layout(Path.cwd())

        cache_dir = cache_root / "cache"

        if not cache_dir.exists():
            QMessageBox.information(
                self,
                "No Cache Found",
                "No cache directory found for this location."
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            f"This will delete all cached LLM results in:\n{cache_dir}\n\n"
            "This includes:\n"
            "- Unified analysis cache (current format)\n"
            "- Legacy assessment and naming caches (old format)\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete cache contents
            import shutil
            try:
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True)  # Recreate empty cache dir
                QMessageBox.information(
                    self,
                    "Cache Cleared",
                    "Cache cleared successfully!"
                )
                self.status_bar.showMessage("Cache cleared", 3000)

                # Refresh the view if a folder is currently loaded
                if self.current_folder:
                    self._on_refresh_clicked()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear cache: {e}"
                )

    def _on_select_folder(self) -> None:
        """Handle Select Folder button click."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder:
            return

        self.current_folder = Path(folder)
        self._scan_folder()

    def _on_refresh_clicked(self) -> None:
        """Handle Refresh button click - re-scan current folder."""
        if not self.current_folder:
            return

        # Clear current selection and pixmap
        self.current_pixmap = None
        self.preview_label.setText("No image selected")
        self.preview_filename_label.setText("Selected: (none)")

        # Re-scan with current recursive setting
        self._scan_folder()

        mode = "recursively" if self.recursive_scan else "in folder only"
        self.status_bar.showMessage(f"Refreshed {mode}", 3000)

    def _scan_folder(self) -> None:
        """Scan current folder for image files and populate table."""
        if not self.current_folder:
            return

        # Collect image files (reuse logic from main.py _collect_image_files)
        if self.recursive_scan:
            # Recursive scan - search all subdirectories
            image_files = sorted([
                p for p in self.current_folder.rglob("*")
                if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ])
        else:
            # Flat scan - current directory only
            image_files = sorted([
                p for p in self.current_folder.iterdir()
                if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ])

        if not image_files:
            self.status_bar.showMessage(
                f"No supported images found in {self.current_folder.name}", 5000
            )
            return

        # Create RenameItem objects
        self.rename_items = [
            RenameItem(
                path=img_path,
                source_name=img_path.name,
                final_name=img_path.name,
                status=RenameStatus.QUEUED,
                status_message="Waiting in queue..."
            )
            for img_path in image_files
        ]

        # Populate table
        self._populate_table()

        # Enable buttons
        self.refresh_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        # Show scan results
        mode = "recursively" if self.recursive_scan else ""
        self.status_bar.showMessage(
            f"Loaded {len(image_files)} image(s) from {self.current_folder.name} {mode}".strip()
        )

        # Start background cache loader to populate cached data
        self._start_cache_loader()

    def _populate_table(self) -> None:
        """Populate table with rename items."""
        # Block signals during programmatic updates
        self.results_table.blockSignals(True)

        self.results_table.setRowCount(0)  # Clear existing rows

        for item in self.rename_items:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)

            # Column 0: Final name
            self.results_table.setItem(row, 0, QTableWidgetItem(item.final_name))

            # Column 1: Status
            status_text = f"{item.status_icon} {item.status_message}"
            self.results_table.setItem(row, 1, QTableWidgetItem(status_text))

        # Unblock signals
        self.results_table.blockSignals(False)

        # Update progress
        self.progress_bar.setMaximum(len(self.rename_items))
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Ready to process {len(self.rename_items)} images")

        # Update single-rename button state after repopulating
        self._update_single_rename_button_label()

    def _start_cache_loader(self) -> None:
        """Start background cache loader to populate table with cached data."""
        if not self.rename_items or not self.current_folder:
            return

        # Get provider and model
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()

        # Setup cache
        cache_root = ensure_cache_layout(self.current_folder)

        # Create and start cache loader
        self.cache_loader = CacheLoaderWorker(
            items=self.rename_items,
            cache_root=cache_root,
            provider=provider,
            model=model,
        )

        # Connect signals
        self.cache_loader.item_cache_loaded.connect(self._on_cache_item_loaded)
        self.cache_loader.finished.connect(self._on_cache_loading_finished)

        # Start background loading
        self.cache_loader.start()
        self.status_label.setText("Loading cached data...")

    def _on_cache_item_loaded(self, row: int, item: RenameItem) -> None:
        """Handle cache loader finding cached data for an item.

        Args:
            row: Row index in table.
            item: Updated RenameItem with cache data.
        """
        # Update rename_items list
        if row < len(self.rename_items):
            self.rename_items[row] = item

        # Update table row WITHOUT selecting it
        if row < self.results_table.rowCount():
            # Block signals during programmatic update
            self.results_table.blockSignals(True)

            # Column 0: Final name
            self.results_table.setItem(row, 0, QTableWidgetItem(item.final_name))

            # Column 1: Status
            status_text = f"{item.status_icon} {item.status_message}"
            self.results_table.setItem(row, 1, QTableWidgetItem(status_text))

            # Unblock signals
            self.results_table.blockSignals(False)

    def _on_cache_loading_finished(self, cached_count: int, total_count: int) -> None:
        """Handle cache loader finishing.

        Args:
            cached_count: Number of items found in cache.
            total_count: Total items checked.
        """
        if cached_count > 0:
            self.status_label.setText(
                f"Loaded {cached_count}/{total_count} from cache - Ready to process remaining"
            )
            self.status_bar.showMessage(
                f"{cached_count} of {total_count} already in cache", 3000
            )
        else:
            self.status_label.setText(f"Ready to process {total_count} images")

    def _on_preview_clicked(self) -> None:
        """Handle Preview button click - start LLM processing."""
        if not self.rename_items:
            return

        # Get provider and model
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText()

        # Validate provider
        if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
            self.status_bar.showMessage(
                "Error: OPENAI_API_KEY not set. Please configure in environment.", 5000
            )
            return

        # Setup cache
        cache_root = ensure_cache_layout(
            self.current_folder if self.current_folder else Path.cwd()
        )

        # Create LLM gateway and broker
        try:
            if provider == "ollama":
                gateway = OllamaGateway()
            else:
                gateway = OpenAIGateway(api_key=os.environ["OPENAI_API_KEY"])

            llm = LLMBroker(gateway=gateway, model=model)
        except Exception as e:
            self.status_bar.showMessage(f"Error setting up LLM: {e}", 5000)
            return

        # Create and configure worker
        self.worker = RenameWorker(
            items=self.rename_items,
            llm=llm,
            cache_root=cache_root,
            provider=provider,
            model=model,
        )

        # Connect signals
        self.worker.progress_updated.connect(self._on_worker_progress)
        self.worker.item_status_changed.connect(self._on_worker_status_changed)
        self.worker.item_processed.connect(self._on_worker_item_processed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error_occurred.connect(self._on_worker_error)

        # Update UI state
        self.preview_btn.setEnabled(False)
        self.preview_btn.setVisible(False)  # Hide Preview button
        self.stop_btn.setEnabled(True)
        self.stop_btn.setVisible(True)  # Show Stop button
        self.select_folder_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.status_label.setText("Processing...")

        # Start worker
        self.worker.start()

    def _on_worker_progress(self, current: int, total: int) -> None:
        """Handle worker progress update.

        Args:
            current: Number of items processed.
            total: Total number of items.
        """
        self.progress_bar.setValue(current)
        percent = int((current / total) * 100) if total > 0 else 0
        self.status_bar.showMessage(f"Processing: {current}/{total} ({percent}%)")

    def _on_worker_status_changed(self, row: int, status: str, message: str) -> None:
        """Handle worker status change for individual item.

        Args:
            row: Row index in table.
            status: Status key.
            message: Human-readable message.
        """
        # Update status label to show current operation
        self.status_label.setText(message)

        # Select the row being processed to show image in preview
        if row < self.results_table.rowCount():
            self.results_table.selectRow(row)

        # Update table status column
        if row < self.results_table.rowCount():
            # Block signals during programmatic update
            self.results_table.blockSignals(True)

            # Use appropriate icon based on status
            icon_map = {
                "assessing": "🔍",
                "generating": "📝",
                "cache_hit": "💾",
            }
            icon = icon_map.get(status, "🔄")
            status_text = f"{icon} {message}"
            # Column 1: Status
            self.results_table.setItem(row, 1, QTableWidgetItem(status_text))

            # Unblock signals
            self.results_table.blockSignals(False)

    def _on_worker_item_processed(self, row: int, item: RenameItem) -> None:
        """Handle worker completing an item.

        Args:
            row: Row index in table.
            item: Updated RenameItem.
        """
        # Update rename_items list
        if row < len(self.rename_items):
            self.rename_items[row] = item

        # Update table row
        if row < self.results_table.rowCount():
            # Block signals during programmatic update
            self.results_table.blockSignals(True)

            # Column 0: Final name
            self.results_table.setItem(row, 0, QTableWidgetItem(item.final_name))

            # Column 1: Status
            status_text = f"{item.status_icon} {item.status_message}"
            self.results_table.setItem(row, 1, QTableWidgetItem(status_text))

            # Unblock signals
            self.results_table.blockSignals(False)

    def _on_worker_error(self, row: int, error_msg: str) -> None:
        """Handle worker error for individual item.

        Args:
            row: Row index in table.
            error_msg: Error message.
        """
        self.status_bar.showMessage(f"Error on row {row + 1}: {error_msg}", 5000)

    def _on_stop_clicked(self) -> None:
        """Handle Stop button click - cancel processing."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Stopping...")
            self.stop_btn.setEnabled(False)  # Prevent multiple clicks

    def _get_selected_row_and_item(self) -> tuple[int, RenameItem] | None:
        """Get the currently selected row index and item.

        Returns:
            Tuple of (row_index, item) if valid selection exists, None otherwise.
        """
        if not self.rename_items or not self.current_folder:
            return None

        selection_model = self.results_table.selectionModel()
        if not selection_model:
            return None

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.rename_items):
            return None

        return row, self.rename_items[row]

    def _perform_single_rename_with_refs(
        self, item: RenameItem, old_path: Path, new_path: Path, old_name: str, new_name: str
    ) -> int:
        """Perform single file rename and update references.

        Args:
            item: RenameItem to rename.
            old_path: Current file path.
            new_path: Target file path.
            old_name: Current filename.
            new_name: Target filename.

        Returns:
            Number of references updated.
        """
        old_path.rename(new_path)

        total_refs_updated = 0
        if self.update_refs_checkbox.isChecked():
            refs = find_references(old_path, self.current_folder, recursive=self.recursive_scan)
            if refs:
                updates = update_references(refs, old_name, new_name)
                total_refs_updated = sum(u.replacement_count for u in updates)

        return total_refs_updated

    def _update_ui_after_single_rename(self, row: int, item: RenameItem) -> None:
        """Update UI elements after successful single rename.

        Args:
            row: Table row index.
            item: RenameItem that was renamed.
        """
        status_text = f"{item.status_icon} {item.status_message}"
        self.results_table.item(row, 1).setText(status_text)

        self.preview_filename_label.setText(f"Selected: {item.source_name}")
        self._update_metadata_panel(item)

        try:
            pixmap = QPixmap(str(item.path))
            if not pixmap.isNull():
                self.current_pixmap = pixmap
                self._rescale_current_image()
        except Exception:
            pass

    def _on_single_rename_clicked(self) -> None:
        """Rename only the currently selected image to its final name.

        - Uses the value in the "Final Name" column for the selected row.
        - Updates Markdown references if the checkbox is enabled.
        - Updates UI elements for just that row.
        """
        selection = self._get_selected_row_and_item()
        if not selection:
            return

        row, item = selection
        old_path = item.path
        old_name = item.source_name
        new_name = item.final_name or item.source_name
        new_path = old_path.parent / new_name

        if old_name == new_name or old_path == new_path:
            self.status_bar.showMessage("No change: final name matches current name", 3000)
            self._update_single_rename_button_label()
            return

        try:
            total_refs_updated = self._perform_single_rename_with_refs(item, old_path, new_path, old_name, new_name)

            item.status = RenameStatus.COMPLETED
            item.status_message = "Successfully renamed"
            item.source_name = new_name
            item.path = new_path

            self._update_ui_after_single_rename(row, item)

            msg = "Renamed 1 file"
            if total_refs_updated > 0:
                msg += f" — updated {total_refs_updated} reference(s)"
            self.status_bar.showMessage(msg, 5000)

        except Exception as e:
            item.status = RenameStatus.ERROR
            item.status_message = f"Rename failed: {e}"
            item.error_message = str(e)
            self.results_table.item(row, 1).setText(f"{item.status_icon} {item.status_message}")
            QMessageBox.critical(self, "Error", f"Failed to rename file:\n{e}")
            self.status_bar.showMessage("Rename failed", 5000)
        finally:
            self._update_single_rename_button_label()

    def _get_items_to_rename(self) -> list[RenameItem]:
        """Get list of items that need renaming.

        Returns:
            List of RenameItems that need renaming.
        """
        return [
            item for item in self.rename_items
            if item.status in (RenameStatus.READY, RenameStatus.COLLISION)
            and item.final_name != item.source_name
        ]

    def _confirm_batch_rename(self, count: int, update_refs: bool) -> bool:
        """Show confirmation dialog for batch rename operation.

        Args:
            count: Number of files to rename.
            update_refs: Whether references will be updated.

        Returns:
            True if user confirmed, False otherwise.
        """
        ref_text = " and update markdown references" if update_refs else ""
        reply = QMessageBox.question(
            self,
            "Confirm Rename",
            f"Rename {count} file(s){ref_text}?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def _perform_batch_rename(
        self, items_to_rename: list[RenameItem], update_refs: bool
    ) -> tuple[int, int, int]:
        """Perform batch rename operation.

        Args:
            items_to_rename: List of items to rename.
            update_refs: Whether to update markdown references.

        Returns:
            Tuple of (renamed_count, error_count, total_refs_updated).
        """
        renamed_count = 0
        error_count = 0
        total_refs_updated = 0

        for item in items_to_rename:
            try:
                old_path = item.path
                new_path = old_path.parent / item.final_name

                if old_path == new_path:
                    continue

                old_path.rename(new_path)
                renamed_count += 1

                if update_refs:
                    refs = find_references(old_path, self.current_folder, recursive=self.recursive_scan)
                    if refs:
                        updates = update_references(refs, item.source_name, item.final_name)
                        total_refs_updated += sum(u.replacement_count for u in updates)

                item.status = RenameStatus.COMPLETED
                item.status_message = "Successfully renamed"
                item.source_name = item.final_name
                item.path = new_path

            except Exception as e:
                error_count += 1
                item.status = RenameStatus.ERROR
                item.status_message = f"Rename failed: {e}"
                item.error_message = str(e)

        return renamed_count, error_count, total_refs_updated

    def _on_apply_clicked(self) -> None:
        """Handle Apply button click - rename files and optionally update references."""
        if not self.rename_items or not self.current_folder:
            return

        items_to_rename = self._get_items_to_rename()

        if not items_to_rename:
            QMessageBox.information(
                self,
                "Nothing to Rename",
                "No files need renaming. All files are either unchanged or not yet processed."
            )
            return

        update_refs = self.update_refs_checkbox.isChecked()
        if not self._confirm_batch_rename(len(items_to_rename), update_refs):
            return

        renamed_count, error_count, total_refs_updated = self._perform_batch_rename(items_to_rename, update_refs)

        result_msg = f"Renamed {renamed_count} file(s)"
        if update_refs and total_refs_updated > 0:
            result_msg += f"\nUpdated {total_refs_updated} reference(s)"
        if error_count > 0:
            result_msg += f"\n{error_count} error(s) occurred"

        QMessageBox.information(self, "Rename Complete", result_msg)
        self.status_bar.showMessage(f"Renamed {renamed_count} files", 5000)

        self._on_refresh_clicked()

    def _on_worker_finished(self, stats: dict) -> None:
        """Handle worker completion.

        Args:
            stats: Summary statistics.
        """
        renamed = stats.get("renamed", 0)
        unchanged = stats.get("unchanged", 0)
        cached = stats.get("cached", 0)
        errors = stats.get("errors", 0)

        summary = f"Complete: {renamed} renamed, {unchanged} unchanged"
        if cached > 0:
            summary += f", {cached} from cache"
        if errors > 0:
            summary += f", {errors} errors"

        self.status_label.setText(summary)
        self.status_bar.showMessage(summary)

        # Re-enable buttons
        self.preview_btn.setEnabled(True)
        self.preview_btn.setVisible(True)  # Show Preview button
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)  # Hide Stop button
        self.select_folder_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)

        # Enable Apply button if there are items to rename
        if renamed > 0:
            self.apply_btn.setEnabled(True)
