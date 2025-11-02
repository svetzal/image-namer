"""Integration tests for assessment-first logic."""

from pathlib import Path

from typer.testing import CliRunner

import main as cli
from operations.models import NameAssessment, ProposedName

runner = CliRunner()


class _LLMStubWithSuitableAssessment:
    """LLM stub that returns suitable=True for assessments."""

    def __init__(self, gateway=None, model: str | None = None):
        self.gateway = gateway
        self.model = model

    def generate_object(self, messages, object_model):
        if object_model is NameAssessment:
            # Return suitable=True so files are not renamed
            return NameAssessment(suitable=True)
        elif object_model is ProposedName:
            # Should never be called when assessment is suitable
            raise AssertionError("generate_name should not be called when filename is suitable")
        raise AssertionError(f"Unexpected object_model: {object_model}")


def should_skip_rename_when_filename_is_suitable(tmp_path: Path, mocker):
    """Files with suitable names should show as unchanged without calling generate_name."""
    src = tmp_path / "cat--sitting-on-couch.png"
    src.write_bytes(b"x")

    stub = _LLMStubWithSuitableAssessment()
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["file", str(src), "--apply"])

    assert result.exit_code == 0
    assert src.exists()  # File should not be renamed
    assert "unchanged" in result.output
    # Verify generate_name was never called (stub would raise if it was)


def should_skip_all_suitable_files_in_folder(tmp_path: Path, mocker):
    """Folder processing should skip all files with suitable names."""
    (tmp_path / "cat--sitting.png").write_bytes(b"x")
    (tmp_path / "dog--running.jpg").write_bytes(b"y")

    stub = _LLMStubWithSuitableAssessment()
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "cat--sitting.png").exists()
    assert (tmp_path / "dog--running.jpg").exists()
    assert "2 unchanged" in result.output
    assert "0 renamed" in result.output
