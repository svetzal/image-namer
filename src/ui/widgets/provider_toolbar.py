"""Provider/model selector toolbar widget for Image Namer UI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel, QToolBar, QWidget

from operations.gateway_factory import MissingApiKeyError, create_gateway
from ui.settings import get_setting, set_setting


class ProviderToolbar(QToolBar):
    """Toolbar that owns provider/model selection and scan-option checkboxes.

    Emits signals when settings change; exposes read-only properties so
    callers never touch the internal combo boxes directly.
    """

    provider_changed: "Signal" = Signal(str)
    model_changed: "Signal" = Signal(str)
    recursive_changed: "Signal" = Signal(bool)

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize toolbar with provider/model combos and option checkboxes."""
        super().__init__("Main Toolbar", parent)

        saved_provider = get_setting("provider", "ollama")

        self.addWidget(QLabel("Provider:"))
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["ollama", "openai"])
        self._provider_combo.setCurrentText(saved_provider)
        self._provider_combo.currentTextChanged.connect(self._on_provider_changed)
        self.addWidget(self._provider_combo)
        self.addSeparator()

        self.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        self._update_model_list()
        self._restore_model_for_provider(saved_provider)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        self.addWidget(self._model_combo)
        self.addSeparator()

        self.addSeparator()
        self._recursive_checkbox = QCheckBox("Include subdirectories")
        self._recursive_checkbox.setChecked(True)
        self._recursive_checkbox.setToolTip("Scan subdirectories recursively when selecting a folder")
        self._recursive_checkbox.stateChanged.connect(self._on_recursive_changed)
        self.addWidget(self._recursive_checkbox)

        self.addSeparator()
        self._update_refs_checkbox = QCheckBox("Update references")
        self._update_refs_checkbox.setChecked(True)
        self._update_refs_checkbox.setToolTip("Update markdown references when renaming files")
        self.addWidget(self._update_refs_checkbox)

    @property
    def provider(self) -> str:
        """Currently selected provider name."""
        return str(self._provider_combo.currentText())

    @property
    def model(self) -> str:
        """Currently selected model name."""
        return str(self._model_combo.currentText())

    @property
    def recursive(self) -> bool:
        """Whether recursive directory scanning is enabled."""
        return bool(self._recursive_checkbox.isChecked())

    @property
    def update_refs(self) -> bool:
        """Whether markdown reference updating is enabled."""
        return bool(self._update_refs_checkbox.isChecked())

    def _update_model_list(self) -> None:
        """Refresh the model combo with models available from the gateway."""
        provider = self._provider_combo.currentText()
        default_models = {"ollama": ["gemma3:27b"], "openai": ["gpt-4o"]}

        self._model_combo.blockSignals(True)
        try:
            self._model_combo.clear()
            try:
                try:
                    gateway = create_gateway(provider)
                except MissingApiKeyError:
                    self._model_combo.addItems(default_models[provider])
                    return
                models = gateway.get_available_models()
                self._model_combo.addItems(models if models else default_models[provider])
            except (OSError, ConnectionError, ValueError, RuntimeError):
                self._model_combo.addItems(default_models[provider])
        finally:
            self._model_combo.blockSignals(False)

    def _restore_model_for_provider(self, provider: str) -> None:
        """Restore the last saved model selection for the given provider.

        Args:
            provider: Provider name (ollama or openai).
        """
        saved_model = get_setting(f"model_{provider}")
        if saved_model:
            self._model_combo.blockSignals(True)
            try:
                index = self._model_combo.findText(saved_model)
                if index >= 0:
                    self._model_combo.setCurrentIndex(index)
            finally:
                self._model_combo.blockSignals(False)

    def _on_provider_changed(self, provider: str) -> None:
        set_setting("provider", provider)
        self._update_model_list()
        self._restore_model_for_provider(provider)
        self.provider_changed.emit(provider)

    def _on_model_changed(self, model: str) -> None:
        if model:
            set_setting(f"model_{self._provider_combo.currentText()}", model)
        self.model_changed.emit(model)

    def _on_recursive_changed(self, state: int) -> None:
        self.recursive_changed.emit(state == Qt.CheckState.Checked.value)
