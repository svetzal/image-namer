"""Shared fixtures for widget tests.

Widget tests require a running QApplication. This conftest creates one
session-wide so individual tests do not need to manage it.

All widget spec files must guard themselves with::

    pytest.importorskip("PySide6")

so they are automatically skipped when PySide6 is not installed.
"""

import pytest


@pytest.fixture(scope="session")
def qapp():
    """Return (or create) a QApplication instance for the test session."""
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
