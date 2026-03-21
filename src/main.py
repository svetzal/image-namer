"""image-namer CLI entry point.

This module defines the Typer application and all CLI commands.
Command logic is kept thin; all business logic lives in operations/.
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

from constants import SUPPORTED_EXTENSIONS
from operations.batch_references import apply_batch_reference_updates, count_batch_references
from operations.find_references import find_references
from operations.generate_name import generate_name
from operations.models import (
    NameAssessment,
    ProcessingResult,
    ProposedName,
    RenameStatus,
)
from operations.process_folder import compute_statistics, process_folder
from operations.process_image import normalize_extension
from operations.update_references import update_references
from utils.fs import collect_image_files, ensure_cache_layout, next_available_name

# Runtime Python version enforcement (see REVIEW.md #12)
if sys.version_info < (3, 13):  # pragma: no cover - defensive
    raise RuntimeError("Requires Python 3.13+")

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
    """Validate that provider is supported.

    Args:
        provider: The provider name to validate.

    Raises:
        typer.Exit: If provider is invalid.
    """
    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)


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


def _display_results_table(results: list[ProcessingResult], dry_run: bool) -> None:
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
        RenameStatus.RENAMED: "✓ rename",
        RenameStatus.UNCHANGED: "= unchanged",
        RenameStatus.COLLISION: "⚠ collision",
        RenameStatus.ERROR: "✗ error",
    }

    for result in results:
        status_display = status_display_map.get(result.status, result.status.value)
        table.add_row(
            result.source,
            result.proposed,
            result.final,
            status_display,
        )

    console.print(table)


def _print_statistics(results: list[ProcessingResult]) -> None:
    """Print summary statistics for processed files.

    Args:
        results: List of processing results.
    """
    stats = compute_statistics(results)
    console.print(
        f"\n[dim]Summary: {stats[RenameStatus.RENAMED]} renamed, "
        f"{stats[RenameStatus.UNCHANGED]} unchanged, "
        f"{stats[RenameStatus.COLLISION]} collision(s), {stats[RenameStatus.ERROR]} error(s)[/dim]"
    )


def _apply_renames(results: list[ProcessingResult]) -> None:
    """Apply the renames to the filesystem.

    Args:
        results: List of processing results.
    """
    for result in results:
        if result.status in (RenameStatus.RENAMED, RenameStatus.COLLISION) and result.path:
            img_path = result.path
            final_path = img_path.with_name(result.final)
            if final_path != img_path:
                img_path.rename(final_path)
    console.print("[green]✓ All renames applied.[/green]")


def _get_or_assess_current_name(
    path: Path, analysis_cache_dir: Path, provider: str, model: str, llm: LLMBroker
) -> NameAssessment:
    """Assess if current filename is already suitable (with caching).

    Args:
        path: Image file path.
        analysis_cache_dir: Directory for analysis cache.
        provider: LLM provider name.
        model: Model name.
        llm: LLM broker instance.

    Returns:
        NameAssessment instance.

    Raises:
        typer.Exit: If assessment fails.
    """
    from operations.assess_name import assess_name
    from operations.cache import load_assessment_from_cache, save_assessment_to_cache

    current_name = path.name
    current_proposed = ProposedName(stem=path.stem, extension=path.suffix)

    assessment = load_assessment_from_cache(analysis_cache_dir, path, current_name, provider, model)

    if assessment is None:
        try:
            assessment = assess_name(path, current_proposed, llm=llm)
            save_assessment_to_cache(analysis_cache_dir, path, current_name, provider, model, assessment)
        except Exception as e:
            console.print(f"[red]Error assessing filename: {e}[/red]")
            raise typer.Exit(1)

    return assessment


def _get_or_generate_new_name(
    path: Path, names_cache_dir: Path, provider: str, model: str, llm: LLMBroker
) -> ProposedName:
    """Generate a new proposed name (with caching).

    Args:
        path: Image file path.
        names_cache_dir: Directory for names cache.
        provider: LLM provider name.
        model: Model name.
        llm: LLM broker instance.

    Returns:
        ProposedName instance.

    Raises:
        typer.Exit: If name generation fails.
    """
    from operations.cache import load_from_cache, save_to_cache

    proposed = load_from_cache(names_cache_dir, path, provider, model)

    if proposed is None:
        try:
            proposed = generate_name(path, llm=llm)
            save_to_cache(names_cache_dir, path, provider, model, proposed)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    return proposed


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
        None, "--refs-root", help="Root directory for reference updates (defaults to file's directory)",
        file_okay=False
    ),
) -> None:
    """Rename a single file based on its visual contents.

    Validates types, calls vision naming, enforces idempotency, resolves collisions,
    and optionally renames the file when --apply is used.
    """
    _validate_file_type(path)
    _validate_provider(provider)

    cache_root = ensure_cache_layout(Path.cwd())
    analysis_cache_dir = cache_root / "cache" / "analysis"
    names_cache_dir = cache_root / "cache" / "names"

    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error setting up LLM: {e}[/red]")
        raise typer.Exit(1)

    assessment = _get_or_assess_current_name(path, analysis_cache_dir, provider, model, llm)

    if assessment.suitable:
        final_name = path.name
        mode_label = "unchanged"
        proposed_stem = path.stem
        proposed_ext = path.suffix
    else:
        proposed = _get_or_generate_new_name(path, names_cache_dir, provider, model, llm)
        proposed_stem = proposed.stem
        proposed_ext = normalize_extension(proposed.extension, path.suffix)
        final_name, mode_label = _determine_final_name(path, proposed_stem, proposed_ext)

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

    _handle_reference_updates(path, final_name, update_refs, refs_root, dry_run)

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
        None, "--refs-root", help="Root directory for reference updates (defaults to file's directory)",
        file_okay=False
    ),
) -> None:
    """Rename all images in a directory based on their visual contents.

    Processes all supported image files in the directory (flat by default, or
    recursively with --recursive). Shows a summary table of all renames.
    """
    _validate_provider(provider)

    image_files = collect_image_files(path, recursive)
    if not image_files:
        console.print(f"[yellow]No supported image files found in {path}[/yellow]")
        raise typer.Exit(0)

    console.print(f"[dim]Found {len(image_files)} image(s) to process...[/dim]")

    cache_root = ensure_cache_layout(Path.cwd())

    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error setting up LLM: {e}[/red]")
        raise typer.Exit(1)

    results = process_folder(image_files, llm, cache_root, provider, model)

    _display_results_table(results, dry_run)
    _print_statistics(results)

    if update_refs:
        search_root = refs_root if refs_root else path
        if dry_run:
            ref_result = count_batch_references(results, search_root)
        else:
            ref_result = apply_batch_reference_updates(results, search_root)

        if ref_result.total_references == 0:
            console.print("[dim]No markdown references found[/dim]")
        elif dry_run:
            console.print(
                f"[dim]Would update {ref_result.total_references} reference(s) "
                f"across {ref_result.files_updated} file(s)[/dim]"
            )
        else:
            console.print(
                f"[green]Updated {ref_result.total_references} reference(s) "
                f"across {ref_result.files_updated} file(s)[/green]"
            )

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
    _validate_file_type(path)
    _validate_provider(provider)

    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)

        proposed = generate_name(path, llm=llm)
        proposed_name = proposed.filename
    except Exception as e:  # see REVIEW.md #7
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

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

    Raises:
        typer.Exit: If provider configuration is invalid.
    """
    if provider == "ollama":
        return OllamaGateway()
    else:
        if "OPENAI_API_KEY" not in os.environ:
            console.print("[red]OPENAI_API_KEY environment variable not set[/red]")
            raise typer.Exit(2)
        return OpenAIGateway(api_key=os.environ["OPENAI_API_KEY"])


def main() -> None:
    """Programmatic entry point for console_scripts wrappers."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
