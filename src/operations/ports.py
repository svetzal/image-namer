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
