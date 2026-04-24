from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from ui.models.ui_models import RenameItem, RenameStatus  # noqa: E402
from ui.widgets.metadata_panel import MetadataPanel  # noqa: E402


def _make_item(**kwargs) -> RenameItem:
    defaults = dict(
        path=Path("/some/file.png"),
        source_name="file.png",
        final_name="file.png",
        status=RenameStatus.QUEUED,
    )
    defaults.update(kwargs)
    return RenameItem(**defaults)


def should_update_populates_source_label(qapp):
    panel = MetadataPanel()
    item = _make_item(source_name="my-photo.jpg", final_name="my-photo.jpg")
    panel.update(item)
    assert panel._meta_source.text() == "my-photo.jpg"


def should_update_shows_suitable_yes_when_unchanged(qapp):
    panel = MetadataPanel()
    item = _make_item(status=RenameStatus.UNCHANGED)
    panel.update(item)
    assert "Yes" in panel._meta_suitable.text()


def should_update_shows_suitable_no_when_ready(qapp):
    panel = MetadataPanel()
    item = _make_item(status=RenameStatus.READY)
    panel.update(item)
    assert panel._meta_suitable.text() == "No"


def should_update_shows_cached_indicator(qapp):
    panel = MetadataPanel()
    item = _make_item(cached=True)
    panel.update(item)
    assert "Yes" in panel._meta_cached.text()


def should_clear_resets_all_labels_to_none(qapp):
    panel = MetadataPanel()
    item = _make_item(source_name="foo.jpg", final_name="foo.jpg")
    panel.update(item)
    panel.clear()
    for label in (
        panel._meta_source,
        panel._meta_suitable,
        panel._meta_cached,
        panel._meta_proposed,
        panel._meta_final,
        panel._meta_edited,
        panel._meta_reasoning,
    ):
        assert label.text() == "(none)"
