"""CLI integration tests for the folder command."""

from pathlib import Path
from unittest.mock import Mock

from typer.testing import CliRunner

import main as cli
from operations.models import ImageAnalysis, ProposedName
from operations.ports import AnalysisCachePort, ImageAnalyzerPort

runner = CliRunner()


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

    call_count = 0
    name_map = {
        1: {"stem": "first-image", "extension": ".png"},
        2: {"stem": "second-image", "extension": ".jpg"},
    }

    def fake_analyze(path, current_name):
        nonlocal call_count
        call_count += 1
        payload = name_map.get(call_count, {"stem": "default-image", "extension": ".png"})
        return ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(**payload),
            reasoning="stub",
        )

    mock_cache = Mock(spec=AnalysisCachePort)
    mock_cache.load.return_value = None
    mock_analyzer = Mock(spec=ImageAnalyzerPort)
    mock_analyzer.analyze.side_effect = fake_analyze

    mocker.patch.object(cli, "FilesystemAnalysisCache", lambda cache_dir: mock_cache)
    mocker.patch.object(cli, "MojenticImageAnalyzer", lambda llm: mock_analyzer)
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: object())
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "first-image.png").exists()
    assert (tmp_path / "second-image.jpg").exists()
