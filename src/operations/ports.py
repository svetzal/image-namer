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
    ) -> ImageAnalysis | None:
        """Load a cached analysis result for the given image.

        Args:
            image_path: Path to the image file.
            filename: Filename component of the cache key.

        Returns:
            The cached ImageAnalysis, or None if absent or stale.
        """
        ...

    def save(
        self,
        image_path: Path,
        filename: str,
        analysis: ImageAnalysis,
    ) -> None:
        """Persist an analysis result to the cache.

        Args:
            image_path: Path to the image file.
            filename: Filename component of the cache key.
            analysis: The analysis result to store.
        """
        ...


class ImageAnalyzerPort(Protocol):
    """Port for analyzing images via an LLM to produce assessment and naming."""

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Analyze an image and return a combined assessment and proposed name.

        Args:
            path: Path to the image file.
            current_name: The image's current filename.

        Returns:
            ImageAnalysis with suitability assessment and proposed filename.
        """
        ...


class FileRenamerPort(Protocol):
    """Port for renaming files on the filesystem."""

    def rename(self, source: Path, destination: Path) -> None:
        """Rename source to destination.

        Args:
            source: Existing file path.
            destination: Target path after rename.
        """
        ...


class MarkdownFilePort(Protocol):
    """Port for reading, writing, and discovering markdown files."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        """Return .md files under root.

        Args:
            root: Directory to search.
            recursive: If True, search all subdirectories.

        Returns:
            List of .md file paths found.
        """
        ...

    def read_markdown_content(self, file_path: Path) -> str:
        """Read the text content of a markdown file.

        Args:
            file_path: Path to the .md file.

        Returns:
            The file's full text content.
        """
        ...

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        """Write text content to a markdown file.

        Args:
            file_path: Path to the .md file.
            content: Text to write.
        """
        ...


class ProgressCallback(Protocol):
    """Port for receiving progress notifications during image analysis."""

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called when an analysis result is served from the cache.

        Args:
            path: Path to the image file.
            analysis: The cached analysis result.
        """
        ...

    def on_cache_miss(self, path: Path) -> None:
        """Called when no cached result is found and an LLM call will be made.

        Args:
            path: Path to the image file.
        """
        ...

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called after an LLM analysis completes and is ready for use.

        Args:
            path: Path to the image file.
            analysis: The freshly computed analysis result.
        """
        ...
