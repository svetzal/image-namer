"""Concrete adapter implementations for operations layer ports.

These are the imperative-shell implementations of the Protocol contracts
defined in ports.py. They perform real I/O (filesystem, LLM calls).
"""

from pathlib import Path

from mojentic.llm import LLMBroker

from operations.analyze_image import analyze_image
from operations.cache import load_analysis_from_cache, save_analysis_to_cache
from operations.models import ImageAnalysis


class FilesystemAnalysisCache:
    """Filesystem-backed implementation of AnalysisCachePort.

    Wraps the existing cache module functions, binding them to a specific
    cache directory at construction time.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def load(
        self,
        image_path: Path,
        filename: str,
        provider: str,
        model: str,
    ) -> ImageAnalysis | None:
        return load_analysis_from_cache(
            self._cache_dir, image_path, filename, provider, model
        )

    def save(
        self,
        image_path: Path,
        filename: str,
        provider: str,
        model: str,
        analysis: ImageAnalysis,
    ) -> None:
        save_analysis_to_cache(
            self._cache_dir, image_path, filename, provider, model, analysis
        )


class MojenticImageAnalyzer:
    """LLM-backed implementation of ImageAnalyzerPort.

    Wraps the existing analyze_image function, binding the LLMBroker
    at construction time.
    """

    def __init__(self, llm: LLMBroker) -> None:
        self._llm = llm

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        return analyze_image(path, current_name, llm=self._llm)


class FilesystemRenamer:

    def rename(self, source: Path, destination: Path) -> None:
        source.rename(destination)


class FilesystemMarkdownFiles:
    """Thin I/O wrapper with no business logic."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        pattern = "**/*.md" if recursive else "*.md"
        return [p for p in root.glob(pattern) if p.is_file()]

    def read_markdown_content(self, file_path: Path) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
