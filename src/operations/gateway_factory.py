"""Factory for LLM gateway creation.

Shared between CLI and GUI to eliminate duplicated provider-setup logic.
"""

import os

from mojentic.llm.gateways import OllamaGateway, OpenAIGateway


class MissingApiKeyError(Exception):
    """Raised when a required API key is not set in the environment."""


def create_gateway(provider: str) -> OllamaGateway | OpenAIGateway:
    """Create the appropriate LLM gateway for the given provider.

    Args:
        provider: Either ``"ollama"`` or ``"openai"``.

    Returns:
        Gateway instance for the specified provider.

    Raises:
        MissingApiKeyError: If the provider requires an API key not found in
            the environment.
        ValueError: If provider is not recognised.
    """
    if provider == "ollama":
        return OllamaGateway()
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise MissingApiKeyError("OPENAI_API_KEY environment variable not set")
        return OpenAIGateway(api_key=api_key)
    raise ValueError(f"Unknown provider: {provider!r}")
