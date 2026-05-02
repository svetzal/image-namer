"""Factory for constructing the LLM analysis pipeline.

Centralizes the gateway -> broker -> cache -> analyzer wiring that
is shared across CLI commands.
"""

from pathlib import Path
from typing import Annotated

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
) -> AnalysisPipeline:
    """Build the full analysis pipeline from provider configuration.

    Raises MissingApiKeyError if the provider requires an API key not present
    in the environment.
    """
    gateway = create_gateway(provider)
    llm = LLMBroker(gateway=gateway, model=model)
    cache = FilesystemAnalysisCache(cache_root / "cache" / "unified", provider=provider, model=model)
    analyzer = MojenticImageAnalyzer(llm)
    return AnalysisPipeline(analyzer=analyzer, cache=cache, provider=provider, model=model)
