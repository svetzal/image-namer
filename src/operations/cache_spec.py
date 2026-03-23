import json

import pytest

from constants import RUBRIC_VERSION
from operations.cache import (
    AssessmentCacheEntry,
    CacheEntry,
    CacheStore,
    assessment_cache_key,
    build_cache_key,
    cache_key,
    load_analysis_from_cache,
    load_assessment_from_cache,
    load_from_cache,
    save_analysis_to_cache,
    save_assessment_to_cache,
    save_to_cache,
)
from operations.models import ImageAnalysis, NameAssessment, ProposedName


class DescribeBuildCacheKey:
    def should_join_parts_with_double_underscores(self):
        result = build_cache_key("abc123", "ollama", "gemma3:27b")

        assert result == f"abc123__ollama__gemma3_27b__v{RUBRIC_VERSION}"

    def should_sanitize_slashes_and_colons(self):
        result = build_cache_key("abc123", "openai/gpt-4", "model:v1")

        assert result == f"abc123__openai_gpt-4__model_v1__v{RUBRIC_VERSION}"

    def should_include_filename_when_provided(self):
        result = build_cache_key("abc123", "test.png", "ollama", "gemma3:27b")

        assert result == f"abc123__test.png__ollama__gemma3_27b__v{RUBRIC_VERSION}"

    def should_match_legacy_cache_key_output(self):
        assert build_cache_key("h", "p", "m") == cache_key("h", "p", "m")

    def should_match_legacy_assessment_cache_key_output(self):
        assert build_cache_key("h", "f", "p", "m") == assessment_cache_key("h", "f", "p", "m")


class DescribeCacheStore:
    @pytest.fixture
    def store(self):
        return CacheStore(
            entry_type=CacheEntry,
            payload_field="proposed_name",
            key_fields=("provider", "model"),
        )

    @pytest.fixture
    def cache_dir(self, tmp_path):
        return tmp_path / "cache" / "names"

    @pytest.fixture
    def image_path(self, tmp_path):
        p = tmp_path / "test-image.png"
        p.write_bytes(b"fake image content")
        return p

    class DescribeLoad:
        def should_return_none_when_cache_file_missing(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")

            result = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert result is None

        def should_return_payload_after_save(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")

            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")
            result = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert result is not None
            assert result.stem == "test-name"

        def should_return_none_when_image_hash_changed(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")
            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")

            mocker.patch("operations.cache.sha256_file", return_value="different_hash")
            result = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert result is None

        def should_return_none_when_key_field_changed(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")
            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")

            result = store.load(cache_dir, image_path, provider="openai", model="gemma3:27b")

            assert result is None

        def should_return_none_when_rubric_version_tampered(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")
            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")

            key = build_cache_key("abc123", "ollama", "gemma3:27b")
            cache_file = cache_dir / f"{key}.json"
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            data["rubric_version"] = RUBRIC_VERSION + 1
            cache_file.write_text(json.dumps(data), encoding="utf-8")

            result = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert result is None

        def should_return_none_when_cache_file_corrupted(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            cache_dir.mkdir(parents=True)
            key = build_cache_key("abc123", "ollama", "gemma3:27b")
            (cache_dir / f"{key}.json").write_text("invalid json {{{", encoding="utf-8")

            result = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert result is None

    class DescribeSave:
        def should_create_cache_directory_if_missing(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")

            assert not cache_dir.exists()
            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")

            assert cache_dir.exists()
            assert cache_dir.is_dir()

        def should_serialize_as_valid_json(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            proposed = ProposedName(stem="test-name", extension=".png")
            store.save(cache_dir, image_path, proposed, provider="ollama", model="gemma3:27b")

            key = build_cache_key("abc123", "ollama", "gemma3:27b")
            data = json.loads((cache_dir / f"{key}.json").read_text(encoding="utf-8"))

            assert data["image_hash"] == "abc123"
            assert data["provider"] == "ollama"
            assert data["model"] == "gemma3:27b"
            assert data["rubric_version"] == RUBRIC_VERSION
            assert data["proposed_name"]["stem"] == "test-name"

        def should_overwrite_existing_cache_entry(self, store, cache_dir, image_path, mocker):
            mocker.patch("operations.cache.sha256_file", return_value="abc123")
            first = ProposedName(stem="first-name", extension=".png")
            second = ProposedName(stem="second-name", extension=".png")

            store.save(cache_dir, image_path, first, provider="ollama", model="gemma3:27b")
            store.save(cache_dir, image_path, second, provider="ollama", model="gemma3:27b")
            loaded = store.load(cache_dir, image_path, provider="ollama", model="gemma3:27b")

            assert loaded is not None
            assert loaded.stem == "second-name"


class DescribeCacheStoreWithFilenameField:
    @pytest.fixture
    def store(self):
        return CacheStore(
            entry_type=AssessmentCacheEntry,
            payload_field="assessment",
            key_fields=("filename", "provider", "model"),
        )

    @pytest.fixture
    def cache_dir(self, tmp_path):
        return tmp_path / "cache" / "analysis"

    @pytest.fixture
    def image_path(self, tmp_path):
        p = tmp_path / "test-image.png"
        p.write_bytes(b"fake image content")
        return p

    def should_round_trip_with_filename_in_key(self, store, cache_dir, image_path, mocker):
        mocker.patch("operations.cache.sha256_file", return_value="abc123")
        assessment = NameAssessment(suitable=True)

        store.save(
            cache_dir, image_path, assessment,
            filename="test-image.png", provider="ollama", model="gemma3:27b"
        )
        result = store.load(
            cache_dir, image_path,
            filename="test-image.png", provider="ollama", model="gemma3:27b"
        )

        assert result is not None
        assert result.suitable is True

    def should_return_none_when_filename_differs(self, store, cache_dir, image_path, mocker):
        mocker.patch("operations.cache.sha256_file", return_value="abc123")
        assessment = NameAssessment(suitable=True)

        store.save(
            cache_dir, image_path, assessment,
            filename="test-image.png", provider="ollama", model="gemma3:27b"
        )
        result = store.load(
            cache_dir, image_path,
            filename="different.png", provider="ollama", model="gemma3:27b"
        )

        assert result is None


class DescribeWrapperFunctions:
    def should_round_trip_names_cache(self, tmp_path, mocker):
        cache_dir = tmp_path / "cache" / "names"
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"content")
        mocker.patch("operations.cache.sha256_file", return_value="abc123")
        proposed = ProposedName(stem="test", extension=".png")

        save_to_cache(cache_dir, image_path, "ollama", "gemma3:27b", proposed)
        result = load_from_cache(cache_dir, image_path, "ollama", "gemma3:27b")

        assert result is not None
        assert result.stem == "test"

    def should_round_trip_assessment_cache(self, tmp_path, mocker):
        cache_dir = tmp_path / "cache" / "analysis"
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"content")
        mocker.patch("operations.cache.sha256_file", return_value="abc123")
        assessment = NameAssessment(suitable=False)

        save_assessment_to_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b", assessment)
        result = load_assessment_from_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b")

        assert result is not None
        assert result.suitable is False

    def should_round_trip_analysis_cache(self, tmp_path, mocker):
        cache_dir = tmp_path / "cache" / "unified"
        image_path = tmp_path / "test.png"
        image_path.write_bytes(b"content")
        mocker.patch("operations.cache.sha256_file", return_value="abc123")
        analysis = ImageAnalysis(
            current_name_suitable=True,
            proposed_name=ProposedName(stem="good-name", extension=".png"),
            reasoning="Already descriptive",
        )

        save_analysis_to_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b", analysis)
        result = load_analysis_from_cache(cache_dir, image_path, "test.png", "ollama", "gemma3:27b")

        assert result is not None
        assert result.current_name_suitable is True
        assert result.proposed_name.stem == "good-name"


class DescribeEntryModels:
    def should_validate_cache_entry_model(self):
        entry = CacheEntry(
            image_hash="abc123",
            provider="ollama",
            model="gemma3:27b",
            rubric_version=1,
            proposed_name=ProposedName(stem="test", extension=".png"),
        )

        assert entry.image_hash == "abc123"
        assert entry.proposed_name.stem == "test"

    def should_reject_invalid_cache_entry(self):
        with pytest.raises(Exception):
            CacheEntry.model_validate({"image_hash": "abc123"})

    def should_validate_assessment_cache_entry_model(self):
        entry = AssessmentCacheEntry(
            image_hash="abc123",
            filename="test.png",
            provider="ollama",
            model="gemma3:27b",
            rubric_version=1,
            assessment=NameAssessment(suitable=True),
        )

        assert entry.assessment.suitable is True

    def should_reject_invalid_assessment_cache_entry(self):
        with pytest.raises(Exception):
            AssessmentCacheEntry.model_validate({"image_hash": "abc123"})
