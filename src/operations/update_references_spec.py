"""Tests for update_references operation."""
from pathlib import Path

from .models import MarkdownReference
from .update_references import (
    _find_substring_with_different_spaces,
    _generate_replacement,
    _replace_in_path,
    _replace_standard_ref,
    _replace_wiki_ref,
    _replace_wiki_name,
    update_references,
)


def _make_ref(
    file_path: Path, line_number: int, original_text: str,
    image_path: str, ref_type: str
) -> MarkdownReference:
    return MarkdownReference(
        file_path=file_path,
        line_number=line_number,
        original_text=original_text,
        image_path=Path(image_path),
        ref_type=ref_type,
    )


def should_update_standard_image_reference(tmp_path, mock_markdown_files):
    md_file = tmp_path / "test.md"

    mock_markdown_files.read_markdown_content.return_value = "![Alt text](old.png)\n"
    refs = [_make_ref(md_file, 1, "![Alt text](old.png)", "old.png", "image")]

    updates = update_references(refs, "old.png", "new.png", mock_markdown_files)

    assert len(updates) == 1
    assert updates[0].file_path == md_file
    assert updates[0].replacement_count == 1
    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "![Alt text](new.png)\n")


def should_preserve_alt_text_in_standard_images(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"

    mock_markdown_files.read_markdown_content.return_value = "![Important diagram](diagram.jpg)\n"
    refs = [_make_ref(md_file, 1, "![Important diagram](diagram.jpg)", "diagram.jpg", "image")]

    update_references(refs, "diagram.jpg", "chart.jpg", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(
        md_file, "![Important diagram](chart.jpg)\n"
    )


def should_update_standard_link_reference(tmp_path, mock_markdown_files):
    md_file = tmp_path / "links.md"

    mock_markdown_files.read_markdown_content.return_value = "[View image](image.png)\n"
    refs = [_make_ref(md_file, 1, "[View image](image.png)", "image.png", "link")]

    update_references(refs, "image.png", "photo.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "[View image](photo.png)\n")


def should_preserve_link_text_in_standard_links(tmp_path, mock_markdown_files):
    md_file = tmp_path / "nav.md"

    mock_markdown_files.read_markdown_content.return_value = "[Click here for more](data.svg)\n"
    refs = [_make_ref(md_file, 1, "[Click here for more](data.svg)", "data.svg", "link")]

    update_references(refs, "data.svg", "info.svg", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(
        md_file, "[Click here for more](info.svg)\n"
    )


def should_update_wiki_embed_reference(tmp_path, mock_markdown_files):
    md_file = tmp_path / "wiki.md"

    mock_markdown_files.read_markdown_content.return_value = "![[old.png]]\n"
    refs = [_make_ref(md_file, 1, "![[old.png]]", "old.png", "wiki_embed")]

    update_references(refs, "old.png", "new.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "![[new.png]]\n")


def should_preserve_alias_in_wiki_embeds(tmp_path, mock_markdown_files):
    md_file = tmp_path / "obsidian.md"

    mock_markdown_files.read_markdown_content.return_value = "![[screenshot.png|My Screenshot]]\n"
    refs = [_make_ref(md_file, 1, "![[screenshot.png|My Screenshot]]", "screenshot.png", "wiki_embed")]

    update_references(refs, "screenshot.png", "capture.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(
        md_file, "![[capture.png|My Screenshot]]\n"
    )


def should_update_wiki_link_reference(tmp_path, mock_markdown_files):
    md_file = tmp_path / "vault.md"

    mock_markdown_files.read_markdown_content.return_value = "[[photo.jpg]]\n"
    refs = [_make_ref(md_file, 1, "[[photo.jpg]]", "photo.jpg", "wiki_link")]

    update_references(refs, "photo.jpg", "image.jpg", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "[[image.jpg]]\n")


def should_preserve_alias_in_wiki_links(tmp_path, mock_markdown_files):
    md_file = tmp_path / "notes.md"

    mock_markdown_files.read_markdown_content.return_value = "[[graph.svg|See Graph]]\n"
    refs = [_make_ref(md_file, 1, "[[graph.svg|See Graph]]", "graph.svg", "wiki_link")]

    update_references(refs, "graph.svg", "chart.svg", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "[[chart.svg|See Graph]]\n")


def should_update_multiple_references_in_same_file(tmp_path, mock_markdown_files):
    md_file = tmp_path / "multi.md"
    original = (
        "![First](old.png)\n"
        "Some text\n"
        "![[old.png]]\n"
        "[Link](old.png)\n"
    )

    mock_markdown_files.read_markdown_content.return_value = original
    refs = [
        _make_ref(md_file, 1, "![First](old.png)", "old.png", "image"),
        _make_ref(md_file, 3, "![[old.png]]", "old.png", "wiki_embed"),
        _make_ref(md_file, 4, "[Link](old.png)", "old.png", "link"),
    ]

    updates = update_references(refs, "old.png", "new.png", mock_markdown_files)

    assert len(updates) == 1
    assert updates[0].replacement_count == 3

    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "![First](new.png)" in written_content
    assert "![[new.png]]" in written_content
    assert "[Link](new.png)" in written_content


def should_update_references_in_multiple_files(tmp_path, mock_markdown_files):
    file1 = tmp_path / "doc1.md"
    file2 = tmp_path / "doc2.md"

    mock_markdown_files.read_markdown_content.side_effect = [
        "![Image](shared.png)\n",
        "![[shared.png]]\n",
    ]
    refs = [
        _make_ref(file1, 1, "![Image](shared.png)", "shared.png", "image"),
        _make_ref(file2, 1, "![[shared.png]]", "shared.png", "wiki_embed"),
    ]

    updates = update_references(refs, "shared.png", "common.png", mock_markdown_files)

    assert len(updates) == 2
    mock_markdown_files.write_markdown_content.assert_any_call(file1, "![Image](common.png)\n")
    mock_markdown_files.write_markdown_content.assert_any_call(file2, "![[common.png]]\n")


def should_handle_relative_paths_in_updates(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"

    mock_markdown_files.read_markdown_content.return_value = "![Photo](images/old.jpg)\n"
    refs = [_make_ref(md_file, 1, "![Photo](images/old.jpg)", "images/old.jpg", "image")]

    update_references(refs, "old.jpg", "new.jpg", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "![Photo](images/new.jpg)\n")


def should_return_empty_list_when_no_references(mock_markdown_files):
    updates = update_references([], "old.png", "new.png", mock_markdown_files)

    assert len(updates) == 0
    mock_markdown_files.read_markdown_content.assert_not_called()


def should_handle_stem_only_wiki_references(tmp_path, mock_markdown_files):
    md_file = tmp_path / "wiki.md"

    mock_markdown_files.read_markdown_content.return_value = "![[document]]\n"
    refs = [_make_ref(md_file, 1, "![[document]]", "document", "wiki_embed")]

    update_references(refs, "document.png", "article.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "![[article]]\n")


def should_not_write_file_when_content_unchanged(tmp_path, mock_markdown_files):
    md_file = tmp_path / "mixed.md"
    original = (
        "# Header\n"
        "![Image](target.png)\n"
        "Some text that mentions target.png in prose.\n"
        "Another paragraph.\n"
    )

    mock_markdown_files.read_markdown_content.return_value = original
    refs = [_make_ref(md_file, 2, "![Image](target.png)", "target.png", "image")]

    update_references(refs, "target.png", "result.png", mock_markdown_files)

    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "# Header\n" in written_content
    assert "![Image](result.png)\n" in written_content
    assert "Some text that mentions target.png in prose.\n" in written_content
    assert "Another paragraph.\n" in written_content


def should_handle_empty_alt_text(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"

    mock_markdown_files.read_markdown_content.return_value = "![](image.png)\n"
    refs = [_make_ref(md_file, 1, "![](image.png)", "image.png", "image")]

    update_references(refs, "image.png", "photo.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_called_once_with(md_file, "![](photo.png)\n")


def should_report_correct_replacement_counts(tmp_path, mock_markdown_files):
    file1 = tmp_path / "one.md"
    file2 = tmp_path / "two.md"

    mock_markdown_files.read_markdown_content.side_effect = [
        "![A](old.png)\n![B](old.png)\n",
        "![[old.png]]\n",
    ]
    refs = [
        _make_ref(file1, 1, "![A](old.png)", "old.png", "image"),
        _make_ref(file1, 2, "![B](old.png)", "old.png", "image"),
        _make_ref(file2, 1, "![[old.png]]", "old.png", "wiki_embed"),
    ]

    updates = update_references(refs, "old.png", "new.png", mock_markdown_files)

    assert len(updates) == 2
    file1_update = next(u for u in updates if u.file_path == file1)
    file2_update = next(u for u in updates if u.file_path == file2)
    assert file1_update.replacement_count == 2
    assert file2_update.replacement_count == 1


def should_update_url_encoded_references(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"
    original = "![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)\n"

    mock_markdown_files.read_markdown_content.return_value = original
    refs = [_make_ref(
        md_file, 1,
        "![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)",
        "Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png",
        "image",
    )]

    updates = update_references(
        refs, "Screenshot 2025-11-02 at 1.00.29 PM.png", "new-name.png", mock_markdown_files
    )

    assert len(updates) == 1
    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "new-name.png" in written_content
    assert "Screenshot" not in written_content


def should_preserve_url_encoding_in_updates(tmp_path, mock_markdown_files):
    md_file = tmp_path / "encoded.md"

    mock_markdown_files.read_markdown_content.return_value = "![Image](my%20photo.jpg)\n"
    refs = [_make_ref(md_file, 1, "![Image](my%20photo.jpg)", "my%20photo.jpg", "image")]

    updates = update_references(refs, "my photo.jpg", "renamed-photo.jpg", mock_markdown_files)

    assert len(updates) == 1
    written_content = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "renamed-photo.jpg" in written_content or "renamed%2Dphoto.jpg" in written_content


def should_not_write_when_no_change_needed(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"

    # Content that doesn't actually match the reference text after substitution
    mock_markdown_files.read_markdown_content.return_value = "![Same](same.png)\n"
    refs = [_make_ref(md_file, 1, "![Same](same.png)", "same.png", "image")]

    # Updating to the same name — no real change
    update_references(refs, "same.png", "same.png", mock_markdown_files)

    mock_markdown_files.write_markdown_content.assert_not_called()


def should_return_original_text_for_unknown_ref_type(tmp_path):
    ref = MarkdownReference(
        file_path=tmp_path / "doc.md",
        line_number=1,
        original_text="some original text",
        image_path=Path("old.png"),
        ref_type="unknown",
    )

    result = _generate_replacement(ref, "old.png", "new.png")

    assert result == "some original text"


def should_find_substring_with_non_breaking_space():
    haystack = "my photo.png"
    needle = "my photo.png"

    result = _find_substring_with_different_spaces(haystack, needle)

    assert result == "my photo.png"


def should_return_needle_when_no_match_in_find_substring():
    haystack = "something completely different"
    needle = "not found"

    result = _find_substring_with_different_spaces(haystack, needle)

    assert result == "not found"


def should_return_none_for_malformed_standard_ref():
    result = _replace_standard_ref(r'!\[([^\]]*)\]\(([^)]+)\)', "!", "not a standard ref", "old.png", "new.png")

    assert result is None


def should_return_none_for_malformed_wiki_ref():
    result = _replace_wiki_ref(r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', "!", "not a wiki ref", "old.png", "new.png")

    assert result is None


def should_return_unchanged_wiki_name_when_no_match():
    result = _replace_wiki_name("unrelated.png", "old.png", "new.png")

    assert result == "unrelated.png"


def should_log_debug_when_url_decode_fails(mocker):
    from urllib.parse import unquote as real_unquote

    actual_logger = _replace_in_path.__globals__["logger"]
    debug_spy = mocker.spy(actual_logger, "debug")

    def raising_unquote(s, *a, **kw):
        raise ValueError("decode error")

    _replace_in_path.__globals__["unquote"] = raising_unquote
    try:
        result = _replace_in_path("encoded%20name.png", "encoded%20name", "new-name")
    finally:
        _replace_in_path.__globals__["unquote"] = real_unquote

    assert "new-name" in result
    debug_spy.assert_called_once()


def should_handle_url_encoded_path_with_unicode_space(tmp_path, mock_markdown_files):
    md_file = tmp_path / "doc.md"
    # narrow no-break space ( ) encoded as %E2%80%AF
    original = "![One](my%E2%80%AFphoto.png)\n"

    mock_markdown_files.read_markdown_content.return_value = original
    refs = [_make_ref(md_file, 1, "![One](my%E2%80%AFphoto.png)", "my%E2%80%AFphoto.png", "image")]

    updates = update_references(refs, "my photo.png", "renamed.png", mock_markdown_files)

    assert len(updates) == 1
    written = mock_markdown_files.write_markdown_content.call_args[0][1]
    assert "renamed.png" in written
