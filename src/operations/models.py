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
