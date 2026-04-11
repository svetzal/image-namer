"""Tests for single-image processing orchestration."""

import pytest

from conftest import make_analysis
from operations.models import ProposedName, RenameStatus
from operations.ports import AnalysisCachePort, ImageAnalyzerPort, ProgressCallback
from operations.process_image import (
    get_or_generate_analysis,
    process_single_image,
    resolve_final_name,
)


# ---------------------------------------------------------------------------
# process_single_image
# ---------------------------------------------------------------------------

def should_return_unchanged_when_cached_analysis_is_suitable(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis()
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.UNCHANGED
    assert result.final == tmp_image_path.name


def should_not_call_analyze_when_cached_analysis_is_suitable(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis()
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    analyzer.analyze.assert_not_called()


def should_call_analyze_image_and_cache_result_on_cache_miss(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = make_analysis()

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    analyzer.analyze.assert_called_once()
    cache.save.assert_called_once()
    assert result.status == RenameStatus.UNCHANGED


def should_return_error_when_analyze_raises(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.side_effect = RuntimeError("LLM failed")

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.ERROR
    assert result.proposed == "ERROR"


def should_propose_new_name_when_analysis_unsuitable(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(suitable=False, stem="new-name")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.RENAMED
    assert result.proposed == "new-name.png"
    assert result.final == "new-name.png"


def should_return_unchanged_when_stem_matches_proposed(tmp_path, mocker):
    img = tmp_path / "already-named.png"
    img.write_bytes(b"x")
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(suitable=False, stem="already-named")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        img, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.UNCHANGED
    assert result.final == "already-named.png"


def should_resolve_collision_with_existing_file(tmp_path, mocker):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    (tmp_path / "taken-name.png").write_bytes(b"existing")
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(suitable=False, stem="taken-name")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        img, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.COLLISION
    assert result.final == "taken-name-2.png"


def should_resolve_collision_with_planned_names(tmp_path, mocker):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    planned = {"wanted-name.png"}
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(suitable=False, stem="wanted-name")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        img, analyzer, cache, planned, "ollama", "gemma3:27b"
    )

    assert result.status == RenameStatus.COLLISION
    assert result.final == "wanted-name-2.png"


def should_add_final_name_to_planned_names(tmp_path, mocker):
    img = tmp_path / "source.png"
    img.write_bytes(b"x")
    planned: set[str] = set()
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(suitable=False, stem="new-name")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    process_single_image(
        img, analyzer, cache, planned, "ollama", "gemma3:27b"
    )

    assert "new-name.png" in planned


def should_populate_reasoning_on_processing_result(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis(reasoning="The current name is descriptive.")
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.reasoning == "The current name is descriptive."


def should_populate_cached_true_when_analysis_comes_from_cache(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis()
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.cached is True


def should_populate_cached_false_when_analysis_is_freshly_generated(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = make_analysis()

    result = process_single_image(
        tmp_image_path, analyzer, cache, set(), "ollama", "gemma3:27b"
    )

    assert result.cached is False


# ---------------------------------------------------------------------------
# get_or_generate_analysis
# ---------------------------------------------------------------------------

def should_return_cached_analysis_when_available(tmp_image_path, mocker):
    expected = make_analysis()
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = expected
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    result, cached = get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
    )

    assert result == expected
    analyzer.analyze.assert_not_called()


def should_call_analyze_image_on_cache_miss(tmp_image_path, mocker):
    expected = make_analysis(suitable=False, stem="new-name")
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = expected

    result, cached = get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
    )

    assert result == expected


def should_save_to_cache_on_miss(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = make_analysis()

    get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
    )

    cache.save.assert_called_once()


def should_raise_on_llm_failure(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.side_effect = RuntimeError("LLM failed")

    with pytest.raises(RuntimeError, match="LLM failed"):
        get_or_generate_analysis(
            tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
        )


def should_return_true_for_cached_when_analysis_is_in_cache(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = make_analysis()
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)

    _, cached = get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
    )

    assert cached is True


def should_return_false_for_cached_when_analysis_is_not_in_cache(tmp_image_path, mocker):
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = make_analysis()

    _, cached = get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b"
    )

    assert cached is False


def should_call_on_cache_hit_callback_when_analysis_is_cached(tmp_image_path, mocker):
    analysis = make_analysis()
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = analysis
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    progress = mocker.Mock(spec=ProgressCallback)

    get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b", progress
    )

    progress.on_cache_hit.assert_called_once_with(tmp_image_path, analysis)
    progress.on_cache_miss.assert_not_called()
    progress.on_analysis_complete.assert_not_called()


def should_call_on_cache_miss_and_on_analysis_complete_callbacks_on_miss(tmp_image_path, mocker):
    analysis = make_analysis(suitable=False, stem="new-name")
    cache = mocker.Mock(spec=AnalysisCachePort)
    cache.load.return_value = None
    analyzer = mocker.Mock(spec=ImageAnalyzerPort)
    analyzer.analyze.return_value = analysis
    progress = mocker.Mock(spec=ProgressCallback)
    call_order = []
    progress.on_cache_miss.side_effect = lambda path: call_order.append("miss")
    progress.on_analysis_complete.side_effect = lambda path, a: call_order.append("complete")

    get_or_generate_analysis(
        tmp_image_path, "sample.png", analyzer, cache, "ollama", "gemma3:27b", progress
    )

    progress.on_cache_miss.assert_called_once_with(tmp_image_path)
    progress.on_analysis_complete.assert_called_once_with(tmp_image_path, analysis)
    progress.on_cache_hit.assert_not_called()
    assert call_order == ["miss", "complete"]


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
