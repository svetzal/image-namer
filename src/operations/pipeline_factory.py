"""Factory for constructing the LLM analysis pipeline.

Centralizes the gateway -> broker -> cache -> analyzer wiring that
is shared across CLI commands.
"""

from pathlib import Path

from mojentic.llm import LLMBroker

from operations.adapters import FilesystemAnalysisCache, MojenticImageAnalyzer
from operations.gateway_factory import create_gateway
from operations.ports import AnalysisCachePort, ImageAnalyzerPort


class AnalysisPipeline:
    """Holds the constructed analysis pipeline components.

    Attributes:
        analyzer: Image analyzer for LLM-based analysis.
        cache: Analysis cache for load/save operations.
    """

    def __init__(self, analyzer: ImageAnalyzerPort, cache: AnalysisCachePort) -> None:
        self.analyzer = analyzer
        self.cache = cache


def build_analysis_pipeline(
    provider: str,
    model: str,
    cache_root: Path,
) -> AnalysisPipeline:
    """Build the full analysis pipeline from provider configuration.

    Args:
        provider: LLM provider name ("ollama" or "openai").
        model: Model identifier string.
        cache_root: Path to the .image_namer cache root directory.

    Returns:
        AnalysisPipeline with configured analyzer and cache.

    Raises:
        MissingApiKeyError: If the provider requires an API key not found
            in the environment.
        ValueError: If provider is not recognized.
    """
    gateway = create_gateway(provider)
    llm = LLMBroker(gateway=gateway, model=model)
    cache = FilesystemAnalysisCache(cache_root / "cache" / "unified")
    analyzer = MojenticImageAnalyzer(llm)
    return AnalysisPipeline(analyzer=analyzer, cache=cache)
