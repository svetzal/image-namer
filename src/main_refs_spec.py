from pathlib import Path

from typer.testing import CliRunner

import main as cli
from operations.models import NameAssessment

runner = CliRunner()


def should_search_for_references_when_update_refs_flag_used(tmp_path: Path, mocker) -> None:
    src = tmp_path / "img.png"
    src.write_bytes(b"x")

    # Stub LLM/gateway to avoid external calls
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: object())
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch(
        "operations.generate_name.generate_name",
        lambda path, llm=None: type("PN", (), {"stem": "new-name", "extension": ".png"})()
    )
    # Mock assessment to return unsuitable so generate_name is called
    mocker.patch(
        "operations.assess_name.assess_name",
        lambda path, proposed, llm=None: NameAssessment(suitable=False)
    )

    result = runner.invoke(
        cli.app, ["file", str(src), "--update-refs", "--refs-root", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "No markdown references found" in result.output
