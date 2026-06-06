"""Find markdown references to images."""
import logging
import re
from pathlib import Path

from operations.models import MarkdownReference
from operations.ports import MarkdownFilePort
from operations.text_utils import (
    names_match,
    ref_path_matches_image,
    REFERENCE_PATTERNS,
    WIKI_REF_TYPES,
)

logger = logging.getLogger(__name__)


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
    image_name = image_path.name
    patterns = _get_reference_patterns()

    return [
        ref
        for md_file in markdown_files.find_markdown_files(refs_root, recursive=recursive)
        for line_num, line in enumerate(
            markdown_files.read_markdown_content(md_file).splitlines(keepends=True), start=1
        )
        for ref in _find_references_in_line(line, line_num, md_file, image_path, image_name, patterns)
    ]


def _get_reference_patterns() -> dict[str, re.Pattern[str]]:
    return {
        ref_type: re.compile(
            (r'(?<!!)' if not pattern.startswith('!') else '') + pattern
        )
        for ref_type, pattern in REFERENCE_PATTERNS.items()
    }


def _match_to_reference(
    ref_type: str,
    match: re.Match[str],
    md_file: Path,
    line_num: int,
    image_path: Path,
    image_name: str,
) -> MarkdownReference | None:
    if ref_type in WIKI_REF_TYPES:
        ref_name = match.group(1)
        if names_match(ref_name, image_name):
            return MarkdownReference(
                file_path=md_file,
                line_number=line_num,
                original_text=match.group(0),
                image_path=Path(ref_name),
                ref_type=ref_type,
            )
    else:
        ref_path = Path(match.group(2))
        if ref_path_matches_image(ref_path, image_path, image_name):
            return MarkdownReference(
                file_path=md_file,
                line_number=line_num,
                original_text=match.group(0),
                image_path=ref_path,
                ref_type=ref_type,
            )
    return None


def _find_references_in_line(
    line: str,
    line_num: int,
    md_file: Path,
    image_path: Path,
    image_name: str,
    patterns: dict[str, re.Pattern[str]]
) -> list[MarkdownReference]:
    candidates = (
        _match_to_reference(ref_type, match, md_file, line_num, image_path, image_name)
        for ref_type, pattern_re in patterns.items()
        for match in pattern_re.finditer(line)
    )
    return [ref for ref in candidates if ref is not None]


def ref_matches_filename(ref: MarkdownReference, filename: str) -> bool:
    """Check if a markdown reference matches a given filename.

    Handles URL-encoded paths and Unicode whitespace normalization.
    Used during batch reference updates to match references by old filename.
    """
    return names_match(str(ref.image_path.name), filename)
