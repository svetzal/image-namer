"""Cache operations for storing and retrieving LLM results."""

import json
from pathlib import Path
from typing import Generic, TypeVar, cast

from pydantic import BaseModel, Field

from constants import RUBRIC_VERSION
from operations.models import ImageAnalysis, NameAssessment, ProposedName
from utils.fs import sha256_file


class BaseCacheEntry(BaseModel):
    """Shared fields common to all cache entry types.

    Attributes:
        image_hash: SHA-256 hash of the image file.
        rubric_version: Version of the naming rubric used for cache invalidation.
    """

    image_hash: str = Field(..., description="SHA-256 hash of the image")
    rubric_version: int = Field(..., description="Rubric version")


class CacheEntry(BaseCacheEntry):
    """A cached LLM result for an image naming operation.

    Attributes:
        provider: LLM provider name (e.g., 'ollama', 'openai').
        model: Model name (e.g., 'gemma3:27b', 'gpt-4o').
        proposed_name: The proposed filename from the LLM.
    """

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    proposed_name: ProposedName = Field(..., description="Proposed filename")


class AssessmentCacheEntry(BaseCacheEntry):
    """A cached LLM result for an image name assessment operation.

    Attributes:
        filename: The filename that was assessed.
        provider: LLM provider name (e.g., 'ollama', 'openai').
        model: Model name (e.g., 'gemma3:27b', 'gpt-4o').
        assessment: The assessment result from the LLM.
    """

    filename: str = Field(..., description="Filename that was assessed")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    assessment: NameAssessment = Field(..., description="Assessment result")


class AnalysisCacheEntry(BaseCacheEntry):
    """A cached unified analysis result for an image.

    Attributes:
        filename: The filename that was analyzed.
        provider: LLM provider name.
        model: Model name.
        analysis: The complete analysis result.
    """

    filename: str = Field(..., description="Filename that was analyzed")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    analysis: ImageAnalysis = Field(..., description="Complete analysis result")


def build_cache_key(image_hash: str, *parts: str) -> str:
    """Generate a cache key from an image hash and arbitrary string parts.

    Args:
        image_hash: SHA-256 hash of the image file.
        *parts: Additional parts to include in the key (provider, model, filename, etc.).

    Returns:
        Cache key string with all parts joined by double underscores and rubric version appended.
    """
    sanitized = [p.replace("/", "_").replace(":", "_") for p in parts]
    return "__".join([image_hash, *sanitized, f"v{RUBRIC_VERSION}"])


def cache_key(image_hash: str, provider: str, model: str) -> str:
    """Generate a cache key for a given image and LLM configuration.

    Args:
        image_hash: SHA-256 hash of the image file.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cache key string in format: {hash}__{provider}__{model}__v{rubric_version}
    """
    return build_cache_key(image_hash, provider, model)


def assessment_cache_key(image_hash: str, filename: str, provider: str, model: str) -> str:
    """Generate a cache key for a filename assessment.

    Args:
        image_hash: SHA-256 hash of the image file.
        filename: The filename being assessed.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cache key string in format: {hash}__{filename}__{provider}__{model}__v{rubric_version}
    """
    return build_cache_key(image_hash, filename, provider, model)


T = TypeVar("T", bound=BaseModel)


class CacheStore(Generic[T]):
    """Generic cache store for Pydantic model payloads keyed by image hash and string fields.

    Args:
        entry_type: The Pydantic model class wrapping the cached payload.
        payload_field: Name of the field on entry_type that holds the payload.
        key_fields: Ordered tuple of field names used to build the cache key (after the image hash).
    """

    def __init__(
        self,
        entry_type: type[BaseCacheEntry],
        payload_field: str,
        key_fields: tuple[str, ...],
    ) -> None:
        self._entry_type = entry_type
        self._payload_field = payload_field
        self._key_fields = key_fields

    def load(self, cache_dir: Path, image_path: Path, **key_values: str) -> T | None:
        """Load a cached payload if it exists and all key values match.

        Args:
            cache_dir: Directory to search for the cache file.
            image_path: Path to the image file (used to compute hash).
            **key_values: Values for each field in key_fields.

        Returns:
            The cached payload model, or None on any miss or validation failure.
        """
        try:
            image_hash = sha256_file(image_path)
            key = build_cache_key(image_hash, *(key_values[f] for f in self._key_fields))
            cache_file = cache_dir / f"{key}.json"
            if not cache_file.exists():
                return None
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            entry = self._entry_type.model_validate(data)
            if entry.image_hash != image_hash or entry.rubric_version != RUBRIC_VERSION:
                return None
            for field_name in self._key_fields:
                if getattr(entry, field_name) != key_values[field_name]:
                    return None
            return cast(T, getattr(entry, self._payload_field))
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def save(self, cache_dir: Path, image_path: Path, payload: T, **key_values: str) -> None:
        """Save a payload to the cache.

        Args:
            cache_dir: Directory to write the cache file into (created if missing).
            image_path: Path to the image file (used to compute hash).
            payload: The Pydantic model instance to cache.
            **key_values: Values for each field in key_fields.
        """
        image_hash = sha256_file(image_path)
        key = build_cache_key(image_hash, *(key_values[f] for f in self._key_fields))
        cache_file = cache_dir / f"{key}.json"
        entry = self._entry_type(
            image_hash=image_hash,
            rubric_version=RUBRIC_VERSION,
            **{self._payload_field: payload},
            **key_values,
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            entry.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )


_names_store: CacheStore[ProposedName] = CacheStore(
    entry_type=CacheEntry,
    payload_field="proposed_name",
    key_fields=("provider", "model"),
)

_assessment_store: CacheStore[NameAssessment] = CacheStore(
    entry_type=AssessmentCacheEntry,
    payload_field="assessment",
    key_fields=("filename", "provider", "model"),
)

_analysis_store: CacheStore[ImageAnalysis] = CacheStore(
    entry_type=AnalysisCacheEntry,
    payload_field="analysis",
    key_fields=("filename", "provider", "model"),
)


def load_from_cache(
    cache_dir: Path,
    image_path: Path,
    provider: str,
    model: str,
) -> ProposedName | None:
    """Load a cached naming result if it exists and is valid.

    Args:
        cache_dir: Path to the cache/names directory.
        image_path: Path to the image file.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cached ProposedName if found and valid, None otherwise.
    """
    return _names_store.load(cache_dir, image_path, provider=provider, model=model)


def save_to_cache(
    cache_dir: Path,
    image_path: Path,
    provider: str,
    model: str,
    proposed_name: ProposedName,
) -> None:
    """Save a naming result to the cache.

    Args:
        cache_dir: Path to the cache/names directory.
        image_path: Path to the image file.
        provider: LLM provider name.
        model: Model name.
        proposed_name: The proposed filename to cache.
    """
    _names_store.save(cache_dir, image_path, proposed_name, provider=provider, model=model)


def load_assessment_from_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
) -> NameAssessment | None:
    """Load a cached assessment result if it exists and is valid.

    Args:
        cache_dir: Path to the cache/analysis directory.
        image_path: Path to the image file.
        filename: The filename being assessed.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cached NameAssessment if found and valid, None otherwise.
    """
    return _assessment_store.load(
        cache_dir, image_path, filename=filename, provider=provider, model=model
    )


def save_assessment_to_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
    assessment: NameAssessment,
) -> None:
    """Save an assessment result to the cache.

    Args:
        cache_dir: Path to the cache/analysis directory.
        image_path: Path to the image file.
        filename: The filename that was assessed.
        provider: LLM provider name.
        model: Model name.
        assessment: The assessment result to cache.
    """
    _assessment_store.save(
        cache_dir, image_path, assessment, filename=filename, provider=provider, model=model
    )


def load_analysis_from_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
) -> ImageAnalysis | None:
    """Load a cached unified analysis result if it exists and is valid.

    Args:
        cache_dir: Path to the cache/unified directory.
        image_path: Path to the image file.
        filename: The filename to check against cache.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cached ImageAnalysis if found and valid, None otherwise.
    """
    return _analysis_store.load(
        cache_dir, image_path, filename=filename, provider=provider, model=model
    )


def save_analysis_to_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
    analysis: ImageAnalysis,
) -> None:
    """Save a unified analysis result to the cache.

    Args:
        cache_dir: Path to the cache/unified directory.
        image_path: Path to the image file.
        filename: The filename that was analyzed.
        provider: LLM provider name.
        model: Model name.
        analysis: The analysis result to cache.
    """
    _analysis_store.save(
        cache_dir, image_path, analysis, filename=filename, provider=provider, model=model
    )
