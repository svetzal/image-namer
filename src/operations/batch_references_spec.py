"""Tests for batch markdown reference update logic."""

from pathlib import Path

from operations.batch_references import (
    process_batch_references,
    process_single_file_references,
)
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


def should_return_zero_counts_when_no_renamed_results(tmp_path, mock_markdown_files):
    results = [
        ProcessingResult(
            source="a.png",
            proposed="a.png",
            final="a.png",
            status=RenameStatus.UNCHANGED,
            path=tmp_path / "a.png",
        )
    ]

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 0
    assert result.files_updated == 0
    mock_markdown_files.find_markdown_files.assert_not_called()


def should_return_zero_counts_when_no_refs_found(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    mock_markdown_files.find_markdown_files.return_value = []

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 0
    assert result.files_updated == 0


def should_update_refs_and_return_counts(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n![Again](old.png)\n"

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 2
    assert result.files_updated == 1
    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "new.png" in written_content


def should_skip_error_results(tmp_path, mock_markdown_files):
    results = [
        ProcessingResult(
            source="bad.png",
            proposed="ERROR",
            final="bad.png",
            status=RenameStatus.ERROR,
        )
    ]

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 0
    mock_markdown_files.find_markdown_files.assert_not_called()


def should_handle_collision_status_results(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "orig.png", "name-2.png", RenameStatus.COLLISION)]
    md_file = tmp_path / "note.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![](orig.png)\n"

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 1
    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "name-2.png" in written_content


def should_count_refs_without_modifying_files(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 1
    assert result.files_updated == 1
    mock_markdown_files.write_markdown_content.assert_not_called()


def should_count_return_zero_when_no_refs(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]

    mock_markdown_files.find_markdown_files.return_value = []

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 0
    assert result.files_updated == 0


def should_count_single_file_references(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 1
    assert result.files_updated == 1
    mock_markdown_files.write_markdown_content.assert_not_called()


def should_count_single_file_references_returns_zero_when_no_refs(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")

    mock_markdown_files.find_markdown_files.return_value = []

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 0
    assert result.files_updated == 0


def should_apply_single_file_reference_updates(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 1
    assert result.files_updated == 1
    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "new.png" in written_content


def should_apply_single_file_reference_updates_returns_zero_when_no_refs(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")

    mock_markdown_files.find_markdown_files.return_value = []

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 0
    assert result.files_updated == 0
    mock_markdown_files.write_markdown_content.assert_not_called()


def should_process_single_file_references_counts_when_dry_run(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 1
    mock_markdown_files.write_markdown_content.assert_not_called()


def should_process_single_file_references_applies_when_not_dry_run(tmp_path, mock_markdown_files):
    img = tmp_path / "old.png"
    img.write_bytes(b"fake-image")
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_single_file_references(img, "new.png", tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 1
    mock_markdown_files.write_markdown_content.assert_called_once()


def should_process_batch_references_counts_when_dry_run(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=True)

    assert result.total_references == 1
    mock_markdown_files.write_markdown_content.assert_not_called()


def should_process_batch_references_applies_when_not_dry_run(tmp_path, mock_markdown_files):
    results = [_make_result(tmp_path, "old.png", "new.png", RenameStatus.RENAMED)]
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](old.png)\n"

    result = process_batch_references(results, tmp_path, mock_markdown_files, dry_run=False)

    assert result.total_references == 1
    mock_markdown_files.write_markdown_content.assert_called_once()
