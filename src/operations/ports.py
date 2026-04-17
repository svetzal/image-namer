"""Ports (Protocol interfaces) for I/O boundaries in the operations layer.

These protocols define the contracts for external dependencies that the
functional core depends on. Concrete implementations live in the imperative
shell or adapter modules.
"""

from pathlib import Path
from typing import Protocol

from operations.models import ImageAnalysis


class AnalysisCachePort(Protocol):
    """Port for loading and saving unified image analysis results."""

    def load(
        self,
        image_path: Path,
        filename: str,
        provider: str,
        model: str,
    ) -> ImageAnalysis | None:
        ...

    def save(
        self,
        image_path: Path,
        filename: str,
        provider: str,
        model: str,
        analysis: ImageAnalysis,
    ) -> None:
        ...


class ImageAnalyzerPort(Protocol):
    """Port for analyzing images via an LLM to produce assessment and naming."""

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        ...


class FileRenamerPort(Protocol):
    """Port for renaming files on the filesystem."""

    def rename(self, source: Path, destination: Path) -> None:
        ...


class MarkdownFilePort(Protocol):
    """Port for reading, writing, and discovering markdown files."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        ...

    def read_markdown_content(self, file_path: Path) -> str:
        ...

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        ...


class ProgressCallback(Protocol):
    """Port for receiving progress notifications during image analysis."""

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        ...

    def on_cache_miss(self, path: Path) -> None:
        ...

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        ...
