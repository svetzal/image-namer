"""CLI integration tests for the file command."""

from pathlib import Path

from typer.testing import CliRunner

import main as cli

runner = CliRunner()


def should_reject_unsupported_type(tmp_path: Path) -> None:
    src = tmp_path / "a.txt"
    src.write_text("hello")

    result = runner.invoke(cli.app, ["file", str(src)])

    assert result.exit_code == 2
    assert "Unsupported file type" in result.output


def should_reject_invalid_provider(tmp_path: Path) -> None:
    src = tmp_path / "a.png"
    src.write_bytes(b"x")

    result = runner.invoke(cli.app, ["file", str(src), "--provider", "bogus"])

    assert result.exit_code == 2
    assert "Invalid provider" in result.output
