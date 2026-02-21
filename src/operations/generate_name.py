from pathlib import Path
from typing import cast

from mojentic.llm import MessageBuilder, LLMBroker

from operations.models import ProposedName


RUBRIC_PROMPT = (
    "You are an expert at naming image files for clarity and organization.\n"
    "Follow this strict rubric to propose a filename for the provided image:\n"
    "- Compose 5–8 short words.\n"
    "- Lowercase letters only; separate words with hyphens.\n"
    "- Maximum total length: 80 characters.\n"
    "- Prefer structure: <primary-subject>--<specific-detail>.\n"
    "- Use helpful discriminators when applicable (e.g., chart-type, version, color, angle, year).\n"
    "- If the current filename already follows this rubric, keep the same stem.\n"
    "Return only the stem and extension components for the filename."
)


def generate_name(
    path: Path,
    llm: LLMBroker,
) -> ProposedName:
    messages = [
        MessageBuilder(RUBRIC_PROMPT)
        .add_image(path)
        .build()
    ]
    return cast(ProposedName, llm.generate_object(messages, object_model=ProposedName))
