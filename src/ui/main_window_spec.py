"""Tests for MainWindow signal wiring and UI state.

Verifies that coordinator signals drive the correct widget state changes.
All tests require PySide6 and are automatically skipped when it is absent.
"""

import pytest

pytest.importorskip("PySide6")

from ui.main_window import MainWindow  # noqa: E402


def should_set_folder_loaded_state_when_coordinator_scans_successfully(qapp, mocker):
    mocker.patch("ui.processing_coordinator.collect_image_files", return_value=[])
    window = MainWindow()

    # Emit folder_scanned with items to simulate a successful scan
    from pathlib import Path
    from ui.models.ui_models import RenameItem, RenameStatus

    items = [
        RenameItem(
            path=Path("/tmp/img.png"),
            source_name="img.png",
            final_name="img.png",
            status=RenameStatus.QUEUED,
        )
    ]
    # Stub out start_cache_loader so it doesn't try to touch the filesystem
    mocker.patch.object(window.coordinator, "start_cache_loader")
    # Patch ensure_cache_layout to avoid filesystem side-effects
    mocker.patch("ui.main_window.ensure_cache_layout")

    window.coordinator.current_folder = Path("/tmp")
    window.coordinator.folder_scanned.emit(items)

    assert window.bottom_panel._refresh_btn.isEnabled()
    assert window.bottom_panel._preview_btn.isEnabled()


def should_enter_processing_state_on_preview_clicked(qapp, mocker):
    window = MainWindow()
    # Prevent actual LLM setup
    mocker.patch.object(window.coordinator, "start_analysis")

    window.bottom_panel.preview_clicked.emit()

    assert not window.bottom_panel._preview_btn.isVisible()
    assert window.bottom_panel._stop_btn.isVisible()
    assert window.bottom_panel._stop_btn.isEnabled()


def should_restore_idle_state_when_analysis_finishes(qapp, mocker):
    window = MainWindow()
    mocker.patch.object(window.coordinator, "start_analysis")

    # Put window into processing mode first
    window.bottom_panel.preview_clicked.emit()
    assert not window.bottom_panel._preview_btn.isVisible()

    # Simulate analysis completion with renamed items
    window.coordinator.analysis_finished.emit({"renamed": 2, "unchanged": 0, "cached": 0, "errors": 0})

    assert window.bottom_panel._preview_btn.isVisible()
    assert window.bottom_panel._preview_btn.isEnabled()
    assert not window.bottom_panel._stop_btn.isVisible()
    assert window.bottom_panel._apply_btn.isEnabled()


def should_restore_idle_state_on_coordinator_setup_error(qapp, mocker):
    window = MainWindow()
    mocker.patch.object(window.coordinator, "start_analysis")

    # Put window into processing mode
    window.bottom_panel.preview_clicked.emit()

    # Simulate a setup error (row == -1)
    window.coordinator.error_occurred.emit(-1, "missing API key")

    assert window.bottom_panel._preview_btn.isVisible()
    assert not window.bottom_panel._stop_btn.isVisible()
