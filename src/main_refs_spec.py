from pathlib import Path

from typer.testing import CliRunner

import main as cli

runner = CliRunner()


def should_search_for_references_when_update_refs_flag_used(tmp_path: Path, mocker) -> None:
    src = tmp_path / "img.png"
    src.write_bytes(b"x")

    # Stub LLM/gateway to avoid external calls
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: object())
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch.object(
        cli, "generate_name",
        lambda path, llm=None: type("PN", (), {"stem": "new-name", "extension": ".png"})()
    )

    result = runner.invoke(
        cli.app, ["file", str(src), "--update-refs", "--refs-root", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "No markdown references found" in result.output
