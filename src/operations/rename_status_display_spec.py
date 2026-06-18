"""Tests for the RenameStatus presentation table."""

from operations.models import RenameStatus
from operations.rename_status_display import RENAME_STATUS_PRESENTATION


def should_cover_every_rename_status():
    assert set(RENAME_STATUS_PRESENTATION) == set(RenameStatus)
