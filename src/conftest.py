import pathlib
import typing as t

import pytest

from operations.models import ImageAnalysis, NameAssessment, ProposedName


@pytest.fixture
def cache_dirs(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create standard cache directory layout and return cache root."""
    (tmp_path / ".image_namer" / "cache" / "analysis").mkdir(parents=True)
    (tmp_path / ".image_namer" / "cache" / "names").mkdir(parents=True)
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
            data = self.payload or {"stem": "primary-subject--specific-detail", "extension": ".png"}
            return ProposedName(**data)
        if object_model is NameAssessment:
            data = self.payload or {"suitable": True}
            return NameAssessment(**data)
        if object_model is ImageAnalysis:
            data = self.payload or {
                "current_name_suitable": True,
                "proposed_name": {"stem": "primary-subject--specific-detail", "extension": ".png"},
                "reasoning": "Test reasoning",
            }
            return ImageAnalysis(**data)
        raise AssertionError("Unexpected object_model requested")


@pytest.fixture
def tmp_image_path(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "sample.png"
    p.write_bytes(b"fake-image-bytes")
    return p


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
