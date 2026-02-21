from pathlib import Path
from typing import cast

from mojentic.llm import LLMBroker, MessageBuilder

from operations.models import ImageAnalysis


UNIFIED_PROMPT = (
    "You are an expert at analyzing and naming image files for clarity and organization.\n"
    "\n"
    "Your task is to:\n"
    "1. Assess whether the current filename follows the rubric and matches the image content.\n"
    "2. Propose an optimal filename according to the rubric.\n"
    "\n"
    "Rubric for filenames:\n"
    "- Compose 5–8 short words.\n"
    "- Lowercase letters only; separate words with hyphens.\n"
    "- Maximum total length: 80 characters.\n"
    "- Prefer structure: <primary-subject>--<specific-detail>.\n"
    "- Use helpful discriminators when applicable (e.g., chart-type, version, color, angle, year).\n"
    "\n"
    "Instructions:\n"
    "- If the current filename already follows the rubric perfectly, set current_name_suitable to true "
    "and propose the same filename.\n"
    "- If the current filename doesn't follow the rubric or doesn't match the content, set "
    "current_name_suitable to false and propose a better filename.\n"
    "- Always return both the assessment and a proposed filename.\n"
    "- Provide brief reasoning for your decision."
)


def analyze_image(
    path: Path,
    current_name: str,
    llm: LLMBroker,
) -> ImageAnalysis:
    """Analyze an image and provide assessment + naming in a single LLM call.

    This replaces the two-call pattern (assess_name + generate_name) with a single
    unified call that returns both pieces of information.

    Args:
        path: Path to the image file.
        current_name: Current filename (stem + extension) to assess.
        llm: LLM broker for making the call.

    Returns:
        ImageAnalysis containing assessment, proposed name, and reasoning.
    """
    prompt = f"{UNIFIED_PROMPT}\n\nCurrent filename: '{current_name}'"

    messages = [
        MessageBuilder(prompt)
        .add_image(path)
        .build()
    ]

    return cast(ImageAnalysis, llm.generate_object(messages, object_model=ImageAnalysis))
