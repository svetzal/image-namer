"""Display formatting utilities: accept a Console and domain models, produce Rich output."""

from rich.console import Console
from rich.table import Table

from operations.models import BatchReferenceResult, ProcessingResult
from operations.process_folder import compute_statistics
from operations.rename_status_display import RENAME_STATUS_PRESENTATION


def display_results_table(console: Console, results: list[ProcessingResult], dry_run: bool) -> None:
    """Render a Rich table of processing results to the console."""
    table = Table(title=f"image-namer: folder ({'dry-run' if dry_run else 'apply'})")
    table.add_column("Source", style="dim")
    table.add_column("Proposed", style="bold")
    table.add_column("Final", style="green")
    table.add_column("Status", style="cyan")

    for result in results:
        status_display = RENAME_STATUS_PRESENTATION[result.status].table_label
        table.add_row(result.source, result.proposed, result.final, status_display)

    console.print(table)


def print_statistics(console: Console, results: list[ProcessingResult]) -> None:
    """Print a one-line summary of rename statistics to the console."""
    stats = compute_statistics(results)
    console.print(
        f"\n[dim]Summary: {stats.renamed} renamed, "
        f"{stats.unchanged} unchanged, "
        f"{stats.collision} collision(s), {stats.error} error(s)[/dim]"
    )


def print_reference_result(console: Console, ref_result: BatchReferenceResult, dry_run: bool) -> None:
    """Print a summary of markdown reference update results."""
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
    if ref_result.failures:
        console.print(f"[red]⚠ {len(ref_result.failures)} reference(s) could not be updated:[/red]")
        for failure in ref_result.failures:
            console.print(f"[red]  {failure.file_path}:{failure.line_number} — {failure.reason}[/red]")
