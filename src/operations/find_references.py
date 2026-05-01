"""Find markdown references to images."""
import re
from pathlib import Path
from urllib.parse import unquote

from .models import MarkdownReference
from .ports import MarkdownFilePort
from .text_utils import (
    normalized_name_equals,
    STANDARD_IMAGE_PATTERN,
    STANDARD_LINK_PATTERN,
    WIKI_EMBED_PATTERN,
    WIKI_LINK_PATTERN,
)


def find_references(
    image_path: Path,
    refs_root: Path,
    markdown_files: MarkdownFilePort,
    *,
    recursive: bool = True
) -> list[MarkdownReference]:
    """Find all markdown references to an image file.

    Scans markdown files under refs_root for references to the given image.
    Supports standard Markdown syntax and Obsidian wiki links:
    - Standard image: ![alt](path/to/image.png)
    - Standard link: [text](path/to/image.png)
    - Wiki link: [[image.png]], [[image.png|alias]]
    - Wiki embed: ![[image.png]], ![[image.png|alias]]
    """
    references = []
    image_name = image_path.name
    patterns = _get_reference_patterns()

    for md_file in markdown_files.find_markdown_files(refs_root, recursive=recursive):
        content = markdown_files.read_markdown_content(md_file)
        lines = content.splitlines(keepends=True)

        for line_num, line in enumerate(lines, start=1):
            refs = _find_references_in_line(line, line_num, md_file, image_path, image_name, patterns)
            references.extend(refs)

    return references


def _get_reference_patterns() -> dict[str, re.Pattern[str]]:
    return {
        'image': re.compile(STANDARD_IMAGE_PATTERN),
        'link': re.compile(r'(?<!!)' + STANDARD_LINK_PATTERN),
        'wiki_embed': re.compile(WIKI_EMBED_PATTERN),
        'wiki_link': re.compile(r'(?<!!)' + WIKI_LINK_PATTERN),
    }


def _find_references_in_line(
    line: str,
    line_num: int,
    md_file: Path,
    image_path: Path,
    image_name: str,
    patterns: dict[str, re.Pattern[str]]
) -> list[MarkdownReference]:
    refs = []

    # Check standard markdown (images and links)
    for ref_type in ['image', 'link']:
        for match in patterns[ref_type].finditer(line):
            ref_path = Path(match.group(2))
            if _matches_image(ref_path, image_path, image_name):
                refs.append(MarkdownReference(
                    file_path=md_file,
                    line_number=line_num,
                    original_text=match.group(0),
                    image_path=ref_path,
                    ref_type=ref_type
                ))

    # Check wiki-style (embeds and links)
    for ref_type in ['wiki_embed', 'wiki_link']:
        for match in patterns[ref_type].finditer(line):
            ref_name = match.group(1)
            if ref_name == image_name or ref_name == image_path.stem:
                refs.append(MarkdownReference(
                    file_path=md_file,
                    line_number=line_num,
                    original_text=match.group(0),
                    image_path=Path(ref_name),
                    ref_type=ref_type
                ))

    return refs


def _names_match(ref_name: str, target_name: str) -> bool:
    if ref_name == target_name:
        return True
    if Path(ref_name).stem == Path(target_name).stem:
        return True
    if normalized_name_equals(ref_name, target_name):
        return True
    if normalized_name_equals(Path(ref_name).stem, Path(target_name).stem):
        return True
    return False


def _matches_image(ref_path: Path, image_path: Path, image_name: str) -> bool:
    if _names_match(str(ref_path.name), image_name):
        return True

    try:
        if ref_path.resolve() == image_path.resolve():
            return True
    except (OSError, ValueError):
        pass

    try:
        decoded_path = Path(unquote(str(ref_path)))
        if decoded_path.resolve() == image_path.resolve():
            return True
    except (OSError, ValueError, TypeError):
        pass

    return False


def ref_matches_filename(ref: MarkdownReference, filename: str) -> bool:
    """Check if a markdown reference matches a given filename.

    Handles URL-encoded paths and Unicode whitespace normalization.
    Used during batch reference updates to match references by old filename.
    """
    return _names_match(str(ref.image_path.name), filename)
