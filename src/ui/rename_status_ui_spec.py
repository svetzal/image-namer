"""Tests for the RenameStatus UI projection table."""

from operations.models import RenameStatus
from ui.models.ui_models import AnalysisStats
from ui.rename_status_ui import RENAME_STATUS_UI


def should_define_ui_projection_for_every_rename_status():
    assert set(RENAME_STATUS_UI) == set(RenameStatus)


def should_increment_a_real_analysis_stats_field():
    for info in RENAME_STATUS_UI.values():
        assert info.stat_field in AnalysisStats.model_fields
