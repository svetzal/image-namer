"""Display formatting utilities for the image-namer CLI.

Pure formatting functions: accept a Console instance and domain models,
produce Rich output. No business logic.
"""

from rich.console import Console
from rich.table import Table

from operations.models import BatchReferenceResult, ProcessingResult, RenameStatus
from operations.process_folder import compute_statistics


def display_results_table(console: Console, results: list[ProcessingResult], dry_run: bool) -> None:
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
        table.add_row(result.source, result.proposed, result.final, status_display)

    console.print(table)


def print_statistics(console: Console, results: list[ProcessingResult]) -> None:
    stats = compute_statistics(results)
    console.print(
        f"\n[dim]Summary: {stats.renamed} renamed, "
        f"{stats.unchanged} unchanged, "
        f"{stats.collision} collision(s), {stats.error} error(s)[/dim]"
    )


def print_reference_result(console: Console, ref_result: BatchReferenceResult, dry_run: bool) -> None:
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
