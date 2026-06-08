"""Tests for concrete adapter implementations."""

import pytest
from pathlib import Path

from conftest import make_analysis
from operations.adapters import (
    FilesystemAnalysisCache,
    FilesystemMarkdownFiles,
    FilesystemRenamer,
    MojenticImageAnalyzer,
)


# ---------------------------------------------------------------------------
# FilesystemAnalysisCache
# ---------------------------------------------------------------------------

@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


@pytest.fixture
def cache(cache_dir: Path) -> FilesystemAnalysisCache:
    return FilesystemAnalysisCache(cache_dir, provider="ollama", model="gemma3:27b")


def should_return_none_when_no_cache_exists(
    cache: FilesystemAnalysisCache, tmp_image_path: Path
):
    result = cache.load(tmp_image_path, "sample.png")

    assert result is None


def should_return_previously_saved_analysis(
    cache: FilesystemAnalysisCache, tmp_image_path: Path
):
    expected = make_analysis()

    cache.save(tmp_image_path, "sample.png", expected)
    result = cache.load(tmp_image_path, "sample.png")

    assert result == expected


def should_return_none_when_cache_miss(
    cache: FilesystemAnalysisCache, tmp_image_path: Path
):
    cache.save(tmp_image_path, "other.png", make_analysis())

    result = cache.load(tmp_image_path, "sample.png")

    assert result is None


def should_persist_analysis_to_cache_directory(
    cache_dir: Path, cache: FilesystemAnalysisCache, tmp_image_path: Path
):
    analysis = make_analysis()

    cache.save(tmp_image_path, "sample.png", analysis)

    json_files = list(cache_dir.glob("*.json"))
    assert len(json_files) >= 1


# ---------------------------------------------------------------------------
# MojenticImageAnalyzer
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_analyze(mocker):
    return mocker.Mock()


@pytest.fixture
def analyzer(mock_llm, mock_analyze) -> MojenticImageAnalyzer:
    return MojenticImageAnalyzer(mock_llm, analyze_fn=mock_analyze)


def should_delegate_analyze_to_analyze_image(
    analyzer: MojenticImageAnalyzer, mock_llm, mock_analyze, tmp_image_path: Path
):
    expected = make_analysis(suitable=False, stem="golden-retriever--running-in-park")
    mock_analyze.return_value = expected

    analyzer.analyze(tmp_image_path, "sample.png")

    mock_analyze.assert_called_once_with(tmp_image_path, "sample.png", llm=mock_llm)


def should_return_image_analysis_result(
    analyzer: MojenticImageAnalyzer, mock_analyze, tmp_image_path: Path
):
    expected = make_analysis(suitable=False, stem="golden-retriever--running-in-park")
    mock_analyze.return_value = expected

    result = analyzer.analyze(tmp_image_path, "sample.png")

    assert result is expected


# ---------------------------------------------------------------------------
# FilesystemRenamer
# ---------------------------------------------------------------------------

@pytest.fixture
def renamer() -> FilesystemRenamer:
    return FilesystemRenamer()


def should_rename_file_on_disk(tmp_path: Path, renamer: FilesystemRenamer):
    source = tmp_path / "original.png"
    source.write_bytes(b"image-data")
    destination = tmp_path / "renamed.png"

    renamer.rename(source, destination)

    assert destination.exists()
    assert not source.exists()


def should_preserve_file_contents_after_rename(tmp_path: Path, renamer: FilesystemRenamer):
    source = tmp_path / "original.png"
    source.write_bytes(b"image-data")
    destination = tmp_path / "renamed.png"

    renamer.rename(source, destination)

    assert destination.read_bytes() == b"image-data"


# ---------------------------------------------------------------------------
# FilesystemMarkdownFiles
# ---------------------------------------------------------------------------

@pytest.fixture
def markdown_files() -> FilesystemMarkdownFiles:
    return FilesystemMarkdownFiles()


def should_find_markdown_files_non_recursively(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    (tmp_path / "top.md").write_text("# Top")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.md").write_text("# Nested")

    result = markdown_files.find_markdown_files(tmp_path, recursive=False)

    assert len(result) == 1
    assert result[0].name == "top.md"


def should_find_markdown_files_recursively(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    (tmp_path / "top.md").write_text("# Top")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.md").write_text("# Nested")

    result = markdown_files.find_markdown_files(tmp_path, recursive=True)

    names = {p.name for p in result}
    assert names == {"top.md", "nested.md"}


def should_return_empty_list_when_no_markdown_files(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    (tmp_path / "image.png").write_bytes(b"")

    result = markdown_files.find_markdown_files(tmp_path, recursive=False)

    assert result == []


def should_not_include_non_md_files(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    (tmp_path / "notes.md").write_text("# Notes")
    (tmp_path / "data.txt").write_text("data")

    result = markdown_files.find_markdown_files(tmp_path, recursive=False)

    assert all(p.suffix == ".md" for p in result)


def should_return_file_content(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Hello\n\nWorld", encoding="utf-8")

    result = markdown_files.read_markdown_content(md_file)

    assert result == "# Hello\n\nWorld"


def should_write_content_to_file(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    md_file = tmp_path / "notes.md"

    markdown_files.write_markdown_content(md_file, "# Written\n")

    assert md_file.read_text(encoding="utf-8") == "# Written\n"


def should_overwrite_existing_content(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles
):
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Original", encoding="utf-8")

    markdown_files.write_markdown_content(md_file, "# Updated\n")

    assert md_file.read_text(encoding="utf-8") == "# Updated\n"


def should_preserve_original_and_leave_no_tmp_when_replace_fails(
    tmp_path: Path, markdown_files: FilesystemMarkdownFiles, mocker
):
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Original", encoding="utf-8")

    mocker.patch("operations.adapters.os.replace", side_effect=OSError("disk full"))

    with pytest.raises(OSError):
        markdown_files.write_markdown_content(md_file, "# New content\n")

    assert md_file.read_text(encoding="utf-8") == "# Original"
    assert list(tmp_path.glob("*.tmp")) == []
