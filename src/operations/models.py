from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ProposedName(BaseModel):
    """Proposed filename components."""

    stem: str = Field(..., description="The stem of the filename")
    extension: str = Field(..., description="The extension of the filename. May or may not include the leading dot")

    def filename_with_fallback(self, fallback_ext: str) -> str:
        """Compose full filename, using fallback_ext when extension is empty.

        Args:
            fallback_ext: Extension to use when self.extension is empty.
                Should include a leading dot (e.g. ``".png"``).

        Returns:
            Full filename string with normalised extension.
        """
        ext = self.extension or ""
        if not ext:
            ext = fallback_ext
        elif not ext.startswith('.'):
            ext = f".{ext}"
        return f"{self.stem}{ext}"

    @property
    def filename(self) -> str:
        """Full filename composed from stem and extension.

        Handles both cases where ``extension`` includes the leading dot and
        where it does not.  When the extension is empty, returns the bare stem.
        """
        return self.filename_with_fallback("")


class ImageAnalysis(BaseModel):
    """Combined assessment and naming for an image in a single LLM call."""

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
        description="Optional brief explanation of the assessment and naming choice"
    )


class MarkdownReference(BaseModel):
    """A reference to an image in a markdown file."""
    file_path: Path = Field(..., description="Path to the markdown file")
    line_number: int = Field(..., description="Line number (1-indexed)")
    original_text: str = Field(..., description="Original reference text")
    image_path: Path = Field(..., description="Path to the referenced image")
    ref_type: str = Field(..., description="Type of reference")


class ReferenceUpdate(BaseModel):
    """Result of updating references in markdown files."""
    file_path: Path = Field(..., description="Path to the updated markdown file")
    replacement_count: int = Field(..., description="Number of replacements made")


class RenameStatus(StrEnum):
    """Status of a single image processing operation."""

    RENAMED = "renamed"
    UNCHANGED = "unchanged"
    COLLISION = "collision"
    ERROR = "error"


class ProcessingResult(BaseModel):
    """Result of processing a single image file."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(..., description="Original filename")
    proposed: str = Field(..., description="LLM-proposed filename")
    final: str = Field(..., description="Resolved final filename")
    status: RenameStatus = Field(..., description="Processing outcome")
    path: Path | None = Field(default=None, description="Original file path")
    reasoning: str = Field(default="", description="LLM reasoning for the assessment")
    cached: bool = Field(default=False, description="Whether result came from cache")


class BatchReferenceResult(BaseModel):
    """Result of batch markdown reference updates."""

    model_config = ConfigDict(frozen=True)

    total_references: int = Field(..., description="Total reference replacements")
    files_updated: int = Field(..., description="Number of markdown files updated")


class RenameOutcome(BaseModel):
    """Result of a single file rename with optional reference updates."""

    model_config = ConfigDict(frozen=True)

    renamed: bool = Field(..., description="Whether the file was renamed")
    new_path: Path = Field(..., description="Final path of the file (unchanged if not renamed)")
    references_updated: int = Field(..., description="Number of markdown references updated")
