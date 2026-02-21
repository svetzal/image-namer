"""Find markdown references to images."""
import re
from pathlib import Path
from urllib.parse import unquote

from .models import MarkdownReference


def find_references(
    image_path: Path,
    refs_root: Path,
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

    Args:
        image_path: Path to the image file to find references to.
        refs_root: Root directory to search for markdown files.
        recursive: Whether to search subdirectories recursively.

    Returns:
        List of MarkdownReference objects found.
    """
    references = []
    image_name = image_path.name
    patterns = _get_reference_patterns()

    # Find all markdown files
    pattern = "**/*.md" if recursive else "*.md"
    for md_file in refs_root.glob(pattern):
        if not md_file.is_file():
            continue

        with open(md_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            refs = _find_references_in_line(line, line_num, md_file, image_path, image_name, patterns)
            references.extend(refs)

    return references


def _get_reference_patterns() -> dict[str, re.Pattern[str]]:
    """Get compiled regex patterns for markdown references.

    Returns:
        Dictionary mapping reference type to compiled pattern.
    """
    return {
        'image': re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
        'link': re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)'),
        'wiki_embed': re.compile(r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'),
        'wiki_link': re.compile(r'(?<!!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'),
    }


def _find_references_in_line(
    line: str,
    line_num: int,
    md_file: Path,
    image_path: Path,
    image_name: str,
    patterns: dict[str, re.Pattern[str]]
) -> list[MarkdownReference]:
    """Find all references in a single line.

    Args:
        line: The line to search.
        line_num: Line number (1-indexed).
        md_file: Path to the markdown file.
        image_path: Path to the image being searched for.
        image_name: Name of the image file.
        patterns: Compiled regex patterns.

    Returns:
        List of references found in the line.
    """
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


def _matches_image(ref_path: Path, image_path: Path, image_name: str) -> bool:
    """Check if a reference path matches the image being searched for.

    Args:
        ref_path: Path from the markdown reference.
        image_path: Full path to the image file.
        image_name: Name of the image file.

    Returns:
        True if the reference matches the image.
    """
    # Try direct match
    if ref_path.name == image_name:
        return True

    # Try URL-decoded matches
    if _matches_url_decoded(ref_path, image_path, image_name):
        return True

    # Match by full path
    if _matches_by_full_path(ref_path, image_path):
        return True

    return False


def _matches_url_decoded(ref_path: Path, image_path: Path, image_name: str) -> bool:
    """Check if URL-decoded reference matches the image.

    Args:
        ref_path: Path from the markdown reference.
        image_path: Full path to the image file.
        image_name: Name of the image file.

    Returns:
        True if matches after URL decoding.
    """
    try:
        decoded_name = unquote(str(ref_path.name))
        if decoded_name == image_name:
            return True
        # Also try normalizing whitespace (various Unicode spaces to regular space)
        if _normalize_spaces(decoded_name) == _normalize_spaces(image_name):
            return True
    except Exception:
        pass

    # Try URL-decoded full path
    try:
        decoded_path = Path(unquote(str(ref_path)))
        if decoded_path.name == image_name or decoded_path.resolve() == image_path.resolve():
            return True
    except Exception:
        pass

    return False


def _matches_by_full_path(ref_path: Path, image_path: Path) -> bool:
    """Check if reference matches by resolving full paths.

    Args:
        ref_path: Path from the markdown reference.
        image_path: Full path to the image file.

    Returns:
        True if resolved paths match.
    """
    try:
        return ref_path.resolve() == image_path.resolve()
    except (OSError, ValueError):
        return False


def _normalize_spaces(text: str) -> str:
    """Normalize all whitespace characters to regular spaces.

    Args:
        text: Text to normalize.

    Returns:
        Text with all Unicode whitespace normalized to ASCII space.
    """
    import unicodedata
    # Normalize Unicode (e.g., decompose combined characters)
    normalized = unicodedata.normalize('NFKC', text)
    # Replace all whitespace characters with regular space
    return ' '.join(normalized.split())
