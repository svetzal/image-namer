from pathlib import Path

from mojentic.llm import LLMBroker, MessageBuilder

from operations.models import NameAssessment, ProposedName


ASSESS_PROMPT_TEMPLATE = (
    "You are validating whether a proposed filename is suitable for the given image.\n"
    "Use this rubric:\n"
    "- 5–8 short words, lowercase, hyphen-separated.\n"
    "- Prefer structure: <primary-subject>--<specific-detail>.\n"
    "- Use helpful discriminators when applicable.\n"
    "- If the proposed name already satisfies the rubric and matches the content, mark it suitable.\n"
    "Answer by assessing suitability only; do not propose alternatives."
)


def assess_name(
    path: Path,
    proposed_name: ProposedName,
    llm: LLMBroker,
) -> NameAssessment:
    """Assess the suitability of a filename for an image"""
    prompt = (
        f"{ASSESS_PROMPT_TEMPLATE}\n\n"
        f"Proposed filename: '{proposed_name.filename}'."
    )
    messages = [
        MessageBuilder(prompt)
        .add_image(path)
        .build()
    ]

    return llm.generate_object(messages, object_model=NameAssessment)
