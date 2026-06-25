"""Tests for the RenameStatus UI projection table."""

from operations.models import RenameStatus
from ui.rename_status_ui import RENAME_STATUS_UI


def should_define_ui_projection_for_every_rename_status():
    assert set(RENAME_STATUS_UI) == set(RenameStatus)
