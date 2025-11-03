"""Image Namer UI entry point.

Launches the Qt6 application with the main window.
"""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    """Entry point for image-namer-ui command.

    Creates QApplication and MainWindow, then enters event loop.
    """
    # Runtime Python version is already enforced in main.py
    app = QApplication(sys.argv)
    app.setApplicationName("Image Namer")
    app.setOrganizationName("svetzal")
    app.setOrganizationDomain("vetzal.com")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    main()
