"""image-namer CLI entry point.

This module defines the Typer application and all CLI commands.
Command logic is kept here for simplicity; business logic lives in operations/.
"""

import os
import sys
from pathlib import Path
from typing import Final, Literal

import typer
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from operations.find_references import find_references
from operations.generate_name import generate_name
from operations.update_references import update_references
from utils.fs import next_available_name

# Runtime Python version enforcement (see REVIEW.md #12)
if sys.version_info < (3, 13):  # pragma: no cover - defensive
    raise RuntimeError("Requires Python 3.13+")

SUPPORTED_EXTENSIONS: Final[set[str]] = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}
SUPPORTED_PROVIDERS: Final[set[str]] = {"ollama", "openai"}

app = typer.Typer(help="Rename image files based on their visual contents.")
console = Console()


def _validate_file_type(path: Path) -> None:
    """Validate that file is a supported image type.

    Args:
        path: Path to the file to validate.

    Raises:
        typer.Exit: If file type is not supported.
    """
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        console.print(
            f"[red]Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}[/red]"
        )
        raise typer.Exit(2)


def _validate_provider(provider: str) -> None:
    """Validate that provider is supported and configured.

    Args:
        provider: The provider name to validate.

    Raises:
        typer.Exit: If provider is invalid or not configured.
    """
    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)

    if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
        console.print("[red]OPENAI_API_KEY environment variable not set[/red]")
        raise typer.Exit(2)


def _normalize_extension(proposed_ext: str, fallback_ext: str) -> str:
    """Normalize extension to include leading dot.

    Args:
        proposed_ext: The proposed extension (may or may not have leading dot).
        fallback_ext: Fallback extension to use if proposed is empty.

    Returns:
        Extension with leading dot.
    """
    if not proposed_ext:
        return fallback_ext
    if proposed_ext.startswith("."):
        return proposed_ext
    return f".{proposed_ext}"


def _determine_final_name(path: Path, proposed_stem: str, proposed_ext: str) -> tuple[str, str]:
    """Determine final filename after idempotency and collision checks.

    Args:
        path: Original file path.
        proposed_stem: Proposed stem from LLM.
        proposed_ext: Proposed extension (with leading dot).

    Returns:
        Tuple of (final_name, mode_label).
    """
    current_stem = path.stem
    if current_stem == proposed_stem:
        return path.name, "unchanged"

    candidate = f"{proposed_stem}{proposed_ext}"
    if (path.parent / candidate).exists():
        final_name = next_available_name(path.parent, proposed_stem, proposed_ext)
        return final_name, "collision-resolved"

    return candidate, "proposed"


def _handle_reference_updates(
    path: Path,
    final_name: str,
    update_refs: bool,
    refs_root: Path | None,
    dry_run: bool
) -> None:
    """Handle updating markdown references if requested.

    Args:
        path: Original file path.
        final_name: Final filename after rename.
        update_refs: Whether to update references.
        refs_root: Root directory to search for references.
        dry_run: Whether in dry-run mode.
    """
    if not update_refs or final_name == path.name:
        return

    search_root = refs_root if refs_root else path.parent
    refs = find_references(path, search_root, recursive=True)

    if refs:
        if not dry_run:
            updates = update_references(refs, path.name, final_name)
            total_replacements = sum(u.replacement_count for u in updates)
            console.print(
                f"[green]Updated {total_replacements} reference(s) "
                f"across {len(updates)} file(s)[/green]"
            )
        else:
            console.print(
                f"[dim]Would update {len(refs)} reference(s) "
                f"across {len(set(r.file_path for r in refs))} file(s)[/dim]"
            )
    else:
        console.print("[dim]No markdown references found[/dim]")


def _collect_image_files(path: Path, recursive: bool) -> list[Path]:
    """Collect all image files in a directory.

    Args:
        path: Directory to search.
        recursive: Whether to search recursively.

    Returns:
        List of image file paths.
    """
    if recursive:
        return [p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]


def _process_single_image(
    img_path: Path,
    llm: LLMBroker,
    planned_names: set[str]
) -> dict:
    """Process a single image file to determine its new name.

    Args:
        img_path: Path to the image file.
        llm: LLM broker for name generation.
        planned_names: Set of already planned filenames to avoid collisions.

    Returns:
        Dictionary with processing result.
    """
    try:
        proposed = generate_name(img_path, llm=llm)
    except Exception as e:
        console.print(f"[red]Error processing {img_path.name}: {e}[/red]")
        return {
            "source": img_path.name,
            "proposed": "ERROR",
            "final": img_path.name,
            "status": "error",
        }

    proposed_stem = proposed.stem
    proposed_ext = _normalize_extension(proposed.extension, img_path.suffix)

    # Check idempotency
    if img_path.stem == proposed_stem:
        return {
            "source": img_path.name,
            "proposed": f"{proposed_stem}{proposed_ext}",
            "final": img_path.name,
            "status": "unchanged",
            "path": img_path,
        }

    # Resolve collisions
    candidate = f"{proposed_stem}{proposed_ext}"
    if (img_path.parent / candidate).exists() or candidate in planned_names:
        final_name = _find_next_available_in_batch(
            img_path.parent, proposed_stem, proposed_ext, planned_names
        )
        status = "collision"
    else:
        final_name = candidate
        status = "renamed"

    planned_names.add(final_name)

    return {
        "source": img_path.name,
        "proposed": f"{proposed_stem}{proposed_ext}",
        "final": final_name,
        "status": status,
        "path": img_path,
    }


def _find_next_available_in_batch(
    directory: Path,
    stem: str,
    ext: str,
    planned_names: set[str]
) -> str:
    """Find next available filename considering both disk and planned renames.

    Args:
        directory: Directory to check for existing files.
        stem: Base filename stem.
        ext: File extension with leading dot.
        planned_names: Set of already planned filenames.

    Returns:
        Next available filename.
    """
    suffix_num = 2
    while True:
        test_name = f"{stem}-{suffix_num}{ext}"
        if not (directory / test_name).exists() and test_name not in planned_names:
            return test_name
        suffix_num += 1


def _display_results_table(results: list[dict], dry_run: bool) -> None:
    """Display results in a formatted table.

    Args:
        results: List of processing results.
        dry_run: Whether in dry-run mode.
    """
    table = Table(title=f"image-namer: folder ({'dry-run' if dry_run else 'apply'})")
    table.add_column("Source", style="dim")
    table.add_column("Proposed", style="bold")
    table.add_column("Final", style="green")
    table.add_column("Status", style="cyan")

    status_display_map = {
        "renamed": "✓ rename",
        "unchanged": "= unchanged",
        "collision": "⚠ collision",
        "error": "✗ error",
    }

    for result in results:
        status_display = status_display_map.get(result["status"], result["status"])
        table.add_row(
            result["source"],
            result["proposed"],
            result["final"],
            status_display,
        )

    console.print(table)


def _print_statistics(results: list[dict]) -> None:
    """Print summary statistics for processed files.

    Args:
        results: List of processing results.
    """
    status_counts = ["renamed", "unchanged", "collision", "error"]
    stats = {
        status: sum(1 for r in results if r["status"] == status)
        for status in status_counts
    }
    console.print(
        f"\n[dim]Summary: {stats['renamed']} renamed, "
        f"{stats['unchanged']} unchanged, "
        f"{stats['collision']} collision(s), {stats['error']} error(s)[/dim]"
    )


def _handle_batch_reference_updates(
    results: list[dict],
    search_root: Path,
    dry_run: bool
) -> None:
    """Handle reference updates for batch processing.

    Args:
        results: List of processing results.
        search_root: Root directory to search for references.
        dry_run: Whether in dry-run mode.
    """
    all_refs = []
    rename_map = {}

    for result in results:
        if result["status"] in ["renamed", "collision"] and "path" in result:
            img_path = result["path"]
            if result["final"] != img_path.name:
                refs = find_references(img_path, search_root, recursive=True)
                all_refs.extend(refs)
                rename_map[img_path.name] = result["final"]

    if not all_refs:
        console.print("[dim]No markdown references found[/dim]")
        return

    if not dry_run:
        updates_by_file = {}
        for old_name, new_name in rename_map.items():
            file_refs = [
                r for r in all_refs
                if r.image_path.name == old_name or r.image_path.stem == Path(old_name).stem
            ]
            if file_refs:
                file_updates = update_references(file_refs, old_name, new_name)
                for upd in file_updates:
                    if upd.file_path not in updates_by_file:
                        updates_by_file[upd.file_path] = 0
                    updates_by_file[upd.file_path] += upd.replacement_count

        total_replacements = sum(updates_by_file.values())
        console.print(
            f"[green]Updated {total_replacements} reference(s) "
            f"across {len(updates_by_file)} file(s)[/green]"
        )
    else:
        unique_files = len(set(r.file_path for r in all_refs))
        console.print(
            f"[dim]Would update {len(all_refs)} reference(s) "
            f"across {unique_files} file(s)[/dim]"
        )


def _apply_renames(results: list[dict]) -> None:
    """Apply the renames to the filesystem.

    Args:
        results: List of processing results.
    """
    for result in results:
        if result["status"] in ["renamed", "collision"] and "path" in result:
            img_path = result["path"]
            final_path = img_path.with_name(result["final"])
            if final_path != img_path:
                img_path.rename(final_path)
    console.print("[green]✓ All renames applied.[/green]")


@app.command()
def file(
    path: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to an image file"
    ),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Model provider: ollama or openai",
        envvar="LLM_PROVIDER",
    ),
    model: str = typer.Option(
        "gemma3:27b",
        "--model",
        help="Visual model to use (default aligns with Ollama gemma3:27b)",
        envvar="LLM_MODEL",
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Preview only vs. actually rename"
    ),
    update_refs: bool = typer.Option(
        False, "--update-refs/--no-update-refs", help="Update markdown/wiki references when renaming"
    ),
    refs_root: Path | None = typer.Option(
        None, "--refs-root", help="Root directory for reference updates (defaults to file's directory)", file_okay=False
    ),
) -> None:
    """Rename a single file based on its visual contents.

    Validates types, calls vision naming, enforces idempotency, resolves collisions,
    and optionally renames the file when --apply is used.
    """
    _validate_file_type(path)
    _validate_provider(provider)

    # Prepare LLM and propose name
    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
        proposed = generate_name(path, llm=llm)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Normalize proposed name
    proposed_stem = proposed.stem
    proposed_ext = _normalize_extension(proposed.extension, path.suffix)

    # Determine final name (idempotency + collision resolution)
    final_name, mode_label = _determine_final_name(path, proposed_stem, proposed_ext)

    # Show output panel
    console.print(
        Panel.fit(
            f"[dim]Source[/]: {path.name}\n"
            f"[bold]Proposed[/]: {proposed_stem}{proposed_ext}\n"
            f"[bold]Final[/]: {final_name}\n"
            f"[dim]Provider[/]: {provider}  [dim]Model[/]: {model}  [dim]Mode[/]: "
            f"{'dry-run' if dry_run else 'apply'} ({mode_label})",
            title="image-namer: file",
            border_style="green",
        )
    )

    # Update markdown references if requested
    _handle_reference_updates(path, final_name, update_refs, refs_root, dry_run)

    # Apply rename if not in dry-run mode
    if not dry_run and final_name != path.name:
        path.rename(path.with_name(final_name))


@app.command()
def folder(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, readable=True, help="Path to a directory containing images"
    ),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Model provider: ollama or openai",
        envvar="LLM_PROVIDER",
    ),
    model: str = typer.Option(
        "gemma3:27b",
        "--model",
        help="Visual model to use (default aligns with Ollama gemma3:27b)",
        envvar="LLM_MODEL",
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Preview only vs. actually rename"
    ),
    recursive: bool = typer.Option(
        False, "--recursive", help="Process subdirectories recursively"
    ),
    update_refs: bool = typer.Option(
        False, "--update-refs/--no-update-refs", help="Update markdown/wiki references when renaming"
    ),
    refs_root: Path | None = typer.Option(
        None, "--refs-root", help="Root directory for reference updates (defaults to file's directory)", file_okay=False
    ),
) -> None:
    """Rename all images in a directory based on their visual contents.

    Processes all supported image files in the directory (flat by default, or
    recursively with --recursive). Shows a summary table of all renames.
    """
    _validate_provider(provider)

    # Collect and validate image files
    image_files = _collect_image_files(path, recursive)
    if not image_files:
        console.print(f"[yellow]No supported image files found in {path}[/yellow]")
        raise typer.Exit(0)

    console.print(f"[dim]Found {len(image_files)} image(s) to process...[/dim]")

    # Prepare LLM
    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
    except Exception as e:
        console.print(f"[red]Error setting up LLM: {e}[/red]")
        raise typer.Exit(1)

    # Process all images
    planned_names: set[str] = set()
    results = [_process_single_image(img, llm, planned_names) for img in image_files]

    # Display results
    _display_results_table(results, dry_run)
    _print_statistics(results)

    # Handle reference updates
    if update_refs:
        search_root = refs_root if refs_root else path
        _handle_batch_reference_updates(results, search_root, dry_run)

    # Apply renames
    if not dry_run:
        _apply_renames(results)


@app.command()
def generate(
    path: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to an image file"
    ),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Model provider: ollama or openai",
        envvar="LLM_PROVIDER",
    ),
    model: str = typer.Option(
        "gemma3:27b",
        "--model",
        help="Visual model to use (default aligns with Ollama gemma3:27b)",
        envvar="LLM_MODEL",
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Preview only vs. actually rename"
    ),
) -> None:
    """Propose a new filename for a given image file.

    Analyzes the image using a vision model and proposes a content-based filename.
    The file is never modified in dry-run mode (default).

    Args:
        path: Path to the image file.
        provider: LLM provider to use (defaults to `ollama`).
        model: Visual model identifier (defaults to `gemma3:27b`).
        dry_run: When true, only prints the proposal; `--apply` reserved for future.
    """
    # Validate file is an image we support (see REVIEW.md #8)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        console.print(
            f"[red]Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}[/red]"
        )
        raise typer.Exit(2)

    # Validate provider and setup (see REVIEW.md #9)
    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)

    if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
        console.print("[red]OPENAI_API_KEY environment variable not set[/red]")
        raise typer.Exit(2)

    # Create gateway and LLM broker
    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)

        # Generate filename proposal
        proposed = generate_name(path, llm=llm)
        proposed_name = proposed.filename
    except Exception as e:  # see REVIEW.md #7
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Display results
    console.print(
        Panel.fit(
            f"[bold]Proposed[/]: {proposed_name}\n"
            f"[dim]Source[/]: {path.name}\n"
            f"[dim]Provider[/]: {provider}  [dim]Model[/]: {model}  [dim]Mode[/]: "
            f"{'dry-run' if dry_run else 'apply'}",
            title="image-namer: generate",
            border_style="cyan",
        )
    )

    if not dry_run:
        console.print("[yellow]Apply mode is not implemented yet. No changes made.[/]")


def _get_gateway(provider: Literal["openai", "ollama"]) -> OllamaGateway | OpenAIGateway:
    """Create the appropriate LLM gateway for the given provider.

    Args:
        provider: Either "ollama" or "openai"

    Returns:
        Gateway instance for the specified provider
    """
    if provider == "ollama":
        return OllamaGateway()
    else:
        return OpenAIGateway(api_key=os.environ["OPENAI_API_KEY"])


def main() -> None:
    """Programmatic entry point for console_scripts wrappers."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
