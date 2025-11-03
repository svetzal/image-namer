"""UI-specific data models for Image Namer.

These models track UI state and processing status.
They work alongside the operations/ models but add UI-specific fields.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class RenameStatus(Enum):
    """Processing status for individual items in the UI queue."""

    QUEUED = "queued"  # Waiting to be processed
    ASSESSING = "assessing"  # Checking if current name is suitable
    GENERATING = "generating"  # Generating new name with LLM
    CACHE_HIT = "cache_hit"  # Loaded from cache
    READY = "ready"  # Ready to rename
    UNCHANGED = "unchanged"  # Current name is already suitable
    COLLISION = "collision"  # Name collision detected
    ERROR = "error"  # Processing error
    COMPLETED = "completed"  # Successfully renamed (after Apply)


class RenameItem(BaseModel):
    """Single item in rename batch with detailed UI tracking.

    Attributes:
        path: Full path to the image file.
        source_name: Original filename.
        proposed_name: LLM-generated filename (None if not yet generated).
        final_name: Final filename after user edits or collision resolution.
        status: Current processing status.
        status_message: Human-readable status detail.
        error_message: Error details if status is ERROR.
        last_updated: Timestamp of last status change.
        cached: Whether result was loaded from cache.
        manually_edited: Whether user manually edited final_name (prevents overwrites).
    """

    path: Path
    source_name: str
    proposed_name: str | None = None
    final_name: str
    status: RenameStatus = RenameStatus.QUEUED
    status_message: str = "Waiting in queue..."
    error_message: str | None = None
    last_updated: datetime = Field(default_factory=datetime.now)
    cached: bool = False
    manually_edited: bool = False
    reasoning: str = ""  # LLM's reasoning for assessment and naming decision

    def update_status(self, status: RenameStatus, message: str) -> None:
        """Update status with timestamp.

        Args:
            status: New status value.
            message: Human-readable status message.
        """
        self.status = status
        self.status_message = message
        self.last_updated = datetime.now()

    @property
    def status_icon(self) -> str:
        """Get emoji icon for current status.

        Returns:
            Emoji string representing the status.
        """
        icons = {
            RenameStatus.QUEUED: "⏳",
            RenameStatus.ASSESSING: "🔍",
            RenameStatus.GENERATING: "📝",
            RenameStatus.CACHE_HIT: "💾",
            RenameStatus.READY: "✓",
            RenameStatus.UNCHANGED: "✓",
            RenameStatus.COLLISION: "⚠️",
            RenameStatus.ERROR: "✗",
            RenameStatus.COMPLETED: "✓",
        }
        return icons.get(self.status, "?")
