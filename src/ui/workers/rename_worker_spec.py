"""Tests for RenameWorker.run() orchestration logic."""

import pytest

pytest.importorskip("PySide6")

from pathlib import Path  # noqa: E402
from unittest.mock import Mock  # noqa: E402

from constants import LLM_OPERATIONAL_ERRORS  # noqa: E402
from operations.models import ProcessingResult, RenameStatus  # noqa: E402
from operations.ports import AnalysisCachePort, ImageAnalyzerPort  # noqa: E402
from ui.models.ui_models import AnalysisStats, ItemStatus, RenameItem  # noqa: E402
from ui.workers.rename_worker import RenameWorker  # noqa: E402


def _make_item(tmp_path: Path, name: str = "img.png", *, manually_edited: bool = False) -> RenameItem:
    p = tmp_path / name
    p.touch()
    return RenameItem(
        path=p,
        source_name=name,
        final_name=name,
        status=ItemStatus.QUEUED,
        manually_edited=manually_edited,
    )


def _capture_signals(worker: RenameWorker) -> dict:
    received: dict = {
        "item_processed": [],
        "progress_updated": [],
        "error_occurred": [],
        "finished": [],
    }
    worker.item_processed.connect(lambda i, item: received["item_processed"].append((i, item)))
    worker.progress_updated.connect(lambda cur, tot: received["progress_updated"].append((cur, tot)))
    worker.error_occurred.connect(lambda i, msg: received["error_occurred"].append((i, msg)))
    worker.finished.connect(lambda stats: received["finished"].append(stats))
    return received


def should_skip_llm_for_manually_edited_item(tmp_path, qapp):
    item = _make_item(tmp_path, manually_edited=True)
    analyzer = Mock(spec=ImageAnalyzerPort)
    cache = Mock(spec=AnalysisCachePort)

    worker = RenameWorker([item], analyzer, cache)
    received = _capture_signals(worker)

    worker.run()

    analyzer.analyze.assert_not_called() if hasattr(analyzer, "analyze") else None
    cache.load.assert_not_called()
    assert len(received["item_processed"]) == 1
    assert len(received["progress_updated"]) == 1
    stats: AnalysisStats = received["finished"][0]
    assert stats.renamed == 1


def should_call_process_single_image_for_normal_item(tmp_path, qapp, mocker):
    item = _make_item(tmp_path, "photo.png")
    analyzer = Mock(spec=ImageAnalyzerPort)
    cache = Mock(spec=AnalysisCachePort)

    result = ProcessingResult(
        source="photo.png",
        proposed="proposed.png",
        final="proposed.png",
        status=RenameStatus.RENAMED,
        path=item.path,
    )
    mock_process = mocker.patch("ui.workers.rename_worker.process_single_image", return_value=result)

    worker = RenameWorker([item], analyzer, cache)
    received = _capture_signals(worker)

    worker.run()

    mock_process.assert_called_once()
    call_args = mock_process.call_args
    assert call_args[0][0] == item.path
    assert call_args[0][1] is analyzer
    assert call_args[0][2] is cache
    assert isinstance(call_args[0][3], set)
    assert len(received["item_processed"]) == 1
    assert len(received["progress_updated"]) == 1
    stats: AnalysisStats = received["finished"][0]
    assert stats.renamed == 1


def should_emit_error_occurred_when_result_status_is_error(tmp_path, qapp, mocker):
    item = _make_item(tmp_path, "bad.png")
    analyzer = Mock(spec=ImageAnalyzerPort)
    cache = Mock(spec=AnalysisCachePort)

    result = ProcessingResult(
        source="bad.png",
        proposed="ERROR",
        final="bad.png",
        status=RenameStatus.ERROR,
        path=item.path,
    )
    mocker.patch("ui.workers.rename_worker.process_single_image", return_value=result)

    worker = RenameWorker([item], analyzer, cache)
    received = _capture_signals(worker)

    worker.run()

    assert len(received["error_occurred"]) == 1
    assert received["error_occurred"][0][0] == 0
    assert item.status == ItemStatus.ERROR


def should_handle_llm_exception_and_set_error_stats(tmp_path, qapp, mocker):
    item = _make_item(tmp_path, "fail.png")
    analyzer = Mock(spec=ImageAnalyzerPort)
    cache = Mock(spec=AnalysisCachePort)

    error_type = LLM_OPERATIONAL_ERRORS[0]
    mocker.patch(
        "ui.workers.rename_worker.process_single_image",
        side_effect=error_type("LLM failed"),
    )

    worker = RenameWorker([item], analyzer, cache)
    received = _capture_signals(worker)

    worker.run()

    stats: AnalysisStats = received["finished"][0]
    assert stats.errors == 1
    assert item.status == ItemStatus.ERROR
    assert item.error_message is not None
    assert len(received["error_occurred"]) == 1
    assert len(received["item_processed"]) == 1


def should_stop_before_processing_when_stop_requested(tmp_path, qapp, mocker):
    item1 = _make_item(tmp_path, "a.png")
    item2 = _make_item(tmp_path, "b.png")
    analyzer = Mock(spec=ImageAnalyzerPort)
    cache = Mock(spec=AnalysisCachePort)

    mock_process = mocker.patch("ui.workers.rename_worker.process_single_image")

    worker = RenameWorker([item1, item2], analyzer, cache)
    received = _capture_signals(worker)
    worker.stop()

    worker.run()

    mock_process.assert_not_called()
    assert len(received["finished"]) == 1
    stats: AnalysisStats = received["finished"][0]
    assert stats.renamed == 0
    assert stats.errors == 0
