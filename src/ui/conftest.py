"""Shared fixtures for UI tests.

Tests that import PySide6 types (QObject subclasses, signals) require a running
QApplication. This conftest creates one session-wide so individual tests do not
need to manage it.

All spec files that use PySide6 must guard themselves with::

    pytest.importorskip("PySide6")

so they are automatically skipped when PySide6 is not installed (headless / CI).
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
