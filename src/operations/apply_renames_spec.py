from pathlib import Path

from operations.apply_renames import apply_rename_with_references, apply_renames
from operations.models import ProcessingResult, RenameStatus
from operations.ports import FileRenamerPort, MarkdownFilePort


def should_rename_files_with_renamed_status(tmp_path, mocker):
    img = tmp_path / "old.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="old.png", proposed="new.png", final="new.png",
            status=RenameStatus.RENAMED, path=img,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 1
    renamer.rename.assert_called_once_with(img, img.with_name("new.png"))


def should_rename_files_with_collision_status(tmp_path, mocker):
    img = tmp_path / "old.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="old.png", proposed="new.png", final="new-2.png",
            status=RenameStatus.COLLISION, path=img,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 1
    renamer.rename.assert_called_once_with(img, img.with_name("new-2.png"))


def should_skip_unchanged_results(mocker):
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="ok.png", proposed="ok.png", final="ok.png",
            status=RenameStatus.UNCHANGED,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 0
    renamer.rename.assert_not_called()


def should_skip_error_results(mocker):
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="bad.png", proposed="ERROR", final="bad.png",
            status=RenameStatus.ERROR,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 0
    renamer.rename.assert_not_called()


def should_skip_results_without_path(mocker):
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="old.png", proposed="new.png", final="new.png",
            status=RenameStatus.RENAMED,
            path=None,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 0
    renamer.rename.assert_not_called()


def should_skip_when_final_equals_current_name(tmp_path, mocker):
    img = tmp_path / "same.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="same.png", proposed="same.png", final="same.png",
            status=RenameStatus.RENAMED, path=img,
        )
    ]

    count = apply_renames(results, renamer)

    assert count == 0
    renamer.rename.assert_not_called()


def should_skip_when_old_and_new_names_match(mocker):
    old_path = Path("/some/path/image.png")
    renamer = mocker.Mock(spec=FileRenamerPort)

    outcome = apply_rename_with_references(old_path, "image.png", None, renamer, None, False)

    assert outcome.renamed is False
    assert outcome.new_path == old_path
    assert outcome.references_updated == 0
    renamer.rename.assert_not_called()


def should_call_renamer_with_destination_path(tmp_path, mocker):
    img = tmp_path / "old.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)

    outcome = apply_rename_with_references(img, "new.png", None, renamer, None, False)

    assert outcome.renamed is True
    assert outcome.new_path == tmp_path / "new.png"
    renamer.rename.assert_called_once_with(img, tmp_path / "new.png")


def should_return_zero_references_when_markdown_port_is_none(tmp_path, mocker):
    img = tmp_path / "old.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)

    outcome = apply_rename_with_references(img, "new.png", None, renamer, None, False)

    assert outcome.references_updated == 0


def should_find_and_update_references_when_markdown_port_provided(tmp_path, mocker):
    img = tmp_path / "old.png"
    img.write_bytes(b"x")
    renamer = mocker.Mock(spec=FileRenamerPort)
    markdown_files = mocker.Mock(spec=MarkdownFilePort)

    mock_refs = [mocker.Mock()]
    mock_update = mocker.Mock(replacement_count=3)
    mocker.patch("operations.apply_renames.find_references", return_value=mock_refs)
    mocker.patch("operations.apply_renames.update_references", return_value=[mock_update])

    outcome = apply_rename_with_references(img, "new.png", tmp_path, renamer, markdown_files, True)

    assert outcome.references_updated == 3


def should_return_total_renamed_count(tmp_path, mocker):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"x")
    img2 = tmp_path / "b.jpg"
    img2.write_bytes(b"y")
    renamer = mocker.Mock(spec=FileRenamerPort)

    results = [
        ProcessingResult(
            source="a.png", proposed="first.png", final="first.png",
            status=RenameStatus.RENAMED, path=img1,
        ),
        ProcessingResult(
            source="b.jpg", proposed="second.jpg", final="second.jpg",
            status=RenameStatus.RENAMED, path=img2,
        ),
    ]

    count = apply_renames(results, renamer)

    assert count == 2
