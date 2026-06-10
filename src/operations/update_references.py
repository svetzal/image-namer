"""Update markdown references to renamed images."""
import logging
import re
from pathlib import Path
from urllib.parse import quote, unquote

from constants import FILESYSTEM_IO_ERRORS
from operations.models import MarkdownReference, ReferenceUpdate
from operations.ports import MarkdownFilePort
from operations.text_utils import (
    normalize_spaces,
    normalized_name_equals,
    REFERENCE_PATTERNS,
    WIKI_REF_TYPES,
    REF_TYPE_PREFIXES,
)

logger = logging.getLogger(__name__)


def update_references(
    references: list[MarkdownReference],
    old_name: str,
    new_name: str,
    markdown_files: MarkdownFilePort,
) -> list[ReferenceUpdate]:
    """Update markdown references to reflect a renamed image.

    Groups references by file and updates all references in each file.
    Preserves alt text, link text, and Obsidian aliases.
    """
    if not references:
        return []

    refs_by_file: dict[Path, list[MarkdownReference]] = {
        fp: [r for r in references if r.file_path == fp]
        for fp in dict.fromkeys(r.file_path for r in references)
    }

    updated = [
        (fp, _update_file(fp, file_refs, old_name, new_name, markdown_files))
        for fp, file_refs in refs_by_file.items()
    ]
    return [
        ReferenceUpdate(file_path=fp, replacement_count=count)
        for fp, count in updated
        if count > 0
    ]


def _update_file(
    file_path: Path,
    references: list[MarkdownReference],
    old_name: str,
    new_name: str,
    markdown_files: MarkdownFilePort,
) -> int:
    try:
        content = markdown_files.read_markdown_content(file_path)
        original_content = content
        replacement_count = 0

        sorted_refs = sorted(references, key=lambda r: r.line_number)

        for ref in sorted_refs:
            new_text = _generate_replacement(ref, old_name, new_name)
            if new_text != ref.original_text:
                pattern = re.escape(ref.original_text)
                content, count = re.subn(pattern, new_text, content, count=1)
                replacement_count += count

        if content != original_content:
            markdown_files.write_markdown_content(file_path, content)

        return replacement_count
    except FILESYSTEM_IO_ERRORS as e:
        logger.warning(
            "Failed to update references in %s: %s: %s", file_path, type(e).__name__, e
        )
        return 0


def _generate_replacement(
    ref: MarkdownReference,
    old_name: str,
    new_name: str
) -> str:
    """Preserves alt text, link text, and aliases while updating the filename."""
    pattern = REFERENCE_PATTERNS.get(ref.ref_type)
    if pattern is None:
        return ref.original_text

    prefix = REF_TYPE_PREFIXES[ref.ref_type]
    if ref.ref_type in WIKI_REF_TYPES:
        result = _replace_wiki_ref(pattern, prefix, ref.original_text, old_name, new_name)
    else:
        result = _replace_standard_ref(pattern, prefix, ref.original_text, old_name, new_name)

    return result if result else ref.original_text


def _replace_in_path(path_str: str, old_name: str, new_name: str) -> str:
    """Replace filename in a path string, handling URL encoding."""
    # Check if path is URL-encoded by trying to decode it
    try:
        decoded = unquote(path_str)
        # If decoded is different, the path was encoded
        if decoded != path_str:
            # Try direct replacement first
            if old_name in decoded:
                new_decoded = decoded.replace(old_name, new_name)
                # Re-encode using the same encoding scheme
                # Quote special chars but keep forward slashes
                return quote(new_decoded, safe='/')

            if normalized_name_equals(Path(decoded).name, old_name):
                new_decoded = decoded.replace(
                    _find_substring_with_different_spaces(decoded, old_name),
                    new_name
                )
                return quote(new_decoded, safe='/')
    except (ValueError, TypeError) as e:
        logger.debug(
            "URL decoding failed for path %r: %s: %s", path_str, type(e).__name__, e
        )

    # Fall back to simple string replacement
    return path_str.replace(old_name, new_name)


def _find_substring_with_different_spaces(haystack: str, needle: str) -> str:
    """Find a substring that matches after Unicode space normalization."""
    window = len(needle)
    normalized_needle = normalize_spaces(needle)
    for i in range(len(haystack) - window + 1):
        candidate = haystack[i:i + window]
        if normalize_spaces(candidate) == normalized_needle:
            return candidate
    return needle


def _replace_standard_ref(pattern: str, prefix: str, original_text: str, old_name: str, new_name: str) -> str | None:
    match = re.match(pattern, original_text)
    if match:
        text = match.group(1)
        old_path = match.group(2)
        new_path = _replace_in_path(old_path, old_name, new_name)
        return f"{prefix}[{text}]({new_path})"
    return None


def _replace_wiki_ref(pattern: str, prefix: str, original_text: str, old_name: str, new_name: str) -> str | None:
    match = re.match(pattern, original_text)
    if match:
        old_ref = match.group(1)
        alias = match.group(2)
        new_ref = _replace_wiki_name(old_ref, old_name, new_name)
        if alias:
            return f"{prefix}[[{new_ref}|{alias}]]"
        return f"{prefix}[[{new_ref}]]"
    return None


def _replace_wiki_name(wiki_ref: str, old_name: str, new_name: str) -> str:
    """Handles both full filename and stem-only references."""
    old_stem = Path(old_name).stem
    new_stem = Path(new_name).stem

    # If the reference matches the full filename, replace it
    if wiki_ref == old_name:
        return new_name

    # If the reference matches just the stem, replace with new stem
    if wiki_ref == old_stem:
        return new_stem

    # Otherwise return unchanged
    return wiki_ref
