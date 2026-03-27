"""Tests for shared text normalization utilities."""
from operations.text_utils import normalize_spaces


def should_normalize_multiple_regular_spaces():
    assert normalize_spaces("hello   world") == "hello world"


def should_normalize_non_breaking_space():
    # \u00a0 = non-breaking space
    assert normalize_spaces("hello\u00a0world") == "hello world"


def should_normalize_narrow_no_break_space():
    # \u202f = narrow no-break space (used by Obsidian in some paths)
    assert normalize_spaces("hello\u202fworld") == "hello world"


def should_apply_nfkc_normalization():
    # NFKC decomposes ligatures: ﬁ (\ufb01) → fi
    assert normalize_spaces("\ufb01le") == "file"


def should_handle_empty_string():
    assert normalize_spaces("") == ""


def should_handle_string_with_no_spaces():
    assert normalize_spaces("hello") == "hello"


def should_handle_leading_and_trailing_whitespace():
    assert normalize_spaces("  hello world  ") == "hello world"
