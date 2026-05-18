"""Shared text normalization utilities for reference operations."""
import unicodedata
from pathlib import Path
from urllib.parse import unquote

STANDARD_IMAGE_PATTERN = r'!\[([^\]]*)\]\(([^)]+)\)'
STANDARD_LINK_PATTERN = r'\[([^\]]+)\]\(([^)]+)\)'
WIKI_EMBED_PATTERN = r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
WIKI_LINK_PATTERN = r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'

REFERENCE_PATTERNS: dict[str, str] = {
    'image': STANDARD_IMAGE_PATTERN,
    'link': STANDARD_LINK_PATTERN,
    'wiki_embed': WIKI_EMBED_PATTERN,
    'wiki_link': WIKI_LINK_PATTERN,
}

WIKI_REF_TYPES: frozenset[str] = frozenset({'wiki_embed', 'wiki_link'})

REF_TYPE_PREFIXES: dict[str, str] = {
    'image': '!',
    'link': '',
    'wiki_embed': '!',
    'wiki_link': '',
}


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


def names_match(ref_name: str, target_name: str) -> bool:
    """Check if two filenames match by name or stem, with URL decoding and Unicode normalization."""
    if Path(ref_name).stem == Path(target_name).stem:
        return True
    if normalized_name_equals(ref_name, target_name):
        return True
    if normalized_name_equals(Path(ref_name).stem, Path(target_name).stem):
        return True
    return False
