import pytest

pytest.importorskip("PySide6")

from ui.widgets.provider_toolbar import ProviderToolbar  # noqa: E402


def should_expose_provider_property(qapp):
    toolbar = ProviderToolbar()
    toolbar._provider_combo.setCurrentText("openai")
    assert toolbar.provider == "openai"


def should_expose_model_property(qapp):
    toolbar = ProviderToolbar()
    # Whatever is in the combo, the property returns it
    current = toolbar._model_combo.currentText()
    assert toolbar.model == current


def should_expose_recursive_property_matching_checkbox(qapp):
    toolbar = ProviderToolbar()
    toolbar._recursive_checkbox.setChecked(False)
    assert toolbar.recursive is False
    toolbar._recursive_checkbox.setChecked(True)
    assert toolbar.recursive is True


def should_expose_update_refs_property_matching_checkbox(qapp):
    toolbar = ProviderToolbar()
    toolbar._update_refs_checkbox.setChecked(False)
    assert toolbar.update_refs is False


def should_emit_provider_changed_signal(qapp):
    toolbar = ProviderToolbar()
    received: list[str] = []
    toolbar.provider_changed.connect(received.append)

    toolbar._provider_combo.setCurrentText("openai")

    assert "openai" in received


def should_emit_recursive_changed_with_bool(qapp):
    toolbar = ProviderToolbar()
    received: list[bool] = []
    toolbar.recursive_changed.connect(received.append)

    from PySide6.QtCore import Qt
    toolbar._recursive_checkbox.setCheckState(Qt.CheckState.Unchecked)

    assert received == [False]
