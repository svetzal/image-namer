"""Cache operations for storing and retrieving LLM results."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from constants import RUBRIC_VERSION
from operations.models import ImageAnalysis, NameAssessment, ProposedName
from utils.fs import sha256_file


class CacheEntry(BaseModel):
    """A cached LLM result for an image naming operation.

    Attributes:
        image_hash: SHA-256 hash of the image file.
        provider: LLM provider name (e.g., 'ollama', 'openai').
        model: Model name (e.g., 'gemma3:27b', 'gpt-4o').
        rubric_version: Version of the naming rubric used.
        proposed_name: The proposed filename from the LLM.
    """
    image_hash: str = Field(..., description="SHA-256 hash of the image")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    rubric_version: int = Field(..., description="Rubric version")
    proposed_name: ProposedName = Field(..., description="Proposed filename")


def cache_key(image_hash: str, provider: str, model: str) -> str:
    """Generate a cache key for a given image and LLM configuration.

    Args:
        image_hash: SHA-256 hash of the image file.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cache key string in format: {hash}__{provider}__{model}__v{rubric_version}
    """
    # Sanitize provider and model to be filesystem-safe
    safe_provider = provider.replace("/", "_").replace(":", "_")
    safe_model = model.replace("/", "_").replace(":", "_")
    return f"{image_hash}__{safe_provider}__{safe_model}__v{RUBRIC_VERSION}"


def load_from_cache(
    cache_dir: Path,
    image_path: Path,
    provider: str,
    model: str,
) -> Optional[ProposedName]:
    """Load a cached naming result if it exists and is valid.

    Args:
        cache_dir: Path to the cache/names directory.
        image_path: Path to the image file.
        provider: LLM provider name.
        model: Model name.

    Returns:
        Cached ProposedName if found and valid, None otherwise.
    """
    try:
        image_hash = sha256_file(image_path)
        key = cache_key(image_hash, provider, model)
        cache_file = cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        data = json.loads(cache_file.read_text(encoding="utf-8"))
        entry = CacheEntry.model_validate(data)

        # Validate that the cached entry matches our current parameters
        if (
            entry.image_hash != image_hash
            or entry.provider != provider
            or entry.model != model
            or entry.rubric_version != RUBRIC_VERSION
        ):
            return None

        return entry.proposed_name

    except (OSError, json.JSONDecodeError, ValueError):
        # If anything goes wrong reading/parsing cache, treat as cache miss
        return None


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
    image_hash = sha256_file(image_path)
    key = cache_key(image_hash, provider, model)
    cache_file = cache_dir / f"{key}.json"

    entry = CacheEntry(
        image_hash=image_hash,
        provider=provider,
        model=model,
        rubric_version=RUBRIC_VERSION,
        proposed_name=proposed_name,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        entry.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


class AssessmentCacheEntry(BaseModel):
    """A cached LLM result for an image name assessment operation.

    Attributes:
        image_hash: SHA-256 hash of the image file.
        filename: The filename that was assessed.
        provider: LLM provider name (e.g., 'ollama', 'openai').
        model: Model name (e.g., 'gemma3:27b', 'gpt-4o').
        rubric_version: Version of the naming rubric used.
        assessment: The assessment result from the LLM.
    """
    image_hash: str = Field(..., description="SHA-256 hash of the image")
    filename: str = Field(..., description="Filename that was assessed")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    rubric_version: int = Field(..., description="Rubric version")
    assessment: NameAssessment = Field(..., description="Assessment result")


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
    # Sanitize filename, provider and model to be filesystem-safe
    safe_filename = filename.replace("/", "_").replace(":", "_")
    safe_provider = provider.replace("/", "_").replace(":", "_")
    safe_model = model.replace("/", "_").replace(":", "_")
    return f"{image_hash}__{safe_filename}__{safe_provider}__{safe_model}__v{RUBRIC_VERSION}"


def load_assessment_from_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
) -> Optional[NameAssessment]:
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
    try:
        image_hash = sha256_file(image_path)
        key = assessment_cache_key(image_hash, filename, provider, model)
        cache_file = cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        data = json.loads(cache_file.read_text(encoding="utf-8"))
        entry = AssessmentCacheEntry.model_validate(data)

        # Validate that the cached entry matches our current parameters
        if (
            entry.image_hash != image_hash
            or entry.filename != filename
            or entry.provider != provider
            or entry.model != model
            or entry.rubric_version != RUBRIC_VERSION
        ):
            return None

        return entry.assessment

    except (OSError, json.JSONDecodeError, ValueError):
        # If anything goes wrong reading/parsing cache, treat as cache miss
        return None


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
    image_hash = sha256_file(image_path)
    key = assessment_cache_key(image_hash, filename, provider, model)
    cache_file = cache_dir / f"{key}.json"

    entry = AssessmentCacheEntry(
        image_hash=image_hash,
        filename=filename,
        provider=provider,
        model=model,
        rubric_version=RUBRIC_VERSION,
        assessment=assessment,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        entry.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )


class AnalysisCacheEntry(BaseModel):
    """A cached unified analysis result for an image.

    Attributes:
        image_hash: SHA-256 hash of the image file.
        filename: The filename that was analyzed.
        provider: LLM provider name.
        model: Model name.
        rubric_version: Version of the naming rubric used.
        analysis: The complete analysis result.
    """
    image_hash: str = Field(..., description="SHA-256 hash of the image")
    filename: str = Field(..., description="Filename that was analyzed")
    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Model name")
    rubric_version: int = Field(..., description="Rubric version")
    analysis: ImageAnalysis = Field(..., description="Complete analysis result")


def load_analysis_from_cache(
    cache_dir: Path,
    image_path: Path,
    filename: str,
    provider: str,
    model: str,
) -> Optional[ImageAnalysis]:
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
    try:
        image_hash = sha256_file(image_path)
        key = assessment_cache_key(image_hash, filename, provider, model)
        cache_file = cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        data = json.loads(cache_file.read_text(encoding="utf-8"))
        entry = AnalysisCacheEntry.model_validate(data)

        # Validate cache entry matches current parameters
        if (
            entry.image_hash != image_hash
            or entry.filename != filename
            or entry.provider != provider
            or entry.model != model
            or entry.rubric_version != RUBRIC_VERSION
        ):
            return None

        return entry.analysis

    except (OSError, json.JSONDecodeError, ValueError):
        return None


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
    image_hash = sha256_file(image_path)
    key = assessment_cache_key(image_hash, filename, provider, model)
    cache_file = cache_dir / f"{key}.json"

    entry = AnalysisCacheEntry(
        image_hash=image_hash,
        filename=filename,
        provider=provider,
        model=model,
        rubric_version=RUBRIC_VERSION,
        analysis=analysis,
    )

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        entry.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
