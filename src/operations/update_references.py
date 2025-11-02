"""Update markdown references to renamed images."""
import re
from pathlib import Path
from urllib.parse import quote, unquote

from .models import MarkdownReference, ReferenceUpdate


def update_references(
    references: list[MarkdownReference],
    old_name: str,
    new_name: str
) -> list[ReferenceUpdate]:
    """Update markdown references to reflect a renamed image.

    Groups references by file and updates all references in each file.
    Preserves alt text, link text, and Obsidian aliases.

    Args:
        references: List of MarkdownReference objects to update.
        old_name: Original filename (including extension).
        new_name: New filename (including extension).

    Returns:
        List of ReferenceUpdate objects describing changes made.
    """
    if not references:
        return []

    # Group references by file
    refs_by_file: dict[Path, list[MarkdownReference]] = {}
    for ref in references:
        if ref.file_path not in refs_by_file:
            refs_by_file[ref.file_path] = []
        refs_by_file[ref.file_path].append(ref)

    updates = []

    # Update each file
    for file_path, file_refs in refs_by_file.items():
        replacement_count = _update_file(file_path, file_refs, old_name, new_name)
        if replacement_count > 0:
            updates.append(ReferenceUpdate(
                file_path=file_path,
                replacement_count=replacement_count
            ))

    return updates


def _update_file(
    file_path: Path,
    references: list[MarkdownReference],
    old_name: str,
    new_name: str
) -> int:
    """Update all references in a single file.

    Args:
        file_path: Path to the markdown file.
        references: List of references in this file.
        old_name: Original filename.
        new_name: New filename.

    Returns:
        Number of replacements made.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    replacement_count = 0

    # Sort references by line number to ensure consistent processing
    sorted_refs = sorted(references, key=lambda r: r.line_number)

    for ref in sorted_refs:
        new_text = _generate_replacement(ref, old_name, new_name)
        if new_text != ref.original_text:
            # Use regex to ensure we only replace exact matches
            pattern = re.escape(ref.original_text)
            content, count = re.subn(pattern, new_text, content, count=1)
            replacement_count += count

    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return replacement_count


def _generate_replacement(
    ref: MarkdownReference,
    old_name: str,
    new_name: str
) -> str:
    """Generate the replacement text for a reference.

    Preserves alt text, link text, and aliases while updating the filename.

    Args:
        ref: The reference to update.
        old_name: Original filename.
        new_name: New filename.

    Returns:
        The replacement text.
    """
    handlers = {
        'image': _replace_standard_image,
        'link': _replace_standard_link,
        'wiki_embed': _replace_wiki_embed,
        'wiki_link': _replace_wiki_link,
    }

    handler = handlers.get(ref.ref_type)
    if handler:
        result = handler(ref.original_text, old_name, new_name)
        if result:
            return result

    return ref.original_text


def _replace_in_path(path_str: str, old_name: str, new_name: str) -> str:
    """Replace filename in a path string, handling URL encoding.

    Args:
        path_str: The path string (may be URL-encoded).
        old_name: Original filename.
        new_name: New filename.

    Returns:
        Updated path string with same encoding as original.
    """
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

            # Try with space normalization (handle Unicode spaces)
            normalized_decoded = _normalize_spaces_for_replacement(decoded)
            normalized_old = _normalize_spaces_for_replacement(old_name)
            if normalized_old in normalized_decoded:
                new_decoded = decoded.replace(
                    _find_substring_with_different_spaces(decoded, old_name),
                    new_name
                )
                return quote(new_decoded, safe='/')
    except Exception:
        pass

    # Fall back to simple string replacement
    return path_str.replace(old_name, new_name)


def _normalize_spaces_for_replacement(text: str) -> str:
    """Normalize spaces for comparison purposes.

    Args:
        text: Text to normalize.

    Returns:
        Text with normalized spaces.
    """
    import unicodedata
    normalized = unicodedata.normalize('NFKC', text)
    return ' '.join(normalized.split())


def _find_substring_with_different_spaces(haystack: str, needle: str) -> str:
    """Find a substring that matches after space normalization.

    Args:
        haystack: String to search in.
        needle: String to search for (with regular spaces).

    Returns:
        The actual substring from haystack, or needle if not found.
    """
    # Normalize the needle for comparison
    normalized_needle = _normalize_spaces_for_replacement(needle)

    # Slide through haystack to find a match
    for i in range(len(haystack) - len(needle) + 1):
        substring = haystack[i:i+len(needle)]
        if _normalize_spaces_for_replacement(substring) == normalized_needle:
            return substring

    return needle


def _replace_standard_image(original_text: str, old_name: str, new_name: str) -> str | None:
    """Replace filename in standard Markdown image: ![alt](path)."""
    match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', original_text)
    if match:
        alt_text = match.group(1)
        old_path = match.group(2)
        new_path = _replace_in_path(old_path, old_name, new_name)
        return f"![{alt_text}]({new_path})"
    return None


def _replace_standard_link(original_text: str, old_name: str, new_name: str) -> str | None:
    """Replace filename in standard Markdown link: [text](path)."""
    match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', original_text)
    if match:
        link_text = match.group(1)
        old_path = match.group(2)
        new_path = _replace_in_path(old_path, old_name, new_name)
        return f"[{link_text}]({new_path})"
    return None


def _replace_wiki_embed(original_text: str, old_name: str, new_name: str) -> str | None:
    """Replace filename in Obsidian wiki embed: ![[name]] or ![[name|alias]]."""
    match = re.match(r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', original_text)
    if match:
        old_ref = match.group(1)
        alias = match.group(2)
        new_ref = _replace_wiki_name(old_ref, old_name, new_name)
        if alias:
            return f"![[{new_ref}|{alias}]]"
        return f"![[{new_ref}]]"
    return None


def _replace_wiki_link(original_text: str, old_name: str, new_name: str) -> str | None:
    """Replace filename in Obsidian wiki link: [[name]] or [[name|alias]]."""
    match = re.match(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', original_text)
    if match:
        old_ref = match.group(1)
        alias = match.group(2)
        new_ref = _replace_wiki_name(old_ref, old_name, new_name)
        if alias:
            return f"[[{new_ref}|{alias}]]"
        return f"[[{new_ref}]]"
    return None


def _replace_wiki_name(wiki_ref: str, old_name: str, new_name: str) -> str:
    """Replace filename in a wiki-style reference.

    Handles both full filename and stem-only references.

    Args:
        wiki_ref: The wiki reference (e.g., 'image.png' or 'image').
        old_name: Original filename with extension.
        new_name: New filename with extension.

    Returns:
        Updated wiki reference.
    """
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
