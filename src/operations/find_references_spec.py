"""Tests for find_references operation."""
from pathlib import Path

from .find_references import find_references, ref_matches_filename
from .models import MarkdownReference


def should_find_standard_image_references(tmp_path, mock_markdown_files):
    image_path = tmp_path / "test.png"
    md_file = tmp_path / "test.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "# Test\n![Alt text](test.png)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].file_path == md_file
    assert refs[0].line_number == 2
    assert refs[0].original_text == "![Alt text](test.png)"
    assert refs[0].ref_type == "image"
    mock_markdown_files.find_markdown_files.assert_called_once_with(tmp_path, recursive=False)


def should_find_standard_link_references(tmp_path, mock_markdown_files):
    image_path = tmp_path / "image.jpg"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "[Link text](image.jpg)"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "link"
    assert refs[0].original_text == "[Link text](image.jpg)"


def should_find_wiki_embed_references(tmp_path, mock_markdown_files):
    image_path = tmp_path / "diagram.png"
    md_file = tmp_path / "note.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![[diagram.png]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"
    assert refs[0].original_text == "![[diagram.png]]"


def should_find_wiki_embed_with_alias(tmp_path, mock_markdown_files):
    image_path = tmp_path / "photo.jpg"
    md_file = tmp_path / "article.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![[photo.jpg|My Photo]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"
    assert refs[0].original_text == "![[photo.jpg|My Photo]]"


def should_find_wiki_link_references(tmp_path, mock_markdown_files):
    image_path = tmp_path / "chart.png"
    md_file = tmp_path / "index.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "[[chart.png]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"
    assert refs[0].original_text == "[[chart.png]]"


def should_find_wiki_link_with_alias(tmp_path, mock_markdown_files):
    image_path = tmp_path / "graph.svg"
    md_file = tmp_path / "readme.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "[[graph.svg|See the graph]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"
    assert refs[0].original_text == "[[graph.svg|See the graph]]"


def should_find_multiple_references_in_same_file(tmp_path, mock_markdown_files):
    image_path = tmp_path / "image.png"
    md_file = tmp_path / "multi.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = (
        "![First](image.png)\n"
        "Some text\n"
        "![[image.png]]\n"
        "[Link](image.png)\n"
    )

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 3
    assert refs[0].line_number == 1
    assert refs[0].ref_type == "image"
    assert refs[1].line_number == 3
    assert refs[1].ref_type == "wiki_embed"
    assert refs[2].line_number == 4
    assert refs[2].ref_type == "link"


def should_find_references_in_multiple_files(tmp_path, mock_markdown_files):
    image_path = tmp_path / "shared.png"
    file1 = tmp_path / "doc1.md"
    file2 = tmp_path / "doc2.md"

    mock_markdown_files.find_markdown_files.return_value = [file1, file2]
    mock_markdown_files.read_markdown_content.side_effect = [
        "![Image](shared.png)\n",
        "![[shared.png]]\n",
    ]

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 2
    assert {ref.file_path for ref in refs} == {file1, file2}


def should_pass_recursive_flag_to_port(tmp_path, mock_markdown_files):
    image_path = tmp_path / "nested.png"

    mock_markdown_files.find_markdown_files.return_value = []

    find_references(image_path, tmp_path, mock_markdown_files, recursive=True)

    mock_markdown_files.find_markdown_files.assert_called_once_with(tmp_path, recursive=True)


def should_not_search_recursively_when_disabled(tmp_path, mock_markdown_files):
    image_path = tmp_path / "nested.png"

    mock_markdown_files.find_markdown_files.return_value = []

    find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    mock_markdown_files.find_markdown_files.assert_called_once_with(tmp_path, recursive=False)


def should_return_empty_list_when_no_references_found(tmp_path, mock_markdown_files):
    image_path = tmp_path / "orphan.png"
    md_file = tmp_path / "empty.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "# No images here\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 0


def should_match_stem_only_wiki_links(tmp_path, mock_markdown_files):
    image_path = tmp_path / "document.png"
    md_file = tmp_path / "wiki.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![[document]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"


def should_handle_relative_paths_in_standard_markdown(tmp_path, mock_markdown_files):
    subdir = tmp_path / "images"
    image_path = subdir / "photo.jpg"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](images/photo.jpg)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].original_text == "![Photo](images/photo.jpg)"


def should_not_match_different_images(tmp_path, mock_markdown_files):
    image_path = tmp_path / "target.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Other](other.png)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 0


def should_distinguish_wiki_embed_from_wiki_link(tmp_path, mock_markdown_files):
    image_path = tmp_path / "test.png"
    md_file = tmp_path / "mixed.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![[test.png]]\n[[test.png]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 2
    assert refs[0].ref_type == "wiki_embed"
    assert refs[1].ref_type == "wiki_link"


def should_distinguish_standard_image_from_link(tmp_path, mock_markdown_files):
    image_path = tmp_path / "file.jpg"
    md_file = tmp_path / "links.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Image](file.jpg)\n[Link](file.jpg)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 2
    assert refs[0].ref_type == "image"
    assert refs[1].ref_type == "link"


def should_find_url_encoded_references(tmp_path, mock_markdown_files):
    image_path = tmp_path / "Screenshot 2025-11-02 at 1.00.29 PM.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = (
        "![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)\n"
    )

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "image"
    assert refs[0].original_text == "![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)"


def should_find_references_with_spaces_in_paths(tmp_path, mock_markdown_files):
    image_path = tmp_path / "my photo.jpg"
    md_file = tmp_path / "spaces.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Photo](my%20photo.jpg)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "image"


# --- ref_matches_filename tests: pure function, no port needed ---

def should_ref_match_direct_filename(tmp_path):
    ref = MarkdownReference(
        file_path=tmp_path / "doc.md",
        line_number=1,
        original_text="![](photo.png)",
        image_path=Path("photo.png"),
        ref_type="image",
    )

    assert ref_matches_filename(ref, "photo.png") is True


def should_ref_match_by_stem_only(tmp_path):
    ref = MarkdownReference(
        file_path=tmp_path / "doc.md",
        line_number=1,
        original_text="![[photo]]",
        image_path=Path("photo"),
        ref_type="wiki_embed",
    )

    assert ref_matches_filename(ref, "photo.png") is True


def should_ref_match_url_encoded_filename(tmp_path):
    ref = MarkdownReference(
        file_path=tmp_path / "doc.md",
        line_number=1,
        original_text="![](my%20photo.png)",
        image_path=Path("my%20photo.png"),
        ref_type="image",
    )

    assert ref_matches_filename(ref, "my photo.png") is True


def should_ref_not_match_different_filename(tmp_path):
    ref = MarkdownReference(
        file_path=tmp_path / "doc.md",
        line_number=1,
        original_text="![](other.png)",
        image_path=Path("other.png"),
        ref_type="image",
    )

    assert ref_matches_filename(ref, "photo.png") is False


def should_agree_on_url_encoded_stem_only_standard_ref(tmp_path, mock_markdown_files):
    image_path = tmp_path / "my photo.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Alt](my%20photo)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert ref_matches_filename(refs[0], "my photo.png") is True


def should_match_ref_path_resolving_to_same_absolute_path(tmp_path, mock_markdown_files):
    image_path = tmp_path / "photo.png"
    image_path.write_bytes(b"x")
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = f"![Alt]({image_path})\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1


def should_not_raise_on_oserror_during_path_resolution(tmp_path, mock_markdown_files):
    image_path = tmp_path / "photo.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![Alt](other.png)\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert refs == []


def should_match_url_decoded_path_resolving_to_image(tmp_path, mock_markdown_files):
    image_path = tmp_path / "my photo.png"
    image_path.write_bytes(b"x")
    md_file = tmp_path / "doc.md"
    encoded = str(image_path).replace(" ", "%20")

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = f"![Alt]({encoded})\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1


def should_match_wiki_link_by_stem_only(tmp_path, mock_markdown_files):
    image_path = tmp_path / "diagram.png"
    md_file = tmp_path / "wiki.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "[[diagram]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"


def should_find_wiki_embed_with_url_encoded_name(tmp_path, mock_markdown_files):
    image_path = tmp_path / "my photo.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "![[my%20photo.png]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"


def should_find_wiki_link_with_unicode_normalized_name(tmp_path, mock_markdown_files):
    image_path = tmp_path / "my photo.png"
    md_file = tmp_path / "doc.md"

    mock_markdown_files.find_markdown_files.return_value = [md_file]
    mock_markdown_files.read_markdown_content.return_value = "[[my photo.png]]\n"

    refs = find_references(image_path, tmp_path, mock_markdown_files, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"
