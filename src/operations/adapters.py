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

    Args:
        cache_dir: Path to the unified cache directory (e.g., .image_namer/cache/unified).
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
        """Load a cached analysis from the filesystem."""
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
        """Save an analysis result to the filesystem cache."""
        save_analysis_to_cache(
            self._cache_dir, image_path, filename, provider, model, analysis
        )


class MojenticImageAnalyzer:
    """LLM-backed implementation of ImageAnalyzerPort.

    Wraps the existing analyze_image function, binding the LLMBroker
    at construction time.

    Args:
        llm: LLM broker instance for making analysis calls.
    """

    def __init__(self, llm: LLMBroker) -> None:
        self._llm = llm

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Analyze an image using the bound LLM broker."""
        return analyze_image(path, current_name, llm=self._llm)
