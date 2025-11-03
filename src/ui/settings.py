"""User settings persistence for Image Namer UI."""

import json
from pathlib import Path
from typing import Any


def get_settings_path() -> Path:
    """Get path to settings file in user's home directory.

    Returns:
        Path to .image_namer_settings.json in home directory.
    """
    return Path.home() / ".image_namer_settings.json"


def load_settings() -> dict[str, Any]:
    """Load settings from disk.

    Returns:
        Dictionary of settings, or empty dict if file doesn't exist or is invalid.
    """
    settings_path = get_settings_path()

    if not settings_path.exists():
        return {}

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # If settings file is corrupted, return empty dict
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings to disk.

    Args:
        settings: Dictionary of settings to save.
    """
    settings_path = get_settings_path()

    try:
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
    except OSError:
        # Silently fail if we can't write settings
        pass


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value.

    Args:
        key: Setting key to retrieve.
        default: Default value if key doesn't exist.

    Returns:
        Setting value or default.
    """
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Set a single setting value.

    Args:
        key: Setting key to set.
        value: Value to store.
    """
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
