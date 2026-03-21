"""Tests for single-image processing orchestration."""

from operations.models import NameAssessment, ProposedName, RenameStatus
from operations.process_image import process_single_image


def should_return_unchanged_when_cached_assessment_is_suitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=True),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.UNCHANGED
    assert result.final == tmp_image_path.name


def should_not_call_generate_when_assessment_is_suitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=True),
    )
    mock_generate = mocker.patch("operations.process_image.generate_name")

    process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    mock_generate.assert_not_called()


def should_call_assess_name_and_cache_result_on_cache_miss(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=None,
    )
    mock_assess = mocker.patch(
        "operations.process_image.assess_name",
        return_value=NameAssessment(suitable=True),
    )
    mock_save_assessment = mocker.patch(
        "operations.process_image.save_assessment_to_cache"
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    mock_assess.assert_called_once()
    mock_save_assessment.assert_called_once()
    assert result.status == RenameStatus.UNCHANGED


def should_return_error_when_assessment_raises(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.assess_name",
        side_effect=RuntimeError("LLM failed"),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.ERROR
    assert result.proposed == "ERROR"


def should_generate_name_when_assessment_unsuitable(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.generate_name",
        return_value=ProposedName(stem="new-name", extension=".png"),
    )
    mocker.patch("operations.process_image.save_to_cache")

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.RENAMED
    assert result.proposed == "new-name.png"
    assert result.final == "new-name.png"


def should_return_error_when_generation_raises(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=None,
    )
    mocker.patch(
        "operations.process_image.generate_name",
        side_effect=RuntimeError("LLM failed"),
    )

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.ERROR


def should_use_cached_name_when_available(
    tmp_image_path, fake_llm, cache_dirs, mocker
):
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=ProposedName(stem="cached-name", extension=".png"),
    )
    mock_generate = mocker.patch("operations.process_image.generate_name")

    result = process_single_image(
        tmp_image_path, fake_llm, set(), cache_dirs, "ollama", "gemma3:27b"
    )

    mock_generate.assert_not_called()
    assert result.proposed == "cached-name.png"


def should_return_unchanged_when_stem_matches_proposed(
    tmp_path, fake_llm, cache_dirs, mocker
):
    img = tmp_path / "already-named.png"
    img.write_bytes(b"x")
    mocker.patch(
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=ProposedName(stem="already-named", extension=".png"),
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
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=ProposedName(stem="taken-name", extension=".png"),
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
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=ProposedName(stem="wanted-name", extension=".png"),
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
        "operations.process_image.load_assessment_from_cache",
        return_value=NameAssessment(suitable=False),
    )
    mocker.patch(
        "operations.process_image.load_from_cache",
        return_value=ProposedName(stem="new-name", extension=".png"),
    )

    process_single_image(
        img, fake_llm, planned, cache_dirs, "ollama", "gemma3:27b"
    )

    assert "new-name.png" in planned
