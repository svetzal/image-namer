"""UI-specific data models for Image Namer.

These models track UI state and processing status.
They work alongside the operations/ models but add UI-specific fields.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ItemStatus(Enum):
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
    status: ItemStatus = ItemStatus.QUEUED
    status_message: str = "Waiting in queue..."
    error_message: str | None = None
    last_updated: datetime = Field(default_factory=datetime.now)
    cached: bool = False
    manually_edited: bool = False
    reasoning: str = ""  # LLM's reasoning for assessment and naming decision

    def update_status(self, status: ItemStatus, message: str) -> None:
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
            ItemStatus.QUEUED: "⏳",
            ItemStatus.ASSESSING: "🔍",
            ItemStatus.GENERATING: "📝",
            ItemStatus.CACHE_HIT: "💾",
            ItemStatus.READY: "✓",
            ItemStatus.UNCHANGED: "✓",
            ItemStatus.COLLISION: "⚠️",
            ItemStatus.ERROR: "✗",
            ItemStatus.COMPLETED: "✓",
        }
        return icons.get(self.status, "?")


class BatchRenameResult(BaseModel):
    """Outcome of a batch rename operation.

    Attributes:
        renamed_count: Number of files successfully renamed.
        error_count: Number of files that failed to rename.
        total_refs_updated: Total markdown references updated across all files.
    """

    renamed_count: int = 0
    error_count: int = 0
    total_refs_updated: int = 0


class RenameResult(BaseModel):
    """Result of a single file rename operation."""

    success: bool = Field(..., description="Whether the rename succeeded")
    error_message: str = Field(default="", description="Error or sentinel ('no_change') when not successful")
    references_updated: int = Field(default=0, description="Number of markdown references updated")


class CacheClearTarget(BaseModel):
    """Resolved cache directory and presence flag."""

    cache_dir: Path
    exists: bool


class CacheClearResult(BaseModel):
    """Outcome of a cache-clear operation."""

    success: bool
    error_message: str | None = None
