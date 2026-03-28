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
        """Load a cached analysis result if available.

        Args:
            image_path: Path to the image file.
            filename: The filename used as a cache key component.
            provider: LLM provider name.
            model: Model name.

        Returns:
            Cached ImageAnalysis if found and valid, None otherwise.
        """
        ...

    def save(
        self,
        image_path: Path,
        filename: str,
        provider: str,
        model: str,
        analysis: ImageAnalysis,
    ) -> None:
        """Save an analysis result to the cache.

        Args:
            image_path: Path to the image file.
            filename: The filename that was analyzed.
            provider: LLM provider name.
            model: Model name.
            analysis: The analysis result to cache.
        """
        ...


class ImageAnalyzerPort(Protocol):
    """Port for analyzing images via an LLM to produce assessment and naming."""

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Analyze an image and return assessment + proposed name.

        Args:
            path: Path to the image file.
            current_name: Current filename (stem + extension) to assess.

        Returns:
            ImageAnalysis containing assessment, proposed name, and reasoning.
        """
        ...


class FileRenamerPort(Protocol):
    """Port for renaming files on the filesystem."""

    def rename(self, source: Path, destination: Path) -> None:
        """Rename a file from source to destination.

        Args:
            source: Current file path.
            destination: New file path.
        """
        ...


class MarkdownFilePort(Protocol):
    """Port for reading, writing, and discovering markdown files."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        """Find all markdown files under a root directory.

        Args:
            root: Root directory to search.
            recursive: Whether to search subdirectories.

        Returns:
            List of paths to markdown files found.
        """
        ...

    def read_markdown_content(self, file_path: Path) -> str:
        """Read the full content of a markdown file.

        Args:
            file_path: Path to the markdown file.

        Returns:
            The file's content as a string.
        """
        ...

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        """Write content to a markdown file.

        Args:
            file_path: Path to the markdown file.
            content: The content to write.
        """
        ...


class ProgressCallback(Protocol):
    """Port for receiving progress notifications during image analysis."""

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called when an analysis result is found in the cache.

        Args:
            path: Path to the image file.
            analysis: The cached analysis result.
        """
        ...

    def on_cache_miss(self, path: Path) -> None:
        """Called when no cached analysis is available and LLM will be invoked.

        Args:
            path: Path to the image file.
        """
        ...

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called after a fresh LLM analysis has been performed and cached.

        Args:
            path: Path to the image file.
            analysis: The freshly generated analysis result.
        """
        ...
