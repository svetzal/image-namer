import sys
from pathlib import Path

from utils.fs import next_available_name


def should_pick_next_numeric_suffix(tmp_path: Path) -> None:
    # existing: photo.png, photo-2.png, photo-3.png
    (tmp_path / "photo.png").write_bytes(b"x")
    (tmp_path / "photo-2.png").write_bytes(b"x")
    (tmp_path / "photo-3.png").write_bytes(b"x")

    result = next_available_name(tmp_path, "photo", ".png")

    assert result == "photo-4.png"


def should_be_case_insensitive_on_macos(mocker, tmp_path: Path) -> None:
    # Simulate macOS behavior by monkeypatching sys.platform
    mocker.patch.object(sys, "platform", "darwin")

    # Existing file differs by case
    (tmp_path / "Sample.png").write_bytes(b"x")

    result = next_available_name(tmp_path, "sample", ".png")

    # Since "Sample.png" exists (case-insensitive), next should be sample-2.png
    assert result == "sample-2.png"
