"""Tests for find_references operation."""
from .find_references import find_references


def should_find_standard_image_references(tmp_path):
    image_path = tmp_path / "test.png"
    image_path.touch()

    md_file = tmp_path / "test.md"
    md_file.write_text("# Test\n![Alt text](test.png)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].file_path == md_file
    assert refs[0].line_number == 2
    assert refs[0].original_text == "![Alt text](test.png)"
    assert refs[0].ref_type == "image"


def should_find_standard_link_references(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.touch()

    md_file = tmp_path / "doc.md"
    md_file.write_text("[Link text](image.jpg)")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "link"
    assert refs[0].original_text == "[Link text](image.jpg)"


def should_find_wiki_embed_references(tmp_path):
    image_path = tmp_path / "diagram.png"
    image_path.touch()

    md_file = tmp_path / "note.md"
    md_file.write_text("![[diagram.png]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"
    assert refs[0].original_text == "![[diagram.png]]"


def should_find_wiki_embed_with_alias(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.touch()

    md_file = tmp_path / "article.md"
    md_file.write_text("![[photo.jpg|My Photo]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"
    assert refs[0].original_text == "![[photo.jpg|My Photo]]"


def should_find_wiki_link_references(tmp_path):
    image_path = tmp_path / "chart.png"
    image_path.touch()

    md_file = tmp_path / "index.md"
    md_file.write_text("[[chart.png]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"
    assert refs[0].original_text == "[[chart.png]]"


def should_find_wiki_link_with_alias(tmp_path):
    image_path = tmp_path / "graph.svg"
    image_path.touch()

    md_file = tmp_path / "readme.md"
    md_file.write_text("[[graph.svg|See the graph]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_link"
    assert refs[0].original_text == "[[graph.svg|See the graph]]"


def should_find_multiple_references_in_same_file(tmp_path):
    image_path = tmp_path / "image.png"
    image_path.touch()

    md_file = tmp_path / "multi.md"
    md_file.write_text(
        "![First](image.png)\n"
        "Some text\n"
        "![[image.png]]\n"
        "[Link](image.png)\n"
    )

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 3
    assert refs[0].line_number == 1
    assert refs[0].ref_type == "image"
    assert refs[1].line_number == 3
    assert refs[1].ref_type == "wiki_embed"
    assert refs[2].line_number == 4
    assert refs[2].ref_type == "link"


def should_find_references_in_multiple_files(tmp_path):
    image_path = tmp_path / "shared.png"
    image_path.touch()

    file1 = tmp_path / "doc1.md"
    file1.write_text("![Image](shared.png)\n")

    file2 = tmp_path / "doc2.md"
    file2.write_text("![[shared.png]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 2
    assert {ref.file_path for ref in refs} == {file1, file2}


def should_search_recursively_when_enabled(tmp_path):
    image_path = tmp_path / "nested.png"
    image_path.touch()

    subdir = tmp_path / "subfolder"
    subdir.mkdir()
    md_file = subdir / "nested.md"
    md_file.write_text("![Nested](nested.png)\n")

    refs = find_references(image_path, tmp_path, recursive=True)

    assert len(refs) == 1
    assert refs[0].file_path == md_file


def should_not_search_recursively_when_disabled(tmp_path):
    image_path = tmp_path / "nested.png"
    image_path.touch()

    subdir = tmp_path / "subfolder"
    subdir.mkdir()
    md_file = subdir / "nested.md"
    md_file.write_text("![Nested](nested.png)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 0


def should_return_empty_list_when_no_references_found(tmp_path):
    image_path = tmp_path / "orphan.png"
    image_path.touch()

    md_file = tmp_path / "empty.md"
    md_file.write_text("# No images here\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 0


def should_match_stem_only_wiki_links(tmp_path):
    image_path = tmp_path / "document.png"
    image_path.touch()

    md_file = tmp_path / "wiki.md"
    md_file.write_text("![[document]]\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "wiki_embed"


def should_handle_relative_paths_in_standard_markdown(tmp_path):
    subdir = tmp_path / "images"
    subdir.mkdir()
    image_path = subdir / "photo.jpg"
    image_path.touch()

    md_file = tmp_path / "doc.md"
    md_file.write_text("![Photo](images/photo.jpg)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].original_text == "![Photo](images/photo.jpg)"


def should_not_match_different_images(tmp_path):
    image_path = tmp_path / "target.png"
    image_path.touch()

    other_image = tmp_path / "other.png"
    other_image.touch()

    md_file = tmp_path / "doc.md"
    md_file.write_text("![Other](other.png)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 0


def should_distinguish_wiki_embed_from_wiki_link(tmp_path):
    image_path = tmp_path / "test.png"
    image_path.touch()

    md_file = tmp_path / "mixed.md"
    md_file.write_text(
        "![[test.png]]\n"
        "[[test.png]]\n"
    )

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 2
    assert refs[0].ref_type == "wiki_embed"
    assert refs[1].ref_type == "wiki_link"


def should_distinguish_standard_image_from_link(tmp_path):
    image_path = tmp_path / "file.jpg"
    image_path.touch()

    md_file = tmp_path / "links.md"
    md_file.write_text(
        "![Image](file.jpg)\n"
        "[Link](file.jpg)\n"
    )

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 2
    assert refs[0].ref_type == "image"
    assert refs[1].ref_type == "link"


def should_find_url_encoded_references(tmp_path):
    image_path = tmp_path / "Screenshot 2025-11-02 at 1.00.29 PM.png"
    image_path.touch()

    md_file = tmp_path / "doc.md"
    md_file.write_text("![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "image"
    assert refs[0].original_text == "![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)"


def should_find_references_with_spaces_in_paths(tmp_path):
    image_path = tmp_path / "my photo.jpg"
    image_path.touch()

    md_file = tmp_path / "spaces.md"
    md_file.write_text("![Photo](my%20photo.jpg)\n")

    refs = find_references(image_path, tmp_path, recursive=False)

    assert len(refs) == 1
    assert refs[0].ref_type == "image"
