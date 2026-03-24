"""Tests for single-image processing orchestration."""

import pytest

from operations.models import ImageAnalysis, ProposedName, RenameStatus
from operations.process_image import (
    get_or_generate_analysis,
    process_single_image,
    resolve_final_name,
)


# ---------------------------------------------------------------------------
# process_single_image
# ---------------------------------------------------------------------------

def should_return_unchanged_when_cached_analysis_is_suitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=True,
            proposed_name=ProposedName(stem="sample", extension=".png"),
        ),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.UNCHANGED
    assert result.final == tmp_image_path.name


def should_not_call_analyze_when_cached_analysis_is_suitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=True,
            proposed_name=ProposedName(stem="sample", extension=".png"),
        ),
    )
    mock_analyze = mocker.patch("operations.process_image.analyze_image")

    process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    mock_analyze.assert_not_called()


def should_call_analyze_image_and_cache_result_on_cache_miss(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=None,
    )
    mock_analyze = mocker.patch(
        "operations.process_image.analyze_image",
        return_value=ImageAnalysis(
            current_name_suitable=True,
            proposed_name=ProposedName(stem="sample", extension=".png"),
        ),
    )
    mock_save = mocker.patch("operations.process_image.save_analysis_to_cache")

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    mock_analyze.assert_called_once()
    mock_save.assert_called_once()
    assert result.status == RenameStatus.UNCHANGED


def should_return_error_when_analyze_raises(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.analyze_image",
        side_effect=RuntimeError("LLM failed"),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.ERROR
    assert result.proposed == "ERROR"


def should_propose_new_name_when_analysis_unsuitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(stem="new-name", extension=".png"),
        ),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.RENAMED
    assert result.proposed == "new-name.png"
    assert result.final == "new-name.png"


def should_return_unchanged_when_stem_matches_proposed(
    tmp_path, fake_llm, cache_dirs, mocker
):
    img = tmp_path / "already-named.png"
    img.write_bytes(b"x")
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(stem="already-named", extension=".png"),
        ),
    )

    result = process_single_image(
        img, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.UNCHANGED
    assert result.final == "already-named.png"


def should_resolve_collision_with_existing_file(
    tmp_path, fake_llm, cache_dirs, mocker
):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    (tmp_path / "taken-name.png").write_bytes(b"existing")
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(stem="taken-name", extension=".png"),
        ),
    )

    result = process_single_image(
        img, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.COLLISION
    assert result.final == "taken-name-2.png"


def should_resolve_collision_with_planned_names(
    tmp_path, fake_llm, cache_dirs, mocker
):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    planned = {"wanted-name.png"}
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(stem="wanted-name", extension=".png"),
        ),
    )

    result = process_single_image(
        img, fake_llm, planned, cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.COLLISION
    assert result.final == "wanted-name-2.png"


def should_add_final_name_to_planned_names(
    tmp_path, fake_llm, cache_dirs, mocker
):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    planned: set[str] = set()
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=ImageAnalysis(
            current_name_suitable=False,
            proposed_name=ProposedName(stem="new-name", extension=".png"),
        ),
    )

    process_single_image(
        img, fake_llm, planned, cache_dirs, "ollama", "gemma3:27b"
    )

    assert "new-name.png" in planned


# ---------------------------------------------------------------------------
# get_or_generate_analysis
# ---------------------------------------------------------------------------

def should_return_cached_analysis_when_available(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    expected = ImageAnalysis(
        current_name_suitable=True,
        proposed_name=ProposedName(stem="sample", extension=".png"),
    )
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=expected,
    )
    mock_analyze = mocker.patch("operations.process_image.analyze_image")

    result = get_or_generate_analysis(
        tmp_image_path, "sample.png", fake_llm,
        cache_dirs / "cache" / "unified", "ollama", "gemma3:27b"
    )

    assert result == expected
    mock_analyze.assert_not_called()


def should_call_analyze_image_on_cache_miss(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    expected = ImageAnalysis(
        current_name_suitable=False,
        proposed_name=ProposedName(stem="new-name", extension=".png"),
    )
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.analyze_image",
        return_value=expected,
    )
    mocker.patch("operations.process_image.save_analysis_to_cache")

    result = get_or_generate_analysis(
        tmp_image_path, "sample.png", fake_llm,
        cache_dirs / "cache" / "unified", "ollama", "gemma3:27b"
    )

    assert result == expected


def should_save_to_cache_on_miss(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.analyze_image",
        return_value=ImageAnalysis(
            current_name_suitable=True,
            proposed_name=ProposedName(stem="sample", extension=".png"),
        ),
    )
    mock_save = mocker.patch("operations.process_image.save_analysis_to_cache")

    get_or_generate_analysis(
        tmp_image_path, "sample.png", fake_llm,
        cache_dirs / "cache" / "unified", "ollama", "gemma3:27b"
    )

    mock_save.assert_called_once()


def should_raise_on_llm_failure(tmp_image_path, fake_llm, cache_dirs, mocker):
    mocker.patch(
        "operations.process_image.load_analysis_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.analyze_image",
        side_effect=RuntimeError("LLM failed"),
    )

    with pytest.raises(RuntimeError, match="LLM failed"):
        get_or_generate_analysis(
            tmp_image_path, "sample.png", fake_llm,
            cache_dirs / "cache" / "unified", "ollama", "gemma3:27b"
        )


# ---------------------------------------------------------------------------
# resolve_final_name
# ---------------------------------------------------------------------------

def should_return_unchanged_when_stem_matches(tmp_path):
    img = tmp_path / "already-named.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="already-named", extension=".png")

    proposed_fn, final_fn, status = resolve_final_name(img, proposed, set())

    assert status == RenameStatus.UNCHANGED
    assert final_fn == img.name


def should_return_renamed_when_no_collision(tmp_path):
    img = tmp_path / "old-name.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="new-name", extension=".png")

    proposed_fn, final_fn, status = resolve_final_name(img, proposed, set())

    assert status == RenameStatus.RENAMED
    assert final_fn == "new-name.png"
    assert proposed_fn == "new-name.png"


def should_return_collision_when_disk_file_exists(tmp_path):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    (tmp_path / "taken-name.png").write_bytes(b"existing")
    proposed = ProposedName(stem="taken-name", extension=".png")

    proposed_fn, final_fn, status = resolve_final_name(img, proposed, set())

    assert status == RenameStatus.COLLISION
    assert final_fn == "taken-name-2.png"


def should_return_collision_when_planned_name_taken(tmp_path):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="wanted-name", extension=".png")
    planned = {"wanted-name.png"}

    proposed_fn, final_fn, status = resolve_final_name(img, proposed, planned)

    assert status == RenameStatus.COLLISION
    assert final_fn == "wanted-name-2.png"


def should_add_resolved_name_to_planned_names(tmp_path):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="new-name", extension=".png")
    planned: set[str] = set()

    resolve_final_name(img, proposed, planned)

    assert "new-name.png" in planned


def should_normalize_extension_without_dot(tmp_path):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="new-name", extension="jpg")

    _, final_fn, _ = resolve_final_name(img, proposed, set())

    assert final_fn.endswith(".jpg")


def should_use_fallback_extension_when_empty(tmp_path):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    proposed = ProposedName(stem="new-name", extension="")

    _, final_fn, _ = resolve_final_name(img, proposed, set())

    assert final_fn.endswith(".png")
