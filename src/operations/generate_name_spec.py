from pathlib import Path

from operations.generate_name import generate_name
from operations.models import ProposedName


class _FakeBuilder:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.images: list[Path] = []

    def add_image(self, path: Path):
        self.images.append(path)
        return self

    def build(self):
        return {"prompt": self.prompt, "images": self.images}


def should_call_llm_with_prompt_and_image(mocker, tmp_image_path, fake_llm):
    # Patch MessageBuilder used in the module under test
    mocker.patch("operations.generate_name.MessageBuilder", _FakeBuilder)

    result = generate_name(tmp_image_path, llm=fake_llm)

    # LLM was called exactly once
    assert len(fake_llm.calls) == 1
    messages, object_model = fake_llm.calls[0]

    # Messages contain our built payload with prompt and images
    assert isinstance(messages, list) and len(messages) == 1
    payload = messages[0]
    assert tmp_image_path in payload["images"]
    assert "rubric" in payload["prompt"].lower()

    # Return type is ProposedName
    assert isinstance(result, ProposedName)
