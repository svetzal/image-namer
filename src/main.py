"""image-namer CLI entry point.

This module defines the Typer application and all CLI commands.
Command logic is kept thin; all business logic lives in operations/.
"""

import sys
from pathlib import Path
from typing import Annotated, Final

import typer
from rich.console import Console
from rich.panel import Panel

from constants import SUPPORTED_EXTENSIONS
from operations.adapters import FilesystemMarkdownFiles, FilesystemRenamer
from operations.apply_renames import apply_renames
from operations.batch_references import (
    apply_batch_reference_updates,
    apply_single_file_reference_updates,
    count_batch_references,
    count_single_file_references,
)
from operations.display import display_results_table, print_reference_result, print_statistics
from operations.gateway_factory import MissingApiKeyError
from operations.models import (
    ProcessingResult,
    RenameStatus,
)
from operations.pipeline_factory import AnalysisPipeline, build_analysis_pipeline
from operations.process_folder import process_folder
from operations.process_image import process_single_image
from utils.fs import collect_image_files, ensure_cache_layout

# Runtime Python version enforcement (see REVIEW.md #12)
if sys.version_info < (3, 13):  # pragma: no cover - defensive
    raise RuntimeError("Requires Python 3.13+")

SUPPORTED_PROVIDERS: Final[set[str]] = {"ollama", "openai"}

Provider = Annotated[str, typer.Option("--provider", help="Model provider: ollama or openai", envvar="LLM_PROVIDER")]
Model = Annotated[str, typer.Option(
    "--model", help="Visual model to use (default aligns with Ollama gemma3:27b)", envvar="LLM_MODEL"
)]
DryRun = Annotated[bool, typer.Option("--dry-run/--apply", help="Preview only vs. actually rename")]

app = typer.Typer(help="Rename image files based on their visual contents.")
console = Console()


def _validate_file_type(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        console.print(
            f"[red]Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}[/red]"
        )
        raise typer.Exit(2)


def _validate_provider(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)


def _build_pipeline_or_exit(provider: str, model: str, cache_root: Path) -> AnalysisPipeline:
    """Build analysis pipeline, exiting with an error message on failure."""
    try:
        return build_analysis_pipeline(provider, model, cache_root)
    except MissingApiKeyError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2)
    except (OSError, ConnectionError, ValueError, RuntimeError) as e:
        console.print(f"[red]Error setting up LLM: {e}[/red]")
        raise typer.Exit(1)


def _handle_reference_updates(
    path: Path,
    final_name: str,
    update_refs: bool,
    refs_root: Path | None,
    dry_run: bool
) -> None:
    if not update_refs or final_name == path.name:
        return
    search_root = refs_root if refs_root else path.parent
    markdown_files = FilesystemMarkdownFiles()
    if dry_run:
        ref_result = count_single_file_references(path, search_root, markdown_files)
    else:
        ref_result = apply_single_file_reference_updates(path, final_name, search_root, markdown_files)
    print_reference_result(console, ref_result, dry_run)


def _apply_renames(results: list[ProcessingResult]) -> None:
    apply_renames(results, FilesystemRenamer())
    console.print("[green]✓ All renames applied.[/green]")


def _apply_single_rename(path: Path, final_name: str) -> None:
    if final_name != path.name:
        FilesystemRenamer().rename(path, path.with_name(final_name))


def _process_single_file(path: Path, provider: str, model: str) -> ProcessingResult:
    """Validate, build pipeline, and process a single image file.

    Args:
        path: Path to the image file.
        provider: LLM provider name.
        model: Model identifier string.

    Returns:
        ProcessingResult for the image.

    Raises:
        typer.Exit: On unsupported file type, invalid provider, pipeline error, or processing error.
    """
    _validate_file_type(path)
    _validate_provider(provider)

    cache_root = ensure_cache_layout(Path.cwd())
    pipeline = _build_pipeline_or_exit(provider, model, cache_root)

    result = process_single_image(path, pipeline.analyzer, pipeline.cache, set())

    if result.status == RenameStatus.ERROR:
        console.print(f"[red]Error processing {path.name}[/red]")
        raise typer.Exit(1)

    return result


@app.command()
def file(
    path: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to an image file"
    ),
    provider: Provider = "ollama",
    model: Model = "gemma3:27b",
    dry_run: DryRun = True,
    update_refs: bool = typer.Option(
        False, "--update-refs/--no-update-refs", help="Update markdown/wiki references when renaming"
    ),
    refs_root: Path | None = typer.Option(
        None, "--refs-root", help="Root directory for reference updates (defaults to file's directory)",
        file_okay=False
    ),
) -> None:
    """Rename a single file based on its visual contents."""
    result = _process_single_file(path, provider, model)

    status_labels = {
        RenameStatus.UNCHANGED: "unchanged",
        RenameStatus.RENAMED: "proposed",
        RenameStatus.COLLISION: "collision-resolved",
        RenameStatus.ERROR: "error",
    }
    mode_label = status_labels[result.status]

    console.print(
        Panel.fit(
            f"[dim]Source[/]: {result.source}\n"
            f"[bold]Proposed[/]: {result.proposed}\n"
            f"[bold]Final[/]: {result.final}\n"
            f"[dim]Provider[/]: {provider}  [dim]Model[/]: {model}  [dim]Mode[/]: "
            f"{'dry-run' if dry_run else 'apply'} ({mode_label})",
            title="image-namer: file",
            border_style="green",
        )
    )

    _handle_reference_updates(path, result.final, update_refs, refs_root, dry_run)

    if not dry_run:
        _apply_single_rename(path, result.final)


@app.command()
def folder(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, readable=True, help="Path to a directory containing images"
    ),
    provider: Provider = "ollama",
    model: Model = "gemma3:27b",
    dry_run: DryRun = True,
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
    """Rename all images in a directory based on their visual contents."""
    _validate_provider(provider)

    image_files = collect_image_files(path, recursive)
    if not image_files:
        console.print(f"[yellow]No supported image files found in {path}[/yellow]")
        raise typer.Exit(0)

    console.print(f"[dim]Found {len(image_files)} image(s) to process...[/dim]")

    cache_root = ensure_cache_layout(Path.cwd())
    pipeline = _build_pipeline_or_exit(provider, model, cache_root)

    results = process_folder(image_files, pipeline.analyzer, pipeline.cache)

    display_results_table(console, results, dry_run)
    print_statistics(console, results)

    if update_refs:
        search_root = refs_root if refs_root else path
        markdown_files = FilesystemMarkdownFiles()
        if dry_run:
            ref_result = count_batch_references(results, search_root, markdown_files)
        else:
            ref_result = apply_batch_reference_updates(results, search_root, markdown_files)
        print_reference_result(console, ref_result, dry_run)

    if not dry_run:
        _apply_renames(results)


@app.command()
def generate(
    path: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to an image file"
    ),
    provider: Provider = "ollama",
    model: Model = "gemma3:27b",
    dry_run: DryRun = True,
) -> None:
    """Propose a new filename for a given image file."""
    result = _process_single_file(path, provider, model)

    console.print(
        Panel.fit(
            f"[bold]Proposed[/]: {result.proposed}\n"
            f"[dim]Source[/]: {result.source}\n"
            f"[dim]Provider[/]: {provider}  [dim]Model[/]: {model}  [dim]Mode[/]: "
            f"{'dry-run' if dry_run else 'apply'}",
            title="image-namer: generate",
            border_style="cyan",
        )
    )

    if not dry_run and result.final != path.name:
        _apply_single_rename(path, result.final)
        console.print(f"[green]Renamed to: {result.final}[/green]")
    elif not dry_run:
        console.print("[dim]No rename needed.[/dim]")


def main() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
