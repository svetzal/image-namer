"""Main window for Image Namer UI."""

import os
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ui.models.ui_models import RenameItem
from ui.processing_coordinator import ProcessingCoordinator
from ui.widgets.bottom_control_panel import BottomControlPanel
from ui.widgets.image_preview_panel import ImagePreviewPanel
from ui.widgets.metadata_panel import MetadataPanel
from ui.widgets.provider_toolbar import ProviderToolbar
from ui.widgets.rename_table import RenameTableManager
from utils.fs import ensure_cache_layout


class MainWindow(QMainWindow):
    """Main application window: toolbar, splitter (preview + table), bottom controls."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Image Namer")
        self.resize(1200, 800)

        self.resize_timer: QTimer | None = None  # Debounce resize events

        self.coordinator = ProcessingCoordinator(self)
        self.coordinator.folder_scanned.connect(self._on_folder_scanned)
        self.coordinator.cache_item_loaded.connect(self._on_cache_item_loaded)
        self.coordinator.cache_loading_finished.connect(self._on_cache_loading_finished)
        self.coordinator.analysis_progress.connect(self._on_analysis_progress)
        self.coordinator.item_status_changed.connect(self._on_item_status_changed)
        self.coordinator.item_updated.connect(self._on_item_updated)
        self.coordinator.analysis_finished.connect(self._on_analysis_finished)
        self.coordinator.error_occurred.connect(self._on_coordinator_error)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar = ProviderToolbar(self)
        self.addToolBar(self.toolbar)
        self.toolbar.provider_changed.connect(self._on_toolbar_provider_changed)
        self.toolbar.recursive_changed.connect(self._on_toolbar_recursive_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)

        self.preview_panel = ImagePreviewPanel()
        splitter.addWidget(self.preview_panel)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        self.table_manager = RenameTableManager()
        self.table_manager.selection_changed.connect(self._on_table_selection_changed)
        self.table_manager.item_edited.connect(self._on_table_item_edited)
        right_layout.addWidget(self.table_manager, stretch=1)

        self.metadata_panel = MetadataPanel()
        right_layout.addWidget(self.metadata_panel, stretch=0)

        splitter.addWidget(right_container)
        splitter.setSizes([480, 720])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        main_layout.addWidget(splitter, stretch=1)

        self.bottom_panel = BottomControlPanel()
        self.bottom_panel.select_folder_clicked.connect(self._on_select_folder)
        self.bottom_panel.refresh_clicked.connect(self._on_refresh_clicked)
        self.bottom_panel.preview_clicked.connect(self._on_preview_clicked)
        self.bottom_panel.stop_clicked.connect(self._on_stop_clicked)
        self.bottom_panel.apply_clicked.connect(self._on_apply_clicked)
        self.bottom_panel.single_rename_clicked.connect(self._on_single_rename_clicked)
        main_layout.addWidget(self.bottom_panel, stretch=0)

        self._create_menu_bar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.coordinator.shutdown()
        event.accept()

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

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

    def _on_folder_scanned(self, items: list[RenameItem]) -> None:
        folder_name = (
            self.coordinator.current_folder.name
            if self.coordinator.current_folder
            else "folder"
        )
        if not items:
            self.status_bar.showMessage(
                f"No supported images found in {folder_name}", 5000
            )
            return

        self.table_manager.populate(items)
        self.bottom_panel.set_progress(0, len(items))
        self.bottom_panel.set_status_text(f"Ready to process {len(items)} images")
        self.bottom_panel.update_rename_button(None, None)
        self.bottom_panel.set_folder_loaded(True)

        mode = "recursively" if self.toolbar.recursive else ""
        self.status_bar.showMessage(
            f"Loaded {len(items)} image(s) from {folder_name} {mode}".strip()
        )

        self.coordinator.start_cache_loader(self.toolbar.provider, self.toolbar.model)
        self.bottom_panel.set_status_text("Loading cached data...")

    def _on_cache_item_loaded(self, row: int, item: RenameItem) -> None:
        if row < self.table_manager.rowCount():
            self.table_manager.update_row(row, item)

    def _on_cache_loading_finished(self, cached_count: int, total_count: int) -> None:
        if cached_count > 0:
            self.bottom_panel.set_status_text(
                f"Loaded {cached_count}/{total_count} from cache - Ready to process remaining"
            )
            self.status_bar.showMessage(
                f"{cached_count} of {total_count} already in cache", 3000
            )
        else:
            self.bottom_panel.set_status_text(f"Ready to process {total_count} images")

    def _on_analysis_progress(self, current: int, total: int) -> None:
        self.bottom_panel.set_progress(current, total)
        percent = int((current / total) * 100) if total > 0 else 0
        self.status_bar.showMessage(f"Processing: {current}/{total} ({percent}%)")

    def _on_item_status_changed(self, row: int, status: str, message: str) -> None:
        self.bottom_panel.set_status_text(message)
        icon_map = {"assessing": "🔍", "generating": "📝", "cache_hit": "💾"}
        icon = icon_map.get(status, "🔄")
        if row < self.table_manager.rowCount():
            self.table_manager.select_row(row)
            self.table_manager.update_row_status(row, icon, message)

    def _on_item_updated(self, row: int, item: RenameItem) -> None:
        if row < self.table_manager.rowCount():
            self.table_manager.update_row(row, item)

    def _on_analysis_finished(self, stats: dict[str, Any]) -> None:
        renamed = stats.get("renamed", 0)
        unchanged = stats.get("unchanged", 0)
        cached = stats.get("cached", 0)
        errors = stats.get("errors", 0)

        summary = f"Complete: {renamed} renamed, {unchanged} unchanged"
        if cached > 0:
            summary += f", {cached} from cache"
        if errors > 0:
            summary += f", {errors} errors"

        self.bottom_panel.set_status_text(summary)
        self.status_bar.showMessage(summary)
        self.bottom_panel.set_processing_state(False)

        if renamed > 0:
            self.bottom_panel.set_apply_enabled(True)

    def _on_coordinator_error(self, row: int, error_msg: str) -> None:
        if row == -1:
            self.status_bar.showMessage(f"Error: {error_msg}", 5000)
            self.bottom_panel.set_processing_state(False)
        else:
            self.status_bar.showMessage(f"Error on row {row + 1}: {error_msg}", 5000)

    def _on_toolbar_provider_changed(self, provider: str) -> None:
        if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
            self.status_bar.showMessage(
                "⚠️ Warning: OPENAI_API_KEY not set in environment", 5000
            )

    def _on_toolbar_recursive_changed(self, is_recursive: bool) -> None:
        if self.coordinator.current_folder:
            mode = "recursive" if is_recursive else "flat"
            self.status_bar.showMessage(
                f"Recursive mode {'enabled' if is_recursive else 'disabled'}. "
                f"Click Refresh to re-scan in {mode} mode.",
                5000,
            )

    def _on_table_selection_changed(self) -> None:
        selected_rows = self.table_manager.selectionModel().selectedRows()

        if not selected_rows or not self.coordinator.rename_items:
            self.preview_panel.clear()
            self.metadata_panel.clear()
            self.bottom_panel.update_rename_button(None, None)
            return

        row = selected_rows[0].row()
        if row >= len(self.coordinator.rename_items):
            return

        item = self.coordinator.rename_items[row]
        self.preview_panel.set_filename_label(f"Selected: {item.source_name}")
        self.metadata_panel.update(item)
        self.preview_panel.show_image(item.path)
        self.bottom_panel.update_rename_button(item.source_name, item.final_name)

    def _on_table_item_edited(self, row: int, new_name: str) -> None:
        if row < len(self.coordinator.rename_items):
            self.coordinator.rename_items[row].final_name = new_name
            self.coordinator.rename_items[row].manually_edited = True
            self.status_bar.showMessage(
                f"Updated final name for row {row + 1} (locked)", 2000
            )
            item = self.coordinator.rename_items[row]
            self.bottom_panel.update_rename_button(item.source_name, item.final_name)

    def _on_select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Image Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not folder:
            return
        self.coordinator.scan_folder(Path(folder), self.toolbar.recursive)

    def _on_refresh_clicked(self) -> None:
        if not self.coordinator.current_folder:
            return
        self.preview_panel.clear()
        self.coordinator.scan_folder(
            self.coordinator.current_folder, self.toolbar.recursive
        )
        mode = "recursively" if self.toolbar.recursive else "in folder only"
        self.status_bar.showMessage(f"Refreshed {mode}", 3000)

    def _on_preview_clicked(self) -> None:
        self.bottom_panel.set_processing_state(True)
        self.bottom_panel.set_status_text("Processing...")
        self.coordinator.start_analysis(self.toolbar.provider, self.toolbar.model)

    def _on_stop_clicked(self) -> None:
        self.coordinator.stop_analysis()
        self.bottom_panel.set_status_text("Stopping...")
        self.bottom_panel.set_stop_enabled(False)

    def _on_apply_clicked(self) -> None:
        if not self.coordinator.rename_items or not self.coordinator.current_folder:
            return

        items_to_rename = self.coordinator.get_items_to_rename()
        if not items_to_rename:
            QMessageBox.information(
                self,
                "Nothing to Rename",
                "No files need renaming. All files are either unchanged or not yet processed.",
            )
            return

        update_refs = self.toolbar.update_refs
        if not self._confirm_batch_rename(len(items_to_rename), update_refs):
            return

        result = self.coordinator.rename_batch(update_refs, self.toolbar.recursive)

        result_msg = f"Renamed {result.renamed_count} file(s)"
        if update_refs and result.total_refs_updated > 0:
            result_msg += f"\nUpdated {result.total_refs_updated} reference(s)"
        if result.error_count > 0:
            result_msg += f"\n{result.error_count} error(s) occurred"

        QMessageBox.information(self, "Rename Complete", result_msg)
        self.status_bar.showMessage(f"Renamed {result.renamed_count} files", 5000)
        self._on_refresh_clicked()

    def _on_single_rename_clicked(self) -> None:
        selection_model = self.table_manager.selectionModel()
        if not selection_model:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        success, error_msg, refs_updated = self.coordinator.rename_single(
            row, self.toolbar.update_refs, self.toolbar.recursive
        )

        if error_msg == "no_change":
            self.status_bar.showMessage(
                "No change: final name matches current name", 3000
            )
            self.bottom_panel.update_rename_button(None, None)
            return

        item = self.coordinator.rename_items[row]
        self.table_manager.update_row_status(row, item.status_icon, item.status_message)

        if success:
            self.preview_panel.set_filename_label(f"Selected: {item.source_name}")
            self.metadata_panel.update(item)
            self.preview_panel.show_image(item.path)
            msg = "Renamed 1 file"
            if refs_updated > 0:
                msg += f" — updated {refs_updated} reference(s)"
            self.status_bar.showMessage(msg, 5000)
            self.bottom_panel.update_rename_button(None, None)
        else:
            QMessageBox.critical(self, "Error", f"Failed to rename file:\n{error_msg}")
            self.status_bar.showMessage("Rename failed", 5000)
            self.bottom_panel.update_rename_button(item.source_name, item.final_name)

    def _on_clear_cache(self) -> None:
        cache_root = ensure_cache_layout(
            self.coordinator.current_folder
            if self.coordinator.current_folder
            else Path.cwd()
        )
        cache_dir = cache_root / "cache"

        if not cache_dir.exists():
            QMessageBox.information(
                self, "No Cache Found", "No cache directory found for this location."
            )
            return

        reply = QMessageBox.question(
            self,
            "Clear Cache",
            f"This will delete all cached LLM results in:\n{cache_dir}\n\n"
            "This includes:\n"
            "- Unified analysis cache (current format)\n"
            "- Legacy assessment and naming caches (old format)\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True)
                QMessageBox.information(self, "Cache Cleared", "Cache cleared successfully!")
                self.status_bar.showMessage("Cache cleared", 3000)
                if self.coordinator.current_folder:
                    self._on_refresh_clicked()
            except (OSError, PermissionError) as e:
                QMessageBox.critical(self, "Error", f"Failed to clear cache: {e}")

    def _confirm_batch_rename(self, count: int, update_refs: bool) -> bool:
        """Returns True if the user confirms the batch rename."""
        ref_text = " and update markdown references" if update_refs else ""
        reply = QMessageBox.question(
            self,
            "Confirm Rename",
            f"Rename {count} file(s){ref_text}?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return bool(reply == QMessageBox.StandardButton.Yes)
