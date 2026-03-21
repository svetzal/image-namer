"""CLI integration tests for the folder command."""

from pathlib import Path

from typer.testing import CliRunner

import main as cli
from operations.models import NameAssessment, ProposedName

runner = CliRunner()


class _LLMStub:
    def __init__(self, gateway=None, model: str | None = None, name_map: dict | None = None):
        self.name_map = name_map or {}
        self._call_count = 0

    def generate_object(self, messages, object_model):
        if object_model is NameAssessment:
            return NameAssessment(suitable=False)
        self._call_count += 1
        payload = self.name_map.get(self._call_count, {"stem": "default-image", "extension": ".png"})
        return ProposedName(**payload)


def should_handle_empty_folder(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["folder", str(tmp_path)])

    assert result.exit_code == 0
    assert "No supported image files found" in result.output


def should_reject_invalid_provider_for_folder(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--provider", "bogus"])

    assert result.exit_code == 2
    assert "Invalid provider" in result.output


def should_rename_images_in_folder(tmp_path: Path, mocker) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"y")

    stub = _LLMStub(
        name_map={
            1: {"stem": "first-image", "extension": ".png"},
            2: {"stem": "second-image", "extension": ".jpg"},
        }
    )
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch("operations.process_image.load_from_cache", return_value=None)
    mocker.patch("operations.process_image.save_to_cache", return_value=None)
    mocker.patch("operations.process_image.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.process_image.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "first-image.png").exists()
    assert (tmp_path / "second-image.jpg").exists()
