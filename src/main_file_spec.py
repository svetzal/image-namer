from pathlib import Path

import pytest
from typer.testing import CliRunner

import main as cli
from operations.models import ProposedName


class _LLMStub:
    def __init__(self, gateway=None, model: str | None = None, payload: dict | None = None):
        self.gateway = gateway
        self.model = model
        self.payload = payload or {"stem": "cat--sitting", "extension": ".png"}

    def generate_object(self, messages, object_model):
        if object_model is ProposedName:
            return ProposedName(**self.payload)
        raise AssertionError("Unexpected object_model")


runner = CliRunner()


def should_rename_file_happy_path(tmp_path: Path, mocker) -> None:
    src = tmp_path / "a.png"
    src.write_bytes(b"x")

    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: _LLMStub(gateway, model))
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["file", str(src), "--apply"])

    assert result.exit_code == 0
    assert not src.exists()
    assert (tmp_path / "cat--sitting.png").exists()


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


def should_be_idempotent_when_stem_matches(tmp_path: Path, mocker) -> None:
    src = tmp_path / "cat--sitting.png"
    src.write_bytes(b"x")

    # Propose the same stem as current
    payload = {"stem": "cat--sitting", "extension": ".png"}
    mocker.patch.object(
        cli,
        "LLMBroker",
        lambda gateway=None, model=None: _LLMStub(gateway, model, payload=payload),
    )
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["file", str(src), "--apply"])

    assert result.exit_code == 0
    assert src.exists()  # unchanged
    assert "unchanged" in result.output


def should_suffix_on_collision(tmp_path: Path, mocker) -> None:
    existing1 = tmp_path / "cat--sitting.png"
    existing1.write_bytes(b"x")
    existing2 = tmp_path / "cat--sitting-2.png"
    existing2.write_bytes(b"x")

    src = tmp_path / "orig.png"
    src.write_bytes(b"x")

    # LLM proposes cat--sitting.png
    payload = {"stem": "cat--sitting", "extension": ".png"}
    mocker.patch.object(
        cli,
        "LLMBroker",
        lambda gateway=None, model=None: _LLMStub(gateway, model, payload=payload),
    )
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())

    result = runner.invoke(cli.app, ["file", str(src), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "cat--sitting-3.png").exists()


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
    # Ensure output reflects chosen provider/model
    assert f"Provider: {expect_provider}" in result.output
    assert f"Model: {expect_model}" in result.output
