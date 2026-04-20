"""Tests for batch folder processing orchestration."""

from conftest import make_analysis
from operations.models import ProcessingResult, RenameStatus
from operations.process_folder import compute_statistics, process_folder


def should_return_empty_list_for_empty_input(mock_cache, mock_analyzer):
    results = process_folder([], mock_analyzer, mock_cache)

    assert results == []


def should_process_all_images_in_list(tmp_path, mock_cache, mock_analyzer):
    imgs = [tmp_path / f"img{i}.png" for i in range(3)]
    for img in imgs:
        img.write_bytes(b"x")

    call_count = 0

    def fake_analyze(path, name):
        nonlocal call_count
        call_count += 1
        return make_analysis(suitable=False, stem=f"name-{call_count}", reasoning="")

    mock_cache.load.return_value = None
    mock_analyzer.analyze.side_effect = fake_analyze

    results = process_folder(imgs, mock_analyzer, mock_cache)

    assert len(results) == 3


def should_track_planned_names_across_images(tmp_path, mock_cache, mock_analyzer):
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    img1.write_bytes(b"x")
    img2.write_bytes(b"y")

    mock_cache.load.return_value = None
    mock_analyzer.analyze.return_value = make_analysis(suitable=False, stem="same-name", reasoning="")

    results = process_folder([img1, img2], mock_analyzer, mock_cache)

    assert results[0].status == RenameStatus.RENAMED
    assert results[0].final == "same-name.png"
    assert results[1].status == RenameStatus.COLLISION
    assert results[1].final == "same-name-2.png"


def should_count_all_statuses():
    results = [
        ProcessingResult(source="a.png", proposed="x.png", final="x.png", status=RenameStatus.RENAMED),
        ProcessingResult(source="b.png", proposed="b.png", final="b.png", status=RenameStatus.UNCHANGED),
        ProcessingResult(source="c.png", proposed="x.png", final="x-2.png", status=RenameStatus.COLLISION),
        ProcessingResult(source="d.png", proposed="ERROR", final="d.png", status=RenameStatus.ERROR),
    ]

    stats = compute_statistics(results)

    assert stats[RenameStatus.RENAMED] == 1
    assert stats[RenameStatus.UNCHANGED] == 1
    assert stats[RenameStatus.COLLISION] == 1
    assert stats[RenameStatus.ERROR] == 1


def should_return_zeros_for_empty_results():
    stats = compute_statistics([])

    assert all(count == 0 for count in stats.values())


def should_handle_all_same_status():
    results = [
        ProcessingResult(source=f"{i}.png", proposed="x.png", final="x.png", status=RenameStatus.UNCHANGED)
        for i in range(5)
    ]

    stats = compute_statistics(results)

    assert stats[RenameStatus.UNCHANGED] == 5
    assert stats[RenameStatus.RENAMED] == 0
