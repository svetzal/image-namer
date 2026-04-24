"""Image preview panel widget for Image Namer UI."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResizableImageLabel(QLabel):
    """QLabel subclass that rescales its owning panel on resize."""

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize resizable image label."""
        super().__init__(parent)
        self._panel: "ImagePreviewPanel | None" = None

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize event to rescale image.

        Args:
            event: Resize event.
        """
        super().resizeEvent(event)
        if self._panel:
            self._panel._rescale_current_image()


class ImagePreviewPanel(QWidget):
    """Self-contained image preview panel.

    Owns the current pixmap state and exposes a simple API for
    showing, clearing, and labelling the previewed image.
    """

    def __init__(self, parent: "QWidget | None" = None) -> None:
        """Initialize image preview panel."""
        super().__init__(parent)
        self.current_pixmap: QPixmap | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self._image_label = ResizableImageLabel()
        self._image_label._panel = self
        self._image_label.setText("No image selected")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumSize(200, 200)
        self._image_label.setScaledContents(False)
        layout.addWidget(self._image_label, stretch=1)

        self._filename_label = QLabel("Selected: (none)")
        self._filename_label.setWordWrap(True)
        self._filename_label.setMaximumHeight(50)
        layout.addWidget(self._filename_label, stretch=0)

    def show_image(self, path: Path) -> None:
        """Load and display an image from the given path.

        Args:
            path: Path to the image file to display.
        """
        try:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._image_label.setText(f"Failed to load:\n{path.name}")
                self.current_pixmap = None
                return
            self.current_pixmap = pixmap
            self._rescale_current_image()
        except (OSError, ValueError) as e:
            self._image_label.setText(f"Error loading image:\n{e}")
            self.current_pixmap = None

    def clear(self) -> None:
        """Reset panel to placeholder state."""
        self._image_label.setText("No image selected")
        self._filename_label.setText("Selected: (none)")
        self.current_pixmap = None

    def set_filename_label(self, text: str) -> None:
        """Set the filename label displayed below the image.

        Args:
            text: Text to display.
        """
        self._filename_label.setText(text)

    def _rescale_current_image(self) -> None:
        """Rescale the current pixmap to fit the label's current size."""
        if not self.current_pixmap:
            return
        available_size = self._image_label.size()
        max_width = max(available_size.width() - 20, 200)
        max_height = max(available_size.height() - 20, 200)
        scaled_pixmap = self.current_pixmap.scaled(
            max_width,
            max_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled_pixmap)
