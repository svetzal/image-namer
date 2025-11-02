"""Tests for update_references operation."""
from pathlib import Path

from .models import MarkdownReference
from .update_references import update_references


def should_update_standard_image_reference(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("![Alt text](old.png)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![Alt text](old.png)",
        image_path=Path("old.png"),
        ref_type="image"
    )]

    updates = update_references(refs, "old.png", "new.png")

    assert len(updates) == 1
    assert updates[0].file_path == md_file
    assert updates[0].replacement_count == 1
    assert md_file.read_text() == "![Alt text](new.png)\n"


def should_preserve_alt_text_in_standard_images(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("![Important diagram](diagram.jpg)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![Important diagram](diagram.jpg)",
        image_path=Path("diagram.jpg"),
        ref_type="image"
    )]

    update_references(refs, "diagram.jpg", "chart.jpg")

    assert md_file.read_text() == "![Important diagram](chart.jpg)\n"


def should_update_standard_link_reference(tmp_path):
    md_file = tmp_path / "links.md"
    md_file.write_text("[View image](image.png)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="[View image](image.png)",
        image_path=Path("image.png"),
        ref_type="link"
    )]

    update_references(refs, "image.png", "photo.png")

    assert md_file.read_text() == "[View image](photo.png)\n"


def should_preserve_link_text_in_standard_links(tmp_path):
    md_file = tmp_path / "nav.md"
    md_file.write_text("[Click here for more](data.svg)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="[Click here for more](data.svg)",
        image_path=Path("data.svg"),
        ref_type="link"
    )]

    update_references(refs, "data.svg", "info.svg")

    assert md_file.read_text() == "[Click here for more](info.svg)\n"


def should_update_wiki_embed_reference(tmp_path):
    md_file = tmp_path / "wiki.md"
    md_file.write_text("![[old.png]]\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![[old.png]]",
        image_path=Path("old.png"),
        ref_type="wiki_embed"
    )]

    update_references(refs, "old.png", "new.png")

    assert md_file.read_text() == "![[new.png]]\n"


def should_preserve_alias_in_wiki_embeds(tmp_path):
    md_file = tmp_path / "obsidian.md"
    md_file.write_text("![[screenshot.png|My Screenshot]]\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![[screenshot.png|My Screenshot]]",
        image_path=Path("screenshot.png"),
        ref_type="wiki_embed"
    )]

    update_references(refs, "screenshot.png", "capture.png")

    assert md_file.read_text() == "![[capture.png|My Screenshot]]\n"


def should_update_wiki_link_reference(tmp_path):
    md_file = tmp_path / "vault.md"
    md_file.write_text("[[photo.jpg]]\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="[[photo.jpg]]",
        image_path=Path("photo.jpg"),
        ref_type="wiki_link"
    )]

    update_references(refs, "photo.jpg", "image.jpg")

    assert md_file.read_text() == "[[image.jpg]]\n"


def should_preserve_alias_in_wiki_links(tmp_path):
    md_file = tmp_path / "notes.md"
    md_file.write_text("[[graph.svg|See Graph]]\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="[[graph.svg|See Graph]]",
        image_path=Path("graph.svg"),
        ref_type="wiki_link"
    )]

    update_references(refs, "graph.svg", "chart.svg")

    assert md_file.read_text() == "[[chart.svg|See Graph]]\n"


def should_update_multiple_references_in_same_file(tmp_path):
    md_file = tmp_path / "multi.md"
    md_file.write_text(
        "![First](old.png)\n"
        "Some text\n"
        "![[old.png]]\n"
        "[Link](old.png)\n"
    )

    refs = [
        MarkdownReference(
            file_path=md_file,
            line_number=1,
            original_text="![First](old.png)",
            image_path=Path("old.png"),
            ref_type="image"
        ),
        MarkdownReference(
            file_path=md_file,
            line_number=3,
            original_text="![[old.png]]",
            image_path=Path("old.png"),
            ref_type="wiki_embed"
        ),
        MarkdownReference(
            file_path=md_file,
            line_number=4,
            original_text="[Link](old.png)",
            image_path=Path("old.png"),
            ref_type="link"
        ),
    ]

    updates = update_references(refs, "old.png", "new.png")

    assert len(updates) == 1
    assert updates[0].replacement_count == 3
    content = md_file.read_text()
    assert "![First](new.png)" in content
    assert "![[new.png]]" in content
    assert "[Link](new.png)" in content


def should_update_references_in_multiple_files(tmp_path):
    file1 = tmp_path / "doc1.md"
    file1.write_text("![Image](shared.png)\n")

    file2 = tmp_path / "doc2.md"
    file2.write_text("![[shared.png]]\n")

    refs = [
        MarkdownReference(
            file_path=file1,
            line_number=1,
            original_text="![Image](shared.png)",
            image_path=Path("shared.png"),
            ref_type="image"
        ),
        MarkdownReference(
            file_path=file2,
            line_number=1,
            original_text="![[shared.png]]",
            image_path=Path("shared.png"),
            ref_type="wiki_embed"
        ),
    ]

    updates = update_references(refs, "shared.png", "common.png")

    assert len(updates) == 2
    assert file1.read_text() == "![Image](common.png)\n"
    assert file2.read_text() == "![[common.png]]\n"


def should_handle_relative_paths_in_updates(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("![Photo](images/old.jpg)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![Photo](images/old.jpg)",
        image_path=Path("images/old.jpg"),
        ref_type="image"
    )]

    update_references(refs, "old.jpg", "new.jpg")

    assert md_file.read_text() == "![Photo](images/new.jpg)\n"


def should_return_empty_list_when_no_references(tmp_path):
    updates = update_references([], "old.png", "new.png")

    assert len(updates) == 0


def should_handle_stem_only_wiki_references(tmp_path):
    md_file = tmp_path / "wiki.md"
    md_file.write_text("![[document]]\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![[document]]",
        image_path=Path("document"),
        ref_type="wiki_embed"
    )]

    update_references(refs, "document.png", "article.png")

    assert md_file.read_text() == "![[article]]\n"


def should_not_modify_unrelated_content(tmp_path):
    md_file = tmp_path / "mixed.md"
    original = (
        "# Header\n"
        "![Image](target.png)\n"
        "Some text that mentions target.png in prose.\n"
        "Another paragraph.\n"
    )
    md_file.write_text(original)

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=2,
        original_text="![Image](target.png)",
        image_path=Path("target.png"),
        ref_type="image"
    )]

    update_references(refs, "target.png", "result.png")

    content = md_file.read_text()
    assert "# Header\n" in content
    assert "![Image](result.png)\n" in content
    assert "Some text that mentions target.png in prose.\n" in content
    assert "Another paragraph.\n" in content


def should_handle_empty_alt_text(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("![](image.png)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![](image.png)",
        image_path=Path("image.png"),
        ref_type="image"
    )]

    update_references(refs, "image.png", "photo.png")

    assert md_file.read_text() == "![](photo.png)\n"


def should_report_correct_replacement_counts(tmp_path):
    file1 = tmp_path / "one.md"
    file1.write_text("![A](old.png)\n![B](old.png)\n")

    file2 = tmp_path / "two.md"
    file2.write_text("![[old.png]]\n")

    refs = [
        MarkdownReference(
            file_path=file1,
            line_number=1,
            original_text="![A](old.png)",
            image_path=Path("old.png"),
            ref_type="image"
        ),
        MarkdownReference(
            file_path=file1,
            line_number=2,
            original_text="![B](old.png)",
            image_path=Path("old.png"),
            ref_type="image"
        ),
        MarkdownReference(
            file_path=file2,
            line_number=1,
            original_text="![[old.png]]",
            image_path=Path("old.png"),
            ref_type="wiki_embed"
        ),
    ]

    updates = update_references(refs, "old.png", "new.png")

    assert len(updates) == 2
    file1_update = next(u for u in updates if u.file_path == file1)
    file2_update = next(u for u in updates if u.file_path == file2)
    assert file1_update.replacement_count == 2
    assert file2_update.replacement_count == 1


def should_update_url_encoded_references(tmp_path):
    md_file = tmp_path / "doc.md"
    md_file.write_text("![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![One](Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png)",
        image_path=Path("Screenshot%202025-11-02%20at%201.00.29%E2%80%AFPM.png"),
        ref_type="image"
    )]

    updates = update_references(refs, "Screenshot 2025-11-02 at 1.00.29 PM.png", "new-name.png")

    assert len(updates) == 1
    content = md_file.read_text()
    assert "new-name.png" in content
    assert "Screenshot" not in content


def should_preserve_url_encoding_in_updates(tmp_path):
    md_file = tmp_path / "encoded.md"
    md_file.write_text("![Image](my%20photo.jpg)\n")

    refs = [MarkdownReference(
        file_path=md_file,
        line_number=1,
        original_text="![Image](my%20photo.jpg)",
        image_path=Path("my%20photo.jpg"),
        ref_type="image"
    )]

    updates = update_references(refs, "my photo.jpg", "renamed-photo.jpg")

    assert len(updates) == 1
    content = md_file.read_text()
    assert "renamed-photo.jpg" in content or "renamed%2Dphoto.jpg" in content
