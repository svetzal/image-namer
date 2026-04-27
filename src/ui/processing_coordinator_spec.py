"""Tests for ProcessingCoordinator orchestration logic."""

import pytest

pytest.importorskip("PySide6")

from pathlib import Path  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from ui.models.ui_models import BatchRenameResult, RenameItem, RenameStatus  # noqa: E402
from ui.processing_coordinator import ProcessingCoordinator  # noqa: E402


def _make_item(tmp_path: Path, name: str = "img.png") -> RenameItem:
    p = tmp_path / name
    p.touch()
    return RenameItem(path=p, source_name=name, final_name=name, status=RenameStatus.QUEUED)


# ------------------------------------------------------------------
# scan_folder
# ------------------------------------------------------------------

def should_scan_folder_populates_rename_items(tmp_path, qapp, mocker):
    files = [tmp_path / "a.png", tmp_path / "b.png"]
    mocker.patch("ui.processing_coordinator.collect_image_files", return_value=files)

    coord = ProcessingCoordinator()
    coord.scan_folder(tmp_path, recursive=False)

    assert len(coord.rename_items) == 2
    assert coord.current_folder == tmp_path


def should_scan_folder_emits_folder_scanned_signal(tmp_path, qapp, mocker):
    files = [tmp_path / "x.png"]
    mocker.patch("ui.processing_coordinator.collect_image_files", return_value=files)

    coord = ProcessingCoordinator()
    received: list[list[RenameItem]] = []
    coord.folder_scanned.connect(received.append)

    coord.scan_folder(tmp_path, recursive=True)

    assert len(received) == 1
    assert len(received[0]) == 1


def should_scan_folder_emits_empty_list_when_no_images(tmp_path, qapp, mocker):
    mocker.patch("ui.processing_coordinator.collect_image_files", return_value=[])

    coord = ProcessingCoordinator()
    received: list[list[RenameItem]] = []
    coord.folder_scanned.connect(received.append)

    coord.scan_folder(tmp_path, recursive=False)

    assert received == [[]]
    assert coord.rename_items == []


# ------------------------------------------------------------------
# start_analysis
# ------------------------------------------------------------------

def should_start_analysis_emits_error_when_api_key_missing(tmp_path, qapp, mocker):
    from operations.gateway_factory import MissingApiKeyError

    mocker.patch("ui.processing_coordinator.ensure_cache_layout", return_value=tmp_path)
    mocker.patch(
        "ui.processing_coordinator.build_analysis_pipeline",
        side_effect=MissingApiKeyError("openai"),
    )

    coord = ProcessingCoordinator()
    coord.rename_items = [_make_item(tmp_path)]
    coord.current_folder = tmp_path

    errors: list[tuple[int, str]] = []
    coord.error_occurred.connect(lambda row, msg: errors.append((row, msg)))

    coord.start_analysis("openai", "gpt-4o")

    assert len(errors) == 1
    assert errors[0][0] == -1


def should_start_analysis_creates_worker_on_success(tmp_path, qapp, mocker):
    fake_pipeline = MagicMock()
    fake_pipeline.analyzer = MagicMock()
    fake_pipeline.cache = MagicMock()

    mocker.patch("ui.processing_coordinator.ensure_cache_layout", return_value=tmp_path)
    mocker.patch(
        "ui.processing_coordinator.build_analysis_pipeline", return_value=fake_pipeline
    )
    mock_worker_cls = mocker.patch("ui.processing_coordinator.RenameWorker")
    mock_worker_cls.return_value.isRunning.return_value = False

    coord = ProcessingCoordinator()
    coord.rename_items = [_make_item(tmp_path)]
    coord.current_folder = tmp_path

    coord.start_analysis("ollama", "gemma3:27b")

    mock_worker_cls.assert_called_once()
    mock_worker_cls.return_value.start.assert_called_once()


# ------------------------------------------------------------------
# stop_analysis
# ------------------------------------------------------------------

def should_stop_analysis_calls_worker_stop(tmp_path, qapp):
    coord = ProcessingCoordinator()
    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    coord._worker = mock_worker

    coord.stop_analysis()

    mock_worker.stop.assert_called_once()


def should_stop_analysis_is_noop_when_no_worker(tmp_path, qapp):
    coord = ProcessingCoordinator()
    coord.stop_analysis()  # Should not raise


# ------------------------------------------------------------------
# shutdown
# ------------------------------------------------------------------

def should_shutdown_stops_workers(tmp_path, qapp):
    coord = ProcessingCoordinator()

    mock_worker = MagicMock()
    mock_worker.isRunning.return_value = True
    mock_worker.wait.return_value = True
    coord._worker = mock_worker

    mock_loader = MagicMock()
    mock_loader.isRunning.return_value = True
    mock_loader.wait.return_value = True
    coord._cache_loader = mock_loader

    coord.shutdown()

    mock_worker.stop.assert_called_once()
    mock_loader.stop.assert_called_once()


# ------------------------------------------------------------------
# get_items_to_rename
# ------------------------------------------------------------------

def should_get_items_to_rename_returns_ready_items(tmp_path, qapp):
    coord = ProcessingCoordinator()
    coord.rename_items = [
        RenameItem(
            path=tmp_path / "a.png",
            source_name="a.png",
            final_name="a-new.png",
            status=RenameStatus.READY,
        ),
        RenameItem(
            path=tmp_path / "b.png",
            source_name="b.png",
            final_name="b.png",
            status=RenameStatus.UNCHANGED,
        ),
    ]

    result = coord.get_items_to_rename()

    assert len(result) == 1
    assert result[0].source_name == "a.png"


# ------------------------------------------------------------------
# rename_single
# ------------------------------------------------------------------

def should_rename_single_returns_success(tmp_path, qapp, mocker):
    mocker.patch("ui.rename_actions.perform_rename_with_refs", return_value=2)

    coord = ProcessingCoordinator()
    coord.current_folder = tmp_path
    coord.rename_items = [
        RenameItem(
            path=tmp_path / "old.png",
            source_name="old.png",
            final_name="new.png",
            status=RenameStatus.READY,
        )
    ]

    result = coord.rename_single(0, update_refs=True, recursive=False)

    assert result.success is True
    assert result.error_message == ""
    assert result.references_updated == 2
    assert coord.rename_items[0].source_name == "new.png"
    assert coord.rename_items[0].status == RenameStatus.COMPLETED


def should_rename_single_returns_no_change_when_names_match(tmp_path, qapp):
    coord = ProcessingCoordinator()
    coord.current_folder = tmp_path
    coord.rename_items = [
        RenameItem(
            path=tmp_path / "same.png",
            source_name="same.png",
            final_name="same.png",
            status=RenameStatus.READY,
        )
    ]

    result = coord.rename_single(0, update_refs=False, recursive=False)

    assert result.success is False
    assert result.error_message == "no_change"


def should_rename_single_returns_error_on_os_error(tmp_path, qapp, mocker):
    mocker.patch(
        "ui.rename_actions.perform_rename_with_refs",
        side_effect=OSError("permission denied"),
    )

    coord = ProcessingCoordinator()
    coord.current_folder = tmp_path
    coord.rename_items = [
        RenameItem(
            path=tmp_path / "old.png",
            source_name="old.png",
            final_name="new.png",
            status=RenameStatus.READY,
        )
    ]

    result = coord.rename_single(0, update_refs=False, recursive=False)

    assert result.success is False
    assert "permission denied" in result.error_message
    assert coord.rename_items[0].status == RenameStatus.ERROR


# ------------------------------------------------------------------
# rename_batch
# ------------------------------------------------------------------

def should_rename_batch_delegates_to_perform_batch_rename(tmp_path, qapp, mocker):
    fake_result = BatchRenameResult(renamed_count=3, error_count=0, total_refs_updated=5)
    mock_fn = mocker.patch(
        "ui.processing_coordinator.perform_batch_rename", return_value=fake_result
    )

    coord = ProcessingCoordinator()
    coord.current_folder = tmp_path
    coord.rename_items = [
        RenameItem(
            path=tmp_path / "a.png",
            source_name="a.png",
            final_name="a-new.png",
            status=RenameStatus.READY,
        )
    ]

    result = coord.rename_batch(update_refs=True, recursive=False)

    assert result.renamed_count == 3
    mock_fn.assert_called_once()
