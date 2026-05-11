"""Tests for shared text normalization utilities."""
from operations.text_utils import normalize_spaces, normalized_name_equals


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


def should_match_identical_names():
    assert normalized_name_equals("photo.png", "photo.png") is True


def should_match_url_encoded_name():
    assert normalized_name_equals("my%20photo.png", "my photo.png") is True


def should_match_unicode_space_after_url_decode():
    # Obsidian encodes narrow no-break space (\u202f) as %E2%80%AF
    assert normalized_name_equals("my%E2%80%AFphoto.png", "my photo.png") is True


def should_not_match_different_names():
    assert normalized_name_equals("other.png", "photo.png") is False


def should_not_match_when_decoded_differs():
    assert normalized_name_equals("foo%20bar.png", "different.png") is False


def should_return_false_for_type_error_in_normalized_name_equals():
    assert normalized_name_equals("hello", "world") is False
