import json

import pytest

from conftest import make_analysis
from constants import RUBRIC_VERSION
from operations.cache import (
    AnalysisCacheEntry,
    CacheStore,
    build_cache_key,
    load_analysis_from_cache,
    save_analysis_to_cache,
)

_fake_hasher = lambda _: "abc123"  # noqa: E731


def should_join_parts_with_double_underscores():
    result = build_cache_key("abc123", "ollama", "gemma3:27b")

    assert result == f"abc123__ollama__gemma3_27b__v{RUBRIC_VERSION}"


def should_sanitize_slashes_and_colons():
    result = build_cache_key("abc123", "openai/gpt-4", "model:v1")

    assert result == f"abc123__openai_gpt-4__model_v1__v{RUBRIC_VERSION}"


def should_include_filename_when_provided():
    result = build_cache_key("abc123", "test.png", "ollama", "gemma3:27b")

    assert result == f"abc123__test.png__ollama__gemma3_27b__v{RUBRIC_VERSION}"


@pytest.fixture
def store():
    return CacheStore(
        entry_type=AnalysisCacheEntry,
        payload_field="analysis",
        key_fields=("filename", "provider", "model"),
        hash_fn=_fake_hasher,
    )


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache" / "unified"


@pytest.fixture
def image_path(tmp_path):
    p = tmp_path / "test-image.png"
    p.write_bytes(b"fake image content")
    return p


def should_return_none_when_cache_file_missing(store, cache_dir, image_path):
    result = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert result is None


def should_return_payload_after_save(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")

    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )
    result = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert result is not None
    assert result.proposed_name.stem == "test-name"


def should_return_none_when_image_hash_changed(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")
    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    different_store = CacheStore(
        entry_type=AnalysisCacheEntry,
        payload_field="analysis",
        key_fields=("filename", "provider", "model"),
        hash_fn=lambda _: "different_hash",
    )
    result = different_store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert result is None


def should_return_none_when_key_field_changed(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")
    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    result = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="openai", model="gemma3:27b",
    )

    assert result is None


def should_return_none_when_rubric_version_tampered(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")
    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    key = build_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    data["rubric_version"] = RUBRIC_VERSION + 1
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    result = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert result is None


def should_return_none_when_cache_file_corrupted(store, cache_dir, image_path):
    cache_dir.mkdir(parents=True)
    key = build_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    (cache_dir / f"{key}.json").write_text("invalid json {{{", encoding="utf-8")

    result = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert result is None


def should_create_cache_directory_if_missing(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")

    assert not cache_dir.exists()
    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert cache_dir.exists()
    assert cache_dir.is_dir()


def should_serialize_as_valid_json(store, cache_dir, image_path):
    analysis = make_analysis(stem="test-name")
    store.save(
        cache_dir, image_path, analysis,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    key = build_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    data = json.loads((cache_dir / f"{key}.json").read_text(encoding="utf-8"))

    assert data["image_hash"] == "abc123"
    assert data["filename"] == "test-image.png"
    assert data["provider"] == "ollama"
    assert data["model"] == "gemma3:27b"
    assert data["rubric_version"] == RUBRIC_VERSION
    assert data["analysis"]["proposed_name"]["stem"] == "test-name"


def should_overwrite_existing_cache_entry(store, cache_dir, image_path):
    first = make_analysis(stem="first-name")
    second = make_analysis(stem="second-name")

    store.save(
        cache_dir, image_path, first,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )
    store.save(
        cache_dir, image_path, second,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )
    loaded = store.load(
        cache_dir, image_path,
        filename="test-image.png", provider="ollama", model="gemma3:27b",
    )

    assert loaded is not None
    assert loaded.proposed_name.stem == "second-name"


def should_round_trip_analysis_cache(tmp_path):
    cache_dir = tmp_path / "cache" / "unified"
    image_path = tmp_path / "test.png"
    image_path.write_bytes(b"content")
    analysis = make_analysis(stem="good-name", reasoning="Already descriptive")

    save_analysis_to_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b", analysis)
    result = load_analysis_from_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b")

    assert result is not None
    assert result.current_name_suitable is True
    assert result.proposed_name.stem == "good-name"
