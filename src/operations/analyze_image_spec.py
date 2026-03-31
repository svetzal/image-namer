import pytest

from operations.analyze_image import UNIFIED_PROMPT, analyze_image
from operations.models import ImageAnalysis, ProposedName


class _FakeMessage:
    def __init__(self, prompt):
        self._prompt = prompt

    def add_image(self, path):
        return self

    def build(self):
        return {"prompt": self._prompt}


@pytest.fixture
def fake_analysis():
    return ImageAnalysis(
        current_name_suitable=False,
        proposed_name=ProposedName(stem="golden-retriever--running-in-park", extension=".png"),
        reasoning="Descriptive name matches content",
    )


@pytest.fixture
def mock_llm(mocker, fake_analysis):
    llm = mocker.MagicMock()
    llm.generate_object.return_value = fake_analysis
    return llm


def should_call_llm_with_unified_prompt(tmp_image_path, mock_llm, mocker):
    mocker.patch("operations.analyze_image.MessageBuilder", _FakeMessage)

    analyze_image(tmp_image_path, "sample.png", llm=mock_llm)

    mock_llm.generate_object.assert_called_once()
    messages = mock_llm.generate_object.call_args[0][0]
    assert UNIFIED_PROMPT in messages[0]["prompt"]


def should_include_current_filename_in_prompt(tmp_image_path, mock_llm, mocker):
    mocker.patch("operations.analyze_image.MessageBuilder", _FakeMessage)

    analyze_image(tmp_image_path, "my-photo.jpg", llm=mock_llm)

    messages = mock_llm.generate_object.call_args[0][0]
    assert "my-photo.jpg" in messages[0]["prompt"]


def should_request_image_analysis_model(tmp_image_path, mock_llm, mocker):
    mocker.patch("operations.analyze_image.MessageBuilder", _FakeMessage)

    analyze_image(tmp_image_path, "sample.png", llm=mock_llm)

    object_model = mock_llm.generate_object.call_args[1].get(
        "object_model"
    ) or mock_llm.generate_object.call_args[0][1]
    assert object_model is ImageAnalysis


def should_return_image_analysis_result(tmp_image_path, mock_llm, fake_analysis, mocker):
    mocker.patch("operations.analyze_image.MessageBuilder", _FakeMessage)

    result = analyze_image(tmp_image_path, "sample.png", llm=mock_llm)

    assert isinstance(result, ImageAnalysis)
    assert result.proposed_name.stem == "golden-retriever--running-in-park"
    assert result.current_name_suitable is False
