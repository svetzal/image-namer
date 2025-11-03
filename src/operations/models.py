from pathlib import Path
from pydantic import BaseModel, Field


class NameAssessment(BaseModel):
    """A judgement about the suitability of a filename for an image"""
    suitable: bool = Field(..., description="Whether the provided filename is suitable for the image")


class ProposedName(BaseModel):
    """Proposed filename components.

    Attributes:
        stem: The stem of the filename (without extension).
        extension: The extension of the filename. May or may not include the leading dot.
    """
    stem: str = Field(..., description="The stem of the filename")
    extension: str = Field(..., description="The extension of the filename. May include the leading dot")

    @property
    def filename(self) -> str:
        """Full filename composed from stem and extension.

        Handles both cases where `extension` includes the leading dot and where it does not.
        """
        ext = self.extension or ""
        if not ext:
            return self.stem
        if ext.startswith('.'):
            return f"{self.stem}{ext}"
        return f"{self.stem}.{ext}"


class ImageAnalysis(BaseModel):
    """Combined assessment and naming for an image in a single LLM call.

    Attributes:
        current_name_suitable: Whether the current filename already follows the rubric.
        proposed_name: The recommended filename (may match current if suitable).
        reasoning: Optional explanation of the assessment and naming decision.
    """
    current_name_suitable: bool = Field(
        ...,
        description="Whether the current filename already follows the rubric and matches image content"
    )
    proposed_name: ProposedName = Field(
        ...,
        description="The recommended filename components (stem and extension)"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the assessment and naming choice"
    )


class MarkdownReference(BaseModel):
    """A reference to an image in a markdown file.

    Attributes:
        file_path: The path to the markdown file containing the reference.
        line_number: The line number (1-indexed) where the reference appears.
        original_text: The original reference text (e.g., '![alt](image.png)').
        image_path: The path to the image being referenced.
        ref_type: The type of reference ('image', 'link', 'wiki', 'wiki_embed').
    """
    file_path: Path = Field(..., description="Path to the markdown file")
    line_number: int = Field(..., description="Line number (1-indexed)")
    original_text: str = Field(..., description="Original reference text")
    image_path: Path = Field(..., description="Path to the referenced image")
    ref_type: str = Field(..., description="Type of reference")


class ReferenceUpdate(BaseModel):
    """Result of updating references in markdown files.

    Attributes:
        file_path: The path to the markdown file that was updated.
        replacement_count: Number of replacements made in this file.
    """
    file_path: Path = Field(..., description="Path to the updated markdown file")
    replacement_count: int = Field(..., description="Number of replacements made")
