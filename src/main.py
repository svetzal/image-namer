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

from operations.generate_name import generate_name

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
def generate(
    path: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True, help="Path to an image file"
    ),
    provider: str = typer.Option(
        os.getenv("LLM_PROVIDER", "ollama"),
        "--provider",
        help="Model provider: ollama or openai",
        envvar=["LLM_PROVIDER"],
    ),
    model: str = typer.Option(
        os.getenv("LLM_MODEL", "gemma3:27b"),
        "--model",
        help="Visual model to use (default aligns with Ollama gemma3:27b)",
        envvar=["LLM_MODEL"],
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
