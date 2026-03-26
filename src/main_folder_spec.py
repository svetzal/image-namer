"""CLI integration tests for the folder command."""

from pathlib import Path

from typer.testing import CliRunner

import main as cli

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
