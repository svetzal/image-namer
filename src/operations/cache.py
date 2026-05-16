"""Cache operations for storing and retrieving LLM results."""

import json
import logging
from pathlib import Path
from typing import Callable, Generic, TypeVar, cast

from pydantic import BaseModel, Field

from constants import RUBRIC_VERSION
from operations.models import ImageAnalysis
from utils.fs import sha256_file

logger = logging.getLogger(__name__)


class BaseCacheEntry(BaseModel):

    image_hash: str = Field(..., description="SHA-256 hash of the image")
    rubric_version: int = Field(..., description="Rubric version")


class AnalysisCacheEntry(BaseCacheEntry):

    filename: str = Field(..., description="Filename that was analyzed")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    analysis: ImageAnalysis = Field(..., description="Complete analysis result")


def build_cache_key(image_hash: str, *parts: str) -> str:
    """Cache key with all parts joined by double underscores, rubric version appended."""
    sanitized = [p.replace("/", "_").replace(":", "_") for p in parts]
    return "__".join([image_hash, *sanitized, f"v{RUBRIC_VERSION}"])


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
        hash_fn: Callable[[Path], str] = sha256_file,
    ) -> None:
        self._entry_type = entry_type
        self._payload_field = payload_field
        self._key_fields = key_fields
        self._hash_fn = hash_fn

    def load(self, cache_dir: Path, image_path: Path, **key_values: str) -> T | None:
        """Load a cached payload if it exists and all key values match."""
        cache_file: Path | None = None
        try:
            image_hash = self._hash_fn(image_path)
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
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.debug(
                "Cache load failed (image=%s, cache_file=%s): %s: %s",
                image_path, cache_file, type(e).__name__, e,
            )
            return None

    def save(self, cache_dir: Path, image_path: Path, payload: T, **key_values: str) -> None:
        image_hash = self._hash_fn(image_path)
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


_analysis_store: CacheStore[ImageAnalysis] = CacheStore(
    entry_type=AnalysisCacheEntry,
    payload_field="analysis",
    key_fields=("filename", "provider", "model"),
)


def load_analysis_from_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
) -> ImageAnalysis | None:
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
    _analysis_store.save(
        cache_dir, image_path, analysis, filename=filename, provider=provider, model=model
    )
