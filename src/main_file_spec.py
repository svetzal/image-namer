"""CLI integration tests for the file command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import main as cli
from operations.models import NameAssessment, ProposedName

runner = CliRunner()


class _LLMStub:
    def __init__(self, gateway=None, model: str | None = None, payload: dict | None = None):
        self.payload = payload or {"stem": "cat--sitting", "extension": ".png"}

    def generate_object(self, messages, object_model):
        if object_model is NameAssessment:
            return NameAssessment(suitable=False)
        return ProposedName(**self.payload)


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


@pytest.mark.parametrize(
    "env_provider,env_model,flag_provider,flag_model,expect_provider,expect_model",
    [
        ("ollama", "gemma3:27b", None, None, "ollama", "gemma3:27b"),
        ("openai", "gpt-4o", None, None, "openai", "gpt-4o"),
        ("ollama", "llava:13b", "openai", "gpt-4o", "openai", "gpt-4o"),
    ],
)
def should_follow_flag_env_default_precedence(
    tmp_path: Path, mocker, env_provider, env_model, flag_provider,
    flag_model, expect_provider, expect_model
) -> None:
    src = tmp_path / "a.png"
    src.write_bytes(b"x")

    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: _LLMStub(gateway, model))
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    env = {
        "LLM_PROVIDER": env_provider,
        "LLM_MODEL": env_model,
    }

    args = ["file", str(src)]
    if flag_provider:
        args += ["--provider", flag_provider]
    if flag_model:
        args += ["--model", flag_model]

    result = runner.invoke(cli.app, args, env=env)

    assert result.exit_code == 0
    assert f"Provider: {expect_provider}" in result.output
    assert f"Model: {expect_model}" in result.output
