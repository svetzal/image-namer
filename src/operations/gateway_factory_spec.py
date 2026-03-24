"""Tests for LLM gateway factory."""

import pytest

from operations.gateway_factory import MissingApiKeyError, create_gateway


def should_create_ollama_gateway():
    gateway = create_gateway("ollama")

    assert gateway is not None


def should_create_openai_gateway_when_api_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    gateway = create_gateway("openai")

    assert gateway is not None


def should_raise_missing_api_key_for_openai_without_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError):
        create_gateway("openai")


def should_raise_value_error_for_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_gateway("unknown")
