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

from operations.generate_name import generate_name
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
        False, "--update-refs/--no-update-refs", help="Update markdown/wiki references (placeholder)"
    ),
    refs_root: Path | None = typer.Option(
        None, "--refs-root", help="Root directory for reference updates (placeholder)", file_okay=False
    ),
) -> None:
    """Rename a single file based on its visual contents.

    Validates types, calls vision naming, enforces idempotency, resolves collisions,
    and optionally renames the file when --apply is used. Reference updating is a
    no-op placeholder for now.
    """
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        console.print(
            f"[red]Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}[/red]"
        )
        raise typer.Exit(2)

    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)

    if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
        console.print("[red]OPENAI_API_KEY environment variable not set[/red]")
        raise typer.Exit(2)

    # Prepare LLM and propose name
    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
        proposed = generate_name(path, llm=llm)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    proposed_stem = proposed.stem
    if proposed.extension.startswith("."):
        proposed_ext = proposed.extension
    elif proposed.extension:
        proposed_ext = f".{proposed.extension}"
    else:
        proposed_ext = path.suffix

    # Idempotency heuristic: if current stem equals proposed stem → unchanged
    current_stem = path.stem
    if current_stem == proposed_stem:
        final_name = path.name
        mode_label = "unchanged"
    else:
        # Resolve collisions in the directory
        candidate = f"{proposed_stem}{proposed_ext}"
        if (path.parent / candidate).exists():
            final_name = next_available_name(path.parent, proposed_stem, proposed_ext)
            mode_label = "collision-resolved"
        else:
            final_name = candidate
            mode_label = "proposed"

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

    # Placeholder for refs update
    if update_refs:
        root_msg = f" at root {refs_root}" if refs_root else ""
        console.print(f"[dim]Ref update requested{root_msg} (placeholder; no changes made).[/dim]")

    if not dry_run:
        final_path = path.with_name(final_name)
        if final_path != path:
            path.rename(final_path)


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
        False, "--update-refs/--no-update-refs", help="Update markdown/wiki references (placeholder)"
    ),
    refs_root: Path | None = typer.Option(
        None, "--refs-root", help="Root directory for reference updates (placeholder)", file_okay=False
    ),
) -> None:
    """Rename all images in a directory based on their visual contents.

    Processes all supported image files in the directory (flat by default, or
    recursively with --recursive). Shows a summary table of all renames and
    reuses the collision resolver and idempotency logic from the file command.
    """
    if provider not in SUPPORTED_PROVIDERS:
        console.print(f"[red]Invalid provider: {provider}[/red]")
        raise typer.Exit(2)

    if provider == "openai" and "OPENAI_API_KEY" not in os.environ:
        console.print("[red]OPENAI_API_KEY environment variable not set[/red]")
        raise typer.Exit(2)

    # Collect all image files
    if recursive:
        image_files = [
            p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    else:
        image_files = [
            p for p in path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    if not image_files:
        console.print(f"[yellow]No supported image files found in {path}[/yellow]")
        raise typer.Exit(0)

    console.print(f"[dim]Found {len(image_files)} image(s) to process...[/dim]")

    # Prepare LLM once
    try:
        gateway = _get_gateway(provider)  # type: ignore[arg-type]
        llm = LLMBroker(gateway=gateway, model=model)
    except Exception as e:
        console.print(f"[red]Error setting up LLM: {e}[/red]")
        raise typer.Exit(1)

    # Process each file
    results = []
    # Track planned filenames to detect collisions between renames
    planned_names = set()

    for img_path in image_files:
        try:
            proposed = generate_name(img_path, llm=llm)
        except Exception as e:
            console.print(f"[red]Error processing {img_path.name}: {e}[/red]")
            results.append({
                "source": img_path.name,
                "proposed": "ERROR",
                "final": img_path.name,
                "status": "error",
            })
            continue

        proposed_stem = proposed.stem
        if proposed.extension.startswith("."):
            proposed_ext = proposed.extension
        elif proposed.extension:
            proposed_ext = f".{proposed.extension}"
        else:
            proposed_ext = img_path.suffix

        # Idempotency heuristic
        current_stem = img_path.stem
        if current_stem == proposed_stem:
            final_name = img_path.name
            status = "unchanged"
        else:
            # Resolve collisions (check both disk and planned renames)
            candidate = f"{proposed_stem}{proposed_ext}"
            if (img_path.parent / candidate).exists() or candidate in planned_names:
                # Find next available considering both disk and planned names
                suffix_num = 2
                while True:
                    test_name = f"{proposed_stem}-{suffix_num}{proposed_ext}"
                    if not (img_path.parent / test_name).exists() and test_name not in planned_names:
                        final_name = test_name
                        break
                    suffix_num += 1
                status = "collision"
            else:
                final_name = candidate
                status = "renamed"

            # Track this name to avoid collisions with future renames
            planned_names.add(final_name)

        results.append({
            "source": img_path.name,
            "proposed": f"{proposed_stem}{proposed_ext}",
            "final": final_name,
            "status": status,
            "path": img_path,
        })

    # Display summary table
    table = Table(title=f"image-namer: folder ({'dry-run' if dry_run else 'apply'})")
    table.add_column("Source", style="dim")
    table.add_column("Proposed", style="bold")
    table.add_column("Final", style="green")
    table.add_column("Status", style="cyan")

    for result in results:
        status_display = {
            "renamed": "✓ rename",
            "unchanged": "= unchanged",
            "collision": "⚠ collision",
            "error": "✗ error",
        }.get(result["status"], result["status"])

        table.add_row(
            result["source"],
            result["proposed"],
            result["final"],
            status_display,
        )

    console.print(table)

    # Statistics
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

    # Placeholder for refs update
    if update_refs:
        root_msg = f" at root {refs_root}" if refs_root else ""
        console.print(f"[dim]Ref update requested{root_msg} (placeholder; no changes made).[/dim]")

    # Apply renames
    if not dry_run:
        for result in results:
            if result["status"] in ["renamed", "collision"] and "path" in result:
                img_path = result["path"]
                final_path = img_path.with_name(result["final"])
                if final_path != img_path:
                    img_path.rename(final_path)
        console.print("[green]✓ All renames applied.[/green]")


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
