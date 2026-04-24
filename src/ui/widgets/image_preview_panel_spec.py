import struct
import zlib

import pytest

pytest.importorskip("PySide6")

from ui.widgets.image_preview_panel import ImagePreviewPanel  # noqa: E402


def _write_png(path) -> None:
    """Write a minimal 1×1 white RGB PNG to *path*."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    iend = chunk(b"IEND", b"")
    path.write_bytes(signature + ihdr + idat + iend)


def should_show_image_sets_pixmap(qapp, tmp_path):
    img_path = tmp_path / "test.png"
    _write_png(img_path)

    panel = ImagePreviewPanel()
    panel.show_image(img_path)

    assert panel.current_pixmap is not None
    assert not panel.current_pixmap.isNull()


def should_clear_resets_pixmap_and_label(qapp):
    panel = ImagePreviewPanel()
    panel.current_pixmap = object()  # type: ignore[assignment]

    panel.clear()

    assert panel.current_pixmap is None
    assert panel._image_label.text() == "No image selected"
    assert panel._filename_label.text() == "Selected: (none)"


def should_set_filename_label(qapp):
    panel = ImagePreviewPanel()
    panel.set_filename_label("Selected: my-photo.jpg")

    assert panel._filename_label.text() == "Selected: my-photo.jpg"


def should_show_image_handles_missing_file_gracefully(qapp, tmp_path):
    missing = tmp_path / "nonexistent.png"

    panel = ImagePreviewPanel()
    panel.show_image(missing)

    assert panel.current_pixmap is None
