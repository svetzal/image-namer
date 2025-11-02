from pathlib import Path

from typer.testing import CliRunner

import main as cli
from operations.models import NameAssessment, ProposedName


class _LLMStub:
    def __init__(self, gateway=None, model: str | None = None, name_map: dict | None = None):
        self.gateway = gateway
        self.model = model
        self.name_map = name_map or {}
        self.default_payload = {"stem": "default-image", "extension": ".png"}
        self._proposal_call_count = 0

    def generate_object(self, messages, object_model):
        if object_model is NameAssessment:
            # Always return unsuitable so tests proceed with renaming
            return NameAssessment(suitable=False)
        elif object_model is ProposedName:
            # Increment proposal counter
            self._proposal_call_count += 1

            # Use name_map if provided, otherwise use default
            if self._proposal_call_count in self.name_map:
                return ProposedName(**self.name_map[self._proposal_call_count])
            return ProposedName(**self.default_payload)
        raise AssertionError(f"Unexpected object_model: {object_model}")


runner = CliRunner()


def should_process_folder_flat(tmp_path: Path, mocker) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"y")
    (tmp_path / "c.txt").write_text("not an image")

    stub = _LLMStub(
        name_map={
            1: {"stem": "first-image", "extension": ".png"},
            2: {"stem": "second-image", "extension": ".jpg"},
        }
    )
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    # Disable caching in tests
    mocker.patch("operations.cache.load_from_cache", return_value=None)
    mocker.patch("operations.cache.save_to_cache", return_value=None)
    mocker.patch("operations.cache.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.cache.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "first-image.png").exists()
    assert (tmp_path / "second-image.jpg").exists()
    assert (tmp_path / "c.txt").exists()  # unchanged
    assert "2 renamed" in result.output


def should_process_folder_recursively(tmp_path: Path, mocker) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "b.png").write_bytes(b"y")

    stub = _LLMStub(
        name_map={
            1: {"stem": "root-image", "extension": ".png"},
            2: {"stem": "nested-image", "extension": ".png"},
        }
    )
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch("operations.cache.load_from_cache", return_value=None)
    mocker.patch("operations.cache.save_to_cache", return_value=None)
    mocker.patch("operations.cache.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.cache.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--recursive", "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "root-image.png").exists()
    assert (subdir / "nested-image.png").exists()
    assert "2 renamed" in result.output


def should_handle_empty_folder(tmp_path: Path) -> None:
    result = runner.invoke(cli.app, ["folder", str(tmp_path)])

    assert result.exit_code == 0
    assert "No supported image files found" in result.output


def should_handle_collisions_in_folder(tmp_path: Path, mocker) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"y")
    (tmp_path / "image-name.png").write_bytes(b"existing")

    # All three will be proposed as "image-name.png" (alphabetical order: a, b, image-name)
    stub = _LLMStub(
        name_map={
            1: {"stem": "image-name", "extension": ".png"},  # a.png
            2: {"stem": "image-name", "extension": ".png"},  # b.png
            3: {"stem": "image-name", "extension": ".png"},  # image-name.png (idempotent)
        }
    )
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch("operations.cache.load_from_cache", return_value=None)
    mocker.patch("operations.cache.save_to_cache", return_value=None)
    mocker.patch("operations.cache.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.cache.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    # a.png collides with existing image-name.png
    assert (tmp_path / "image-name-2.png").exists()  # a.png renamed
    # b.png collides with existing image-name.png AND planned image-name-2.png
    assert (tmp_path / "image-name-3.png").exists()  # b.png renamed
    # image-name.png stays as is (idempotent)
    assert (tmp_path / "image-name.png").exists()  # original unchanged
    assert "collision" in result.output or "2 renamed" in result.output


def should_be_idempotent_in_folder(tmp_path: Path, mocker) -> None:
    (tmp_path / "cat--sitting.png").write_bytes(b"x")
    (tmp_path / "dog--running.jpg").write_bytes(b"y")

    stub = _LLMStub(
        name_map={
            1: {"stem": "cat--sitting", "extension": ".png"},
            2: {"stem": "dog--running", "extension": ".jpg"},
        }
    )
    mocker.patch.object(cli, "LLMBroker", lambda gateway=None, model=None: stub)
    mocker.patch.object(cli, "_get_gateway", lambda provider: object())
    mocker.patch("operations.cache.load_from_cache", return_value=None)
    mocker.patch("operations.cache.save_to_cache", return_value=None)
    mocker.patch("operations.cache.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.cache.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--apply"])

    assert result.exit_code == 0
    assert (tmp_path / "cat--sitting.png").exists()
    assert (tmp_path / "dog--running.jpg").exists()
    assert "2 unchanged" in result.output


def should_show_summary_table_in_dry_run(tmp_path: Path, mocker) -> None:
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
    mocker.patch("operations.cache.load_from_cache", return_value=None)
    mocker.patch("operations.cache.save_to_cache", return_value=None)
    mocker.patch("operations.cache.load_assessment_from_cache", return_value=None)
    mocker.patch("operations.cache.save_assessment_to_cache", return_value=None)

    result = runner.invoke(cli.app, ["folder", str(tmp_path)])  # default is dry-run

    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert "Source" in result.output  # table header
    assert "Proposed" in result.output  # table header
    assert "first-image.png" in result.output
    assert "second-image.jpg" in result.output
    # Files should not be renamed in dry-run
    assert (tmp_path / "a.png").exists()
    assert (tmp_path / "b.jpg").exists()


def should_reject_invalid_provider_for_folder(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")

    result = runner.invoke(cli.app, ["folder", str(tmp_path), "--provider", "bogus"])

    assert result.exit_code == 2
    assert "Invalid provider" in result.output
