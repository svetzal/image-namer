"""Tests for cache operations."""

import json
from pathlib import Path

import pytest

from constants import RUBRIC_VERSION
from operations.cache import (
    AssessmentCacheEntry,
    CacheEntry,
    assessment_cache_key,
    cache_key,
    load_assessment_from_cache,
    load_from_cache,
    save_assessment_to_cache,
    save_to_cache,
)
from operations.models import NameAssessment, ProposedName


def should_generate_correct_cache_key():
    result = cache_key(
        "abc123def456",
        "ollama",
        "gemma3:27b",
    )

    assert result == f"abc123def456__ollama__gemma3_27b__v{RUBRIC_VERSION}"


def should_sanitize_provider_and_model_in_cache_key():
    result = cache_key(
        "abc123",
        "openai/gpt-4",
        "model:with:colons/and/slashes",
    )

    assert result == f"abc123__openai_gpt-4__model_with_colons_and_slashes__v{RUBRIC_VERSION}"


def should_save_and_load_cache_entry(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    loaded = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert loaded is not None
    assert loaded.stem == "test-name"
    assert loaded.extension == ".png"


def should_return_none_when_cache_file_missing(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    result = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_image_hash_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"original content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    mocker.patch("operations.cache.sha256_file", return_value="different_hash")
    result = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_provider_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    result = load_from_cache(cache_dir, image_path, "openai", "gemma3:27b")

    assert result is None


def should_return_none_when_model_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    result = load_from_cache(cache_dir, image_path, "ollama", "different-model")

    assert result is None


def should_return_none_when_rubric_version_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    key = cache_key("abc123", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    data["rubric_version"] = RUBRIC_VERSION + 1
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    result = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_cache_file_corrupted(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    cache_dir.mkdir(parents=True)
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    key = cache_key("abc123", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    cache_file.write_text("invalid json {{{", encoding="utf-8")

    result = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert result is None


def should_create_cache_directory_if_missing(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    assert not cache_dir.exists()
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    assert cache_dir.exists()
    assert cache_dir.is_dir()


def should_serialize_cache_entry_as_valid_json(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    proposed = ProposedName(stem="test-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)

    key = cache_key("abc123", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["image_hash"] == "abc123"
    assert data["provider"] == "ollama"
    assert data["model"] == "gemma3:27b"
    assert data["rubric_version"] == RUBRIC_VERSION
    assert data["proposed_name"]["stem"] == "test-name"
    assert data["proposed_name"]["extension"] == ".png"


def should_validate_cache_entry_model():
    entry = CacheEntry(
        image_hash="abc123",
        provider="ollama",
        model="gemma3:27b",
        rubric_version=1,
        proposed_name=ProposedName(stem="test", extension=".png"),
    )

    assert entry.image_hash == "abc123"
    assert entry.provider == "ollama"
    assert entry.model == "gemma3:27b"
    assert entry.rubric_version == 1
    assert entry.proposed_name.stem == "test"


def should_reject_invalid_cache_entry():
    with pytest.raises(Exception):
        CacheEntry.model_validate({
            "image_hash": "abc123",
            # Missing required fields
        })


def should_overwrite_existing_cache_file(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "names"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    first_proposed = ProposedName(stem="first-name", extension=".png")
    second_proposed = ProposedName(stem="second-name", extension=".png")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", first_proposed)
    save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", second_proposed)

    loaded = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

    assert loaded is not None
    assert loaded.stem == "second-name"


# Assessment cache tests


def should_generate_correct_assessment_cache_key():
    result = assessment_cache_key(
        "abc123def456",
        "test-image.png",
        "ollama",
        "gemma3:27b",
    )

    assert result == f"abc123def456__test-image.png__ollama__gemma3_27b__v{RUBRIC_VERSION}"


def should_sanitize_filename_in_assessment_cache_key():
    result = assessment_cache_key(
        "abc123",
        "path/to/image:name.png",
        "openai",
        "gpt-4o",
    )

    assert result == f"abc123__path_to_image_name.png__openai__gpt-4o__v{RUBRIC_VERSION}"


def should_save_and_load_assessment_cache_entry(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    loaded = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b")

    assert loaded is not None
    assert loaded.suitable is True


def should_return_none_when_assessment_cache_file_missing(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_assessment_image_hash_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"original content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    mocker.patch("operations.cache.sha256_file", return_value="different_hash")
    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_assessment_filename_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    result = load_assessment_from_cache(cache_dir, image_path, "different-name.png", "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_assessment_provider_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "openai", "gemma3:27b")

    assert result is None


def should_return_none_when_assessment_model_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "different-model")

    assert result is None


def should_return_none_when_assessment_rubric_version_changed(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    key = assessment_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    data["rubric_version"] = RUBRIC_VERSION + 1
    cache_file.write_text(json.dumps(data), encoding="utf-8")

    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b")

    assert result is None


def should_return_none_when_assessment_cache_file_corrupted(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    cache_dir.mkdir(parents=True)
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    key = assessment_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    cache_file.write_text("invalid json {{{", encoding="utf-8")

    result = load_assessment_from_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b")

    assert result is None


def should_create_assessment_cache_directory_if_missing(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=False)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    assert not cache_dir.exists()
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    assert cache_dir.exists()
    assert cache_dir.is_dir()


def should_serialize_assessment_cache_entry_as_valid_json(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")
    assessment = NameAssessment(suitable=True)

    mocker.patch("operations.cache.sha256_file", return_value="abc123")
    save_assessment_to_cache(cache_dir, image_path, "test-image.png", "ollama", "gemma3:27b", assessment)

    key = assessment_cache_key("abc123", "test-image.png", "ollama", "gemma3:27b")
    cache_file = cache_dir / f"{key}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["image_hash"] == "abc123"
    assert data["filename"] == "test-image.png"
    assert data["provider"] == "ollama"
    assert data["model"] == "gemma3:27b"
    assert data["rubric_version"] == RUBRIC_VERSION
    assert data["assessment"]["suitable"] is True


def should_validate_assessment_cache_entry_model():
    entry = AssessmentCacheEntry(
        image_hash="abc123",
        filename="test.png",
        provider="ollama",
        model="gemma3:27b",
        rubric_version=1,
        assessment=NameAssessment(suitable=True),
    )

    assert entry.image_hash == "abc123"
    assert entry.filename == "test.png"
    assert entry.provider == "ollama"
    assert entry.model == "gemma3:27b"
    assert entry.rubric_version == 1
    assert entry.assessment.suitable is True


def should_reject_invalid_assessment_cache_entry():
    with pytest.raises(Exception):
        AssessmentCacheEntry.model_validate({
            "image_hash": "abc123",
            # Missing required fields
        })


def should_cache_both_suitable_and_unsuitable_assessments(tmp_path: Path, mocker):
    cache_dir = tmp_path / "cache" / "analysis"
    image_path = tmp_path / "test-image.png"
    image_path.write_bytes(b"fake image content")

    mocker.patch("operations.cache.sha256_file", return_value="abc123")

    # Cache unsuitable assessment
    unsuitable = NameAssessment(suitable=False)
    save_assessment_to_cache(cache_dir, image_path, "bad-name.png", "ollama", "gemma3:27b", unsuitable)
    loaded_unsuitable = load_assessment_from_cache(cache_dir, image_path, "bad-name.png", "ollama", "gemma3:27b")

    assert loaded_unsuitable is not None
    assert loaded_unsuitable.suitable is False

    # Cache suitable assessment
    suitable = NameAssessment(suitable=True)
    save_assessment_to_cache(cache_dir, image_path, "good-name.png", "ollama", "gemma3:27b", suitable)
    loaded_suitable = load_assessment_from_cache(cache_dir, image_path, "good-name.png", "ollama", "gemma3:27b")

    assert loaded_suitable is not None
    assert loaded_suitable.suitable is True
