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
        ...


class ImageAnalyzerPort(Protocol):

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        ...


class FileRenamerPort(Protocol):

    def rename(self, source: Path, destination: Path) -> None:
        ...


class MarkdownFilePort(Protocol):

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        ...

    def read_markdown_content(self, file_path: Path) -> str:
        ...

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        ...


class ProgressCallback(Protocol):

    def on_cache_hit(self, path: Path, analysis: ImageAnalysis) -> None:
        ...

    def on_cache_miss(self, path: Path) -> None:
        ...

    def on_analysis_complete(self, path: Path, analysis: ImageAnalysis) -> None:
        ...
