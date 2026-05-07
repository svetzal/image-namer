"""Tests for the analysis pipeline factory."""

import pytest

from operations.gateway_factory import MissingApiKeyError
from operations.pipeline_factory import AnalysisPipeline, build_analysis_pipeline


@pytest.fixture
def all_mocks(mocker):
    return {
        "create_gateway": mocker.Mock(),
        "LLMBroker": mocker.Mock(),
        "FilesystemAnalysisCache": mocker.Mock(),
        "MojenticImageAnalyzer": mocker.Mock(),
    }


def should_call_create_gateway_with_provider(all_mocks, tmp_path):
    build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    all_mocks["create_gateway"].assert_called_once_with("ollama")


def should_construct_llm_broker_with_gateway_and_model(all_mocks, tmp_path):
    fake_gateway = all_mocks["create_gateway"].return_value

    build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    all_mocks["LLMBroker"].assert_called_once_with(gateway=fake_gateway, model="gemma3:27b")


def should_construct_filesystem_analysis_cache_with_unified_subpath(all_mocks, tmp_path):
    build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    all_mocks["FilesystemAnalysisCache"].assert_called_once_with(
        tmp_path / "cache" / "unified",
        provider="ollama",
        model="gemma3:27b",
    )


def should_construct_mojentic_image_analyzer_with_broker(all_mocks, tmp_path):
    fake_broker = all_mocks["LLMBroker"].return_value

    build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    all_mocks["MojenticImageAnalyzer"].assert_called_once_with(fake_broker)


def should_return_analysis_pipeline_with_correct_provider(all_mocks, tmp_path):
    result = build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    assert result.provider == "ollama"


def should_return_analysis_pipeline_with_correct_model(all_mocks, tmp_path):
    result = build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    assert result.model == "gemma3:27b"


def should_return_analysis_pipeline_with_analyzer(all_mocks, tmp_path):
    fake_analyzer = all_mocks["MojenticImageAnalyzer"].return_value

    result = build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    assert result.analyzer is fake_analyzer


def should_return_analysis_pipeline_with_cache(all_mocks, tmp_path):
    fake_cache = all_mocks["FilesystemAnalysisCache"].return_value

    result = build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    assert result.cache is fake_cache


def should_return_analysis_pipeline_instance(all_mocks, tmp_path):
    result = build_analysis_pipeline(
        "ollama", "gemma3:27b", tmp_path,
        create_gateway_fn=all_mocks["create_gateway"],
        broker_cls=all_mocks["LLMBroker"],
        cache_cls=all_mocks["FilesystemAnalysisCache"],
        analyzer_cls=all_mocks["MojenticImageAnalyzer"],
    )

    assert isinstance(result, AnalysisPipeline)


def should_propagate_missing_api_key_error_from_create_gateway(all_mocks, tmp_path):
    all_mocks["create_gateway"].side_effect = MissingApiKeyError("OPENAI_API_KEY not set")

    with pytest.raises(MissingApiKeyError):
        build_analysis_pipeline(
            "openai", "gpt-4o", tmp_path,
            create_gateway_fn=all_mocks["create_gateway"],
            broker_cls=all_mocks["LLMBroker"],
            cache_cls=all_mocks["FilesystemAnalysisCache"],
            analyzer_cls=all_mocks["MojenticImageAnalyzer"],
        )
