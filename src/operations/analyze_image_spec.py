import pytest

from conftest import make_analysis
from operations.analyze_image import UNIFIED_PROMPT, analyze_image
from operations.models import ImageAnalysis


class _FakeMessage:
    def __init__(self, prompt):
        self._prompt = prompt

    def add_image(self, path):
        return self

    def build(self):
        return {"prompt": self._prompt}


@pytest.fixture
def fake_analysis():
    return make_analysis(
        suitable=False,
        stem="golden-retriever--running-in-park",
        reasoning="Descriptive name matches content",
    )


@pytest.fixture
def mock_llm(mocker, fake_analysis):
    llm = mocker.MagicMock()
    llm.generate_object.return_value = fake_analysis
    return llm


def should_call_llm_with_unified_prompt(tmp_image_path, mock_llm):
    analyze_image(tmp_image_path, "sample.png", llm=mock_llm, message_builder=_FakeMessage)

    mock_llm.generate_object.assert_called_once()
    messages = mock_llm.generate_object.call_args[0][0]
    assert UNIFIED_PROMPT in messages[0]["prompt"]


def should_include_current_filename_in_prompt(tmp_image_path, mock_llm):
    analyze_image(tmp_image_path, "my-photo.jpg", llm=mock_llm, message_builder=_FakeMessage)

    messages = mock_llm.generate_object.call_args[0][0]
    assert "my-photo.jpg" in messages[0]["prompt"]


def should_request_image_analysis_model(tmp_image_path, mock_llm):
    analyze_image(tmp_image_path, "sample.png", llm=mock_llm, message_builder=_FakeMessage)

    object_model = mock_llm.generate_object.call_args[1].get(
        "object_model"
    ) or mock_llm.generate_object.call_args[0][1]
    assert object_model is ImageAnalysis


def should_return_image_analysis_result(tmp_image_path, mock_llm, fake_analysis):
    result = analyze_image(tmp_image_path, "sample.png", llm=mock_llm, message_builder=_FakeMessage)

    assert isinstance(result, ImageAnalysis)
    assert result.proposed_name.stem == "golden-retriever--running-in-park"
    assert result.current_name_suitable is False
