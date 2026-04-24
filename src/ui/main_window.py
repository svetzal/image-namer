"""Main window for Image Namer UI.

Contains the primary application layout with table, toolbar, and controls.
"""

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from operations.adapters import FilesystemAnalysisCache
from operations.gateway_factory import MissingApiKeyError
from operations.pipeline_factory import build_analysis_pipeline
from ui.models.ui_models import RenameItem, RenameStatus
from ui.widgets.image_preview_panel import ImagePreviewPanel
from ui.widgets.metadata_panel import MetadataPanel
from ui.widgets.provider_toolbar import ProviderToolbar
from ui.widgets.rename_table import RenameTableManager
from ui.rename_actions import perform_batch_rename, perform_rename_with_refs
from ui.workers.cache_loader import CacheLoaderWorker
from ui.workers.rename_worker import RenameWorker
from utils.fs import collect_image_files, ensure_cache_layout


class MainWindow(QMainWindow):
    """Main application window for Image Namer.

    Layout:
    - Toolbar: Provider/model selectors
    - Center: Splitter with preview panel (left) and results table (right)
    - Bottom: Progress bar, status label, action buttons
    """

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
        self.resize_timer: QTimer | None = None  # Debounce resize events

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add toolbar
        self.toolbar = ProviderToolbar(self)
        self.addToolBar(self.toolbar)
        self.toolbar.provider_changed.connect(self._on_toolbar_provider_changed)
        self.toolbar.recursive_changed.connect(self._on_toolbar_recursive_changed)

        # Create splitter for preview + (table + metadata)
        # This will take all available vertical space (stretch=1)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)  # Make the divider handle more visible

        # Left: Preview panel
        self.preview_panel = ImagePreviewPanel()
        splitter.addWidget(self.preview_panel)

        # Right: Container for table + metadata panel
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Table takes all available space
        self.table_manager = RenameTableManager()
        self.table_manager.selection_changed.connect(self._on_table_selection_changed)
        self.table_manager.item_edited.connect(self._on_table_item_edited)
        right_layout.addWidget(self.table_manager, stretch=1)

        # Metadata panel at bottom (fixed height)
        self.metadata_panel = MetadataPanel()
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

    def closeEvent(self, event: QCloseEvent) -> None:
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

        if not self.rename_items:
            return

        selection_model = self.table_manager.selectionModel()
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

    def _on_toolbar_provider_changed(self, provider: str) -> None:
        if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
            self.status_bar.showMessage("⚠️ Warning: OPENAI_API_KEY not set in environment", 5000)

    def _on_toolbar_recursive_changed(self, is_recursive: bool) -> None:
        if self.current_folder:
            mode = "recursive" if is_recursive else "flat"
            self.status_bar.showMessage(
                f"Recursive mode {'enabled' if is_recursive else 'disabled'}. "
                f"Click Refresh to re-scan in {mode} mode.",
                5000,
            )

    def _on_table_selection_changed(self) -> None:
        """Handle table selection change to update preview and metadata."""
        selected_rows = self.table_manager.selectionModel().selectedRows()

        if not selected_rows or not self.rename_items:
            self.preview_panel.clear()
            self.metadata_panel.clear()
            self._update_single_rename_button_label()
            return

        # Get selected row index
        row = selected_rows[0].row()

        if row >= len(self.rename_items):
            return

        # Get corresponding RenameItem
        item = self.rename_items[row]

        self.preview_panel.set_filename_label(f"Selected: {item.source_name}")
        self.metadata_panel.update(item)
        self.preview_panel.show_image(item.path)
        self._update_single_rename_button_label()

    def _on_table_item_edited(self, row: int, new_name: str) -> None:
        if row < len(self.rename_items):
            self.rename_items[row].final_name = new_name
            self.rename_items[row].manually_edited = True
            self.status_bar.showMessage(f"Updated final name for row {row + 1} (locked)", 2000)
            self._update_single_rename_button_label()

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
            except (OSError, PermissionError) as e:
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

        # Clear current selection and image
        self.preview_panel.clear()

        # Re-scan with current recursive setting
        self._scan_folder()

        mode = "recursively" if self.toolbar.recursive else "in folder only"
        self.status_bar.showMessage(f"Refreshed {mode}", 3000)

    def _scan_folder(self) -> None:
        """Scan current folder for image files and populate table."""
        if not self.current_folder:
            return

        image_files = collect_image_files(self.current_folder, self.toolbar.recursive)

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
        mode = "recursively" if self.toolbar.recursive else ""
        self.status_bar.showMessage(
            f"Loaded {len(image_files)} image(s) from {self.current_folder.name} {mode}".strip()
        )

        # Start background cache loader to populate cached data
        self._start_cache_loader()

    def _populate_table(self) -> None:
        """Populate table with rename items."""
        self.table_manager.populate(self.rename_items)

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
        provider = self.toolbar.provider
        model = self.toolbar.model

        # Setup cache
        cache_root = ensure_cache_layout(self.current_folder)
        cache = FilesystemAnalysisCache(cache_root / "cache" / "unified", provider=provider, model=model)

        # Create and start cache loader
        self.cache_loader = CacheLoaderWorker(
            items=self.rename_items,
            cache=cache,
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
        if row < self.table_manager.rowCount():
            self.table_manager.update_row(row, item)

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
        provider = self.toolbar.provider
        model = self.toolbar.model

        # Setup cache
        cache_root = ensure_cache_layout(
            self.current_folder if self.current_folder else Path.cwd()
        )

        # Build analysis pipeline (gateway + LLM + cache)
        try:
            pipeline = build_analysis_pipeline(provider, model, cache_root)
        except MissingApiKeyError as e:
            self.status_bar.showMessage(f"Error: {e}", 5000)
            return
        except (OSError, ConnectionError, ValueError, RuntimeError) as e:
            self.status_bar.showMessage(f"Error setting up LLM: {e}", 5000)
            return

        # Create and configure worker
        self.worker = RenameWorker(
            items=self.rename_items,
            analyzer=pipeline.analyzer,
            cache=pipeline.cache,
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

        icon_map = {
            "assessing": "🔍",
            "generating": "📝",
            "cache_hit": "💾",
        }
        icon = icon_map.get(status, "🔄")

        # Select the row being processed to show image in preview
        if row < self.table_manager.rowCount():
            self.table_manager.select_row(row)
            self.table_manager.update_row_status(row, icon, message)

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
        if row < self.table_manager.rowCount():
            self.table_manager.update_row(row, item)

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

        selection_model = self.table_manager.selectionModel()
        if not selection_model:
            return None

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.rename_items):
            return None

        return row, self.rename_items[row]

    def _perform_single_rename_with_refs(self, old_path: Path, new_name: str) -> int:
        """Perform single file rename and update references.

        Args:
            old_path: Current file path.
            new_name: Target filename.

        Returns:
            Number of references updated.
        """
        return perform_rename_with_refs(
            old_path,
            new_name,
            self.current_folder,
            self.toolbar.update_refs,
            self.toolbar.recursive,
        )

    def _update_ui_after_single_rename(self, row: int, item: RenameItem) -> None:
        """Update UI elements after successful single rename.

        Args:
            row: Table row index.
            item: RenameItem that was renamed.
        """
        self.table_manager.update_row_status(row, item.status_icon, item.status_message)

        self.preview_panel.set_filename_label(f"Selected: {item.source_name}")
        self.metadata_panel.update(item)
        self.preview_panel.show_image(item.path)

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
            total_refs_updated = self._perform_single_rename_with_refs(old_path, new_name)

            item.status = RenameStatus.COMPLETED
            item.status_message = "Successfully renamed"
            item.source_name = new_name
            item.path = new_path

            self._update_ui_after_single_rename(row, item)

            msg = "Renamed 1 file"
            if total_refs_updated > 0:
                msg += f" — updated {total_refs_updated} reference(s)"
            self.status_bar.showMessage(msg, 5000)

        except (OSError, PermissionError) as e:
            item.status = RenameStatus.ERROR
            item.status_message = f"Rename failed: {e}"
            item.error_message = str(e)
            self.table_manager.update_row_status(row, item.status_icon, item.status_message)
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
        return bool(reply == QMessageBox.StandardButton.Yes)

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

        update_refs = self.toolbar.update_refs
        if not self._confirm_batch_rename(len(items_to_rename), update_refs):
            return

        result = perform_batch_rename(items_to_rename, self.current_folder, update_refs, self.toolbar.recursive)

        result_msg = f"Renamed {result.renamed_count} file(s)"
        if update_refs and result.total_refs_updated > 0:
            result_msg += f"\nUpdated {result.total_refs_updated} reference(s)"
        if result.error_count > 0:
            result_msg += f"\n{result.error_count} error(s) occurred"

        QMessageBox.information(self, "Rename Complete", result_msg)
        self.status_bar.showMessage(f"Renamed {result.renamed_count} files", 5000)

        self._on_refresh_clicked()

    def _on_worker_finished(self, stats: dict[str, Any]) -> None:
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
