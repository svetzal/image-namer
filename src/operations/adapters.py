"""Concrete adapter implementations for operations layer ports.

These are the imperative-shell implementations of the Protocol contracts
defined in ports.py. They perform real I/O (filesystem, LLM calls).
"""

from collections.abc import Callable
from pathlib import Path

from mojentic.llm import LLMBroker

from operations.analyze_image import analyze_image
from operations.cache import load_analysis_from_cache, save_analysis_to_cache
from operations.models import ImageAnalysis


class FilesystemAnalysisCache:
    """Filesystem-backed implementation of AnalysisCachePort.

    Wraps the existing cache module functions, binding them to a specific
    cache directory, provider, and model at construction time.
    """

    def __init__(self, cache_dir: Path, provider: str, model: str) -> None:
        """Initialize with cache directory and provider/model binding.

        Args:
            cache_dir: Root directory for the cache store.
            provider: LLM provider identifier (e.g., "ollama", "openai").
            model: Model name used to scope cache entries.
        """
        self._cache_dir = cache_dir
        self._provider = provider
        self._model = model

    def load(
        self,
        image_path: Path,
        filename: str,
    ) -> ImageAnalysis | None:
        """Load a cached analysis for the given image and filename.

        Args:
            image_path: Path to the image file on disk.
            filename: Filename used as part of the cache key.

        Returns:
            The cached ImageAnalysis, or None if not present or invalid.
        """
        return load_analysis_from_cache(
            self._cache_dir, image_path, filename, self._provider, self._model
        )

    def save(
        self,
        image_path: Path,
        filename: str,
        analysis: ImageAnalysis,
    ) -> None:
        """Persist an analysis result to the filesystem cache.

        Args:
            image_path: Path to the image file on disk.
            filename: Filename used as part of the cache key.
            analysis: The analysis result to cache.
        """
        save_analysis_to_cache(
            self._cache_dir, image_path, filename, self._provider, self._model, analysis
        )


class MojenticImageAnalyzer:
    """LLM-backed implementation of ImageAnalyzerPort.

    Wraps the existing analyze_image function, binding the LLMBroker
    at construction time.
    """

    def __init__(self, llm: LLMBroker, *, analyze_fn: Callable[..., ImageAnalysis] = analyze_image) -> None:
        """Initialize with an LLMBroker and optional analysis function override.

        Args:
            llm: The LLMBroker instance to use for vision model calls.
            analyze_fn: Analysis function to call; defaults to analyze_image.
        """
        self._llm = llm
        self._analyze_fn = analyze_fn

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Analyze an image and return assessment plus proposed filename.

        Args:
            path: Path to the image file on disk.
            current_name: The image's current filename, used in the LLM prompt.

        Returns:
            ImageAnalysis containing suitability assessment and proposed name.
        """
        return self._analyze_fn(path, current_name, llm=self._llm)


class FilesystemRenamer:
    """Filesystem-backed implementation of FileRenamerPort."""

    def rename(self, source: Path, destination: Path) -> None:
        """Rename source to destination using the filesystem.

        Args:
            source: Existing path to rename.
            destination: Target path; must not already exist.
        """
        source.rename(destination)


class FilesystemMarkdownFiles:
    """Thin I/O wrapper with no business logic."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        """Discover all .md files under root.

        Args:
            root: Directory to search.
            recursive: If True, search all subdirectories.

        Returns:
            List of .md file paths found.
        """
        pattern = "**/*.md" if recursive else "*.md"
        return [p for p in root.glob(pattern) if p.is_file()]

    def read_markdown_content(self, file_path: Path) -> str:
        """Read the UTF-8 text content of a markdown file.

        Args:
            file_path: Path to the .md file.

        Returns:
            The file's full text content.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        """Write UTF-8 text to a markdown file, overwriting existing content.

        Args:
            file_path: Path to the .md file.
            content: Text to write.
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
