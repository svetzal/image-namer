"""Factory for constructing the LLM analysis pipeline.

Centralizes the gateway -> broker -> cache -> analyzer wiring that
is shared across CLI commands.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, SkipValidation
from mojentic.llm import LLMBroker

from operations.adapters import FilesystemAnalysisCache, MojenticImageAnalyzer
from operations.gateway_factory import create_gateway
from operations.ports import AnalysisCachePort, ImageAnalyzerPort


class AnalysisPipeline(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    analyzer: Annotated[ImageAnalyzerPort, SkipValidation]
    cache: Annotated[AnalysisCachePort, SkipValidation]
    provider: str
    model: str


def build_analysis_pipeline(
    provider: str,
    model: str,
    cache_root: Path,
    *,
    create_gateway_fn: Callable[[str], Any] = create_gateway,
    broker_cls: Callable[..., Any] = LLMBroker,
    cache_cls: type[FilesystemAnalysisCache] = FilesystemAnalysisCache,
    analyzer_cls: type[MojenticImageAnalyzer] = MojenticImageAnalyzer,
) -> AnalysisPipeline:
    """Build the full analysis pipeline from provider configuration.

    Raises MissingApiKeyError if the provider requires an API key not present
    in the environment.
    """
    gateway = create_gateway_fn(provider)
    llm = broker_cls(gateway=gateway, model=model)
    cache = cache_cls(cache_root / "cache" / "unified", provider=provider, model=model)
    analyzer = analyzer_cls(llm)
    return AnalysisPipeline(analyzer=analyzer, cache=cache, provider=provider, model=model)
