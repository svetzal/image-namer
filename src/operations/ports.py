from pathlib import Path
from typing import Protocol

from operations.models import ImageAnalysis


class AnalysisCachePort(Protocol):

    def load(
        self,
        image_path: Path,
        filename: str,
    ) -> ImageAnalysis | None:
        """Load a cached analysis result; returns None on cache miss or stale entry."""
        ...

    def save(
        self,
        image_path: Path,
        filename: str,
        analysis: ImageAnalysis,
    ) -> None:
        """Persist an analysis result keyed by image path, filename, provider, and model."""
        ...


class ImageAnalyzerPort(Protocol):

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Analyze the image at path and return an assessment and proposed filename."""
        ...


class FileRenamerPort(Protocol):

    def rename(self, source: Path, destination: Path) -> None:
        """Rename source to destination; destination must not already exist."""
        ...


class MarkdownFilePort(Protocol):

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        """Return .md files under root; searches recursively when recursive is True."""
        ...

    def read_markdown_content(self, file_path: Path) -> str:
        ...

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        """Write content to file_path atomically; partial writes must not corrupt the file."""
        ...


class CacheClearerPort(Protocol):

    def ensure_layout(self, root: Path) -> Path:
        """Ensure cache directory structure exists and return the cache root."""
        ...

    def cache_exists(self, cache_dir: Path) -> bool:
        """Return True if the cache directory exists."""
        ...

    def clear(self, cache_dir: Path) -> None:
        """Delete and recreate the cache directory."""
        ...


class ProgressCallback(Protocol):

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called when a cached analysis is found for path."""
        ...

    def on_cache_miss(self, path: Path) -> None:
        """Called when no cached analysis exists for path and the LLM will be invoked."""
        ...

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        """Called after a fresh LLM analysis has been obtained and cached for path."""
        ...
