from pathlib import Path

from operations.assess_name import assess_name
from operations.models import ProposedName, NameAssessment


class _FakeBuilder:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.images: list[Path] = []

    def add_image(self, path: Path):
        self.images.append(path)
        return self

    def build(self):
        return {"prompt": self.prompt, "images": self.images}


def should_include_proposed_filename_in_prompt_and_image(mocker, tmp_image_path, fake_llm):
    mocker.patch("operations.assess_name.MessageBuilder", _FakeBuilder)

    proposed = ProposedName(stem="sunset--golden-gate", extension=".jpg")

    result = assess_name(tmp_image_path, proposed_name=proposed, llm=fake_llm)

    # LLM was called exactly once
    assert len(fake_llm.calls) == 1
    messages, object_model = fake_llm.calls[0]

    assert object_model is NameAssessment
    assert isinstance(messages, list) and len(messages) == 1
    payload = messages[0]

    # The prompt mentions the proposed filename
    assert proposed.filename in payload["prompt"]

    # The image path is attached
    assert tmp_image_path in payload["images"]

    # Return type is NameAssessment
    assert isinstance(result, NameAssessment)
