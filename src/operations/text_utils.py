"""Shared text normalization utilities for reference operations."""
import unicodedata


def normalize_spaces(text: str) -> str:
    """Normalize all whitespace characters to regular ASCII spaces.

    Applies NFKC Unicode normalization then collapses all whitespace variants
    (non-breaking spaces, narrow no-break spaces, etc.) to a single ASCII space.

    Args:
        text: Text to normalize.

    Returns:
        Text with all Unicode whitespace normalized to ASCII space.
    """
    normalized = unicodedata.normalize('NFKC', text)
    return ' '.join(normalized.split())
