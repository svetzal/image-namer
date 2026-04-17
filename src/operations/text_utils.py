"""Shared text normalization utilities for reference operations."""
import unicodedata
from urllib.parse import unquote

STANDARD_IMAGE_PATTERN = r'!\[([^\]]*)\]\(([^)]+)\)'
STANDARD_LINK_PATTERN = r'\[([^\]]+)\]\(([^)]+)\)'
WIKI_EMBED_PATTERN = r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
WIKI_LINK_PATTERN = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'


def normalize_spaces(text: str) -> str:
    """Normalize all whitespace characters to regular ASCII spaces.

    Applies NFKC Unicode normalization then collapses all whitespace variants
    (non-breaking spaces, narrow no-break spaces, etc.) to a single ASCII space.
    """
    normalized = unicodedata.normalize('NFKC', text)
    return ' '.join(normalized.split())


def normalized_name_equals(a: str, b: str) -> bool:
    """Check if two names are equal after URL decoding and Unicode space normalization."""
    if a == b:
        return True
    try:
        decoded_a = unquote(a)
        if decoded_a == b:
            return True
        if normalize_spaces(decoded_a) == normalize_spaces(b):
            return True
    except (ValueError, TypeError):
        pass
    return False
