from operations.apply_renames import apply_renames
from operations.models import ProcessingResult, RenameStatus
from operations.ports import FileRenamerPort


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
