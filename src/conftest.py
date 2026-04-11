import pathlib
import typing as t

import pytest

from operations.models import ImageAnalysis, ProposedName


def make_proposed_name(stem: str = "sample", extension: str = ".png") -> ProposedName:
    return ProposedName(stem=stem, extension=extension)


def make_analysis(
    suitable: bool = True,
    stem: str = "sample",
    extension: str = ".png",
    reasoning: str | None = None,
) -> ImageAnalysis:
    kwargs: dict[str, object] = {
        "current_name_suitable": suitable,
        "proposed_name": ProposedName(stem=stem, extension=extension),
    }
    if reasoning is not None:
        kwargs["reasoning"] = reasoning
    return ImageAnalysis(**kwargs)


@pytest.fixture
def cache_dirs(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create standard cache directory layout and return cache root."""
    (tmp_path / ".image_namer" / "cache" / "unified").mkdir(parents=True)
    return tmp_path / ".image_namer"


class FakeLLM:
    """A minimal stand-in for LLMBroker used in tests.

    It returns the provided object_model instantiated from a predetermined payload.
    """

    def __init__(self, payload: dict | None = None):
        self.payload = payload or {}
        self.calls: list[tuple[list[dict] | list[object], t.Any]] = []

    def generate_object(self, messages, object_model):  # noqa: D401 - external contract
        """Record call and return a constructed pydantic model object."""
        self.calls.append((messages, object_model))
        if object_model is ProposedName:
            if self.payload:
                return ProposedName(**self.payload)
            return make_proposed_name(stem="primary-subject--specific-detail")
        if object_model is ImageAnalysis:
            if self.payload:
                return ImageAnalysis(**self.payload)
            return make_analysis(stem="primary-subject--specific-detail", reasoning="Test reasoning")
        raise AssertionError("Unexpected object_model requested")


@pytest.fixture
def tmp_image_path(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "sample.png"
    p.write_bytes(b"fake-image-bytes")
    return p


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
