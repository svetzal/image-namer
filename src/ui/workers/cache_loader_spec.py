"""Tests for CacheLoaderWorker.run() orchestration logic."""

import pytest

pytest.importorskip("PySide6")

from pathlib import Path  # noqa: E402
from unittest.mock import Mock  # noqa: E402

from operations.models import ImageAnalysis, ProcessingResult, RenameStatus  # noqa: E402
from operations.ports import AnalysisCachePort  # noqa: E402
from ui.models.ui_models import ItemStatus, RenameItem  # noqa: E402
from ui.workers.cache_loader import CacheLoaderWorker  # noqa: E402


def _make_item(tmp_path: Path, name: str = "img.png") -> RenameItem:
    p = tmp_path / name
    p.touch()
    return RenameItem(path=p, source_name=name, final_name=name, status=ItemStatus.QUEUED)


def _capture_signals(worker: CacheLoaderWorker) -> dict:
    received: dict = {
        "item_cache_loaded": [],
        "finished": [],
    }
    worker.item_cache_loaded.connect(lambda i, item: received["item_cache_loaded"].append((i, item)))
    worker.finished.connect(lambda cached, total: received["finished"].append((cached, total)))
    return received


def should_emit_item_cache_loaded_and_count_cache_hit(tmp_path, qapp, mocker):
    item = _make_item(tmp_path, "photo.png")
    cache = Mock(spec=AnalysisCachePort)

    result = ProcessingResult(
        source="photo.png",
        proposed="new-photo.png",
        final="new-photo.png",
        status=RenameStatus.RENAMED,
        path=item.path,
        cached=True,
    )
    mocker.patch("ui.workers.cache_loader.build_processing_result", return_value=result)
    cache.load.return_value = Mock(spec=ImageAnalysis)

    worker = CacheLoaderWorker([item], cache)
    received = _capture_signals(worker)

    worker.run()

    assert len(received["item_cache_loaded"]) == 1
    cached_count, total = received["finished"][0]
    assert cached_count == 1
    assert total == 1


def should_not_emit_item_cache_loaded_on_cache_miss(tmp_path, qapp):
    item = _make_item(tmp_path, "nope.png")
    cache = Mock(spec=AnalysisCachePort)
    cache.load.return_value = None

    worker = CacheLoaderWorker([item], cache)
    received = _capture_signals(worker)

    worker.run()

    assert len(received["item_cache_loaded"]) == 0
    cached_count, total = received["finished"][0]
    assert cached_count == 0
    assert total == 1


def should_stop_before_loading_when_stop_requested(tmp_path, qapp):
    item1 = _make_item(tmp_path, "a.png")
    item2 = _make_item(tmp_path, "b.png")
    cache = Mock(spec=AnalysisCachePort)

    worker = CacheLoaderWorker([item1, item2], cache)
    received = _capture_signals(worker)
    worker.stop()

    worker.run()

    cache.load.assert_not_called()
    assert len(received["finished"]) == 1
    cached_count, total = received["finished"][0]
    assert cached_count == 0
    assert total == 2
