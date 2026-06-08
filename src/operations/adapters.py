import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from mojentic.llm import LLMBroker

from constants import FILESYSTEM_IO_ERRORS
from operations.analyze_image import analyze_image
from operations.cache import load_analysis_from_cache, save_analysis_to_cache
from operations.models import ImageAnalysis


class FilesystemAnalysisCache:
    """Wraps cache module functions, binding provider and model at construction time."""

    def __init__(self, cache_dir: Path, provider: str, model: str) -> None:
        self._cache_dir = cache_dir
        self._provider = provider
        self._model = model

    def load(
        self,
        image_path: Path,
        filename: str,
    ) -> ImageAnalysis | None:
        """Delegate to the cache module using the bound provider and model."""
        return load_analysis_from_cache(
            self._cache_dir, image_path, filename, self._provider, self._model
        )

    def save(
        self,
        image_path: Path,
        filename: str,
        analysis: ImageAnalysis,
    ) -> None:
        """Delegate to the cache module using the bound provider and model."""
        save_analysis_to_cache(
            self._cache_dir, image_path, filename, self._provider, self._model, analysis
        )


class MojenticImageAnalyzer:
    """Wraps analyze_image, binding the LLMBroker at construction time."""

    def __init__(self, llm: LLMBroker, *, analyze_fn: Callable[..., ImageAnalysis] = analyze_image) -> None:
        self._llm = llm
        self._analyze_fn = analyze_fn

    def analyze(
        self,
        path: Path,
        current_name: str,
    ) -> ImageAnalysis:
        """Invoke the bound analyze function with the bound LLMBroker."""
        return self._analyze_fn(path, current_name, llm=self._llm)


class FilesystemRenamer:
    """Filesystem-backed FileRenamerPort implementation."""

    def rename(self, source: Path, destination: Path) -> None:
        """Rename source to destination using the filesystem."""
        source.rename(destination)


class FilesystemMarkdownFiles:
    """Thin I/O wrapper with no business logic."""

    def find_markdown_files(self, root: Path, *, recursive: bool) -> list[Path]:
        """Glob for .md files under root; searches all subdirectories when recursive is True."""
        pattern = "**/*.md" if recursive else "*.md"
        return [p for p in root.glob(pattern) if p.is_file()]

    def read_markdown_content(self, file_path: Path) -> str:
        """Read UTF-8 text; opens with explicit encoding for cross-platform safety."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_markdown_content(self, file_path: Path, content: str) -> None:
        """Write content atomically via a temp file and os.replace; cleans up the temp file on failure."""
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=file_path.parent,
                suffix='.tmp', delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp.write(content)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, file_path)
        except FILESYSTEM_IO_ERRORS:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink()
            raise
