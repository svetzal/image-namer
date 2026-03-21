"""Tests for batch markdown reference update logic."""

from pathlib import Path

from operations.batch_references import apply_batch_reference_updates, count_batch_references
from operations.models import ProcessingResult, RenameStatus


def _make_result(
    tmp_path: Path,
    source: str,
    final: str,
    status: RenameStatus,
) -> ProcessingResult:
    img = tmp_path / source
    img.write_bytes(b"fake-image")
    return ProcessingResult(
        source=source,
        proposed=final,
        final=final,
        status=status,
        path=img,
    )


def should_return_zero_counts_when_no_renamed_results(tmp_path):
    results = [
        ProcessingResult(
            source="a.png",
            proposed="a.png",
            final="a.png",
            status=RenameStatus.UNCHANGED,
            path=tmp_path / "a.png",
        )
    ]

    result = apply_batch_reference_updates(results, tmp_path)

    assert result.total_references == 0
    assert result.files_updated == 0


def should_return_zero_counts_when_no_refs_found(tmp_path):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    result = apply_batch_reference_updates(results, tmp_path)

    assert result.total_references == 0
    assert result.files_updated == 0


def should_update_refs_and_return_counts(tmp_path):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    md_file = tmp_path / "doc.md"
    md_file.write_text("![Photo](old.png)\n![Again](old.png)\n")

    result = apply_batch_reference_updates(results, tmp_path)

    assert result.total_references == 2
    assert result.files_updated == 1
    assert "new.png" in md_file.read_text()


def should_skip_error_results(tmp_path):
    results = [
        ProcessingResult(
            source="bad.png",
            proposed="ERROR",
            final="bad.png",
            status=RenameStatus.ERROR,
        )
    ]

    result = apply_batch_reference_updates(results, tmp_path)

    assert result.total_references == 0


def should_handle_collision_status_results(tmp_path):
    results = [_make_result(tmp_path, "orig.png", "name-2.png", RenameStatus.COLLISION)]

    md_file = tmp_path / "note.md"
    md_file.write_text("![](orig.png)\n")

    result = apply_batch_reference_updates(results, tmp_path)

    assert result.total_references == 1
    assert "name-2.png" in md_file.read_text()


def should_count_refs_without_modifying_files(tmp_path):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    md_file = tmp_path / "doc.md"
    original_content = "![Photo](old.png)\n"
    md_file.write_text(original_content)

    result = count_batch_references(results, tmp_path)

    assert result.total_references == 1
    assert result.files_updated == 1
    assert md_file.read_text() == original_content


def should_count_return_zero_when_no_refs(tmp_path):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    result = count_batch_references(results, tmp_path)

    assert result.total_references == 0
    assert result.files_updated == 0
