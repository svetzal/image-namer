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

class DescribeFilesystemAnalysisCache:

    @pytest.fixture
    def cache_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "cache"

    @pytest.fixture
    def cache(self, cache_dir: Path) -> FilesystemAnalysisCache:
        return FilesystemAnalysisCache(cache_dir, provider="ollama", model="gemma3:27b")

    class DescribeLoad:

        def should_delegate_to_load_analysis_from_cache(
            self, mocker, cache_dir: Path, cache: FilesystemAnalysisCache, tmp_image_path: Path
        ):
            mock_load = mocker.patch("operations.adapters.load_analysis_from_cache", return_value=None)

            cache.load(tmp_image_path, "sample.png")

            mock_load.assert_called_once_with(
                cache_dir, tmp_image_path, "sample.png", "ollama", "gemma3:27b"
            )

        def should_return_analysis_when_cache_hit(
            self, mocker, cache: FilesystemAnalysisCache, tmp_image_path: Path
        ):
            expected = make_analysis()
            mocker.patch("operations.adapters.load_analysis_from_cache", return_value=expected)

            result = cache.load(tmp_image_path, "sample.png")

            assert result is expected

        def should_return_none_when_cache_miss(
            self, mocker, cache: FilesystemAnalysisCache, tmp_image_path: Path
        ):
            mocker.patch("operations.adapters.load_analysis_from_cache", return_value=None)

            result = cache.load(tmp_image_path, "sample.png")

            assert result is None

    class DescribeSave:

        def should_delegate_to_save_analysis_to_cache(
            self, mocker, cache_dir: Path, cache: FilesystemAnalysisCache, tmp_image_path: Path
        ):
            mock_save = mocker.patch("operations.adapters.save_analysis_to_cache")
            analysis = make_analysis()

            cache.save(tmp_image_path, "sample.png", analysis)

            mock_save.assert_called_once_with(
                cache_dir, tmp_image_path, "sample.png", "ollama", "gemma3:27b", analysis
            )


# ---------------------------------------------------------------------------
# MojenticImageAnalyzer
# ---------------------------------------------------------------------------

class DescribeMojenticImageAnalyzer:

    @pytest.fixture
    def mock_llm(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def analyzer(self, mock_llm) -> MojenticImageAnalyzer:
        return MojenticImageAnalyzer(mock_llm)

    def should_delegate_analyze_to_analyze_image(
        self, mocker, analyzer: MojenticImageAnalyzer, mock_llm, tmp_image_path: Path
    ):
        expected = make_analysis(suitable=False, stem="golden-retriever--running-in-park")
        mock_analyze = mocker.patch("operations.adapters.analyze_image", return_value=expected)

        analyzer.analyze(tmp_image_path, "sample.png")

        mock_analyze.assert_called_once_with(tmp_image_path, "sample.png", llm=mock_llm)

    def should_return_image_analysis_result(
        self, mocker, analyzer: MojenticImageAnalyzer, tmp_image_path: Path
    ):
        expected = make_analysis(suitable=False, stem="golden-retriever--running-in-park")
        mocker.patch("operations.adapters.analyze_image", return_value=expected)

        result = analyzer.analyze(tmp_image_path, "sample.png")

        assert result is expected


# ---------------------------------------------------------------------------
# FilesystemRenamer
# ---------------------------------------------------------------------------

class DescribeFilesystemRenamer:

    @pytest.fixture
    def renamer(self) -> FilesystemRenamer:
        return FilesystemRenamer()

    def should_rename_file_on_disk(self, tmp_path: Path, renamer: FilesystemRenamer):
        source = tmp_path / "original.png"
        source.write_bytes(b"image-data")
        destination = tmp_path / "renamed.png"

        renamer.rename(source, destination)

        assert destination.exists()
        assert not source.exists()

    def should_preserve_file_contents_after_rename(self, tmp_path: Path, renamer: FilesystemRenamer):
        source = tmp_path / "original.png"
        source.write_bytes(b"image-data")
        destination = tmp_path / "renamed.png"

        renamer.rename(source, destination)

        assert destination.read_bytes() == b"image-data"


# ---------------------------------------------------------------------------
# FilesystemMarkdownFiles
# ---------------------------------------------------------------------------

class DescribeFilesystemMarkdownFiles:

    @pytest.fixture
    def markdown_files(self) -> FilesystemMarkdownFiles:
        return FilesystemMarkdownFiles()

    class DescribeFindMarkdownFiles:

        def should_find_markdown_files_non_recursively(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            (tmp_path / "top.md").write_text("# Top")
            subdir = tmp_path / "sub"
            subdir.mkdir()
            (subdir / "nested.md").write_text("# Nested")

            result = markdown_files.find_markdown_files(tmp_path, recursive=False)

            assert len(result) == 1
            assert result[0].name == "top.md"

        def should_find_markdown_files_recursively(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            (tmp_path / "top.md").write_text("# Top")
            subdir = tmp_path / "sub"
            subdir.mkdir()
            (subdir / "nested.md").write_text("# Nested")

            result = markdown_files.find_markdown_files(tmp_path, recursive=True)

            names = {p.name for p in result}
            assert names == {"top.md", "nested.md"}

        def should_return_empty_list_when_no_markdown_files(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            (tmp_path / "image.png").write_bytes(b"")

            result = markdown_files.find_markdown_files(tmp_path, recursive=False)

            assert result == []

        def should_not_include_non_md_files(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            (tmp_path / "notes.md").write_text("# Notes")
            (tmp_path / "data.txt").write_text("data")

            result = markdown_files.find_markdown_files(tmp_path, recursive=False)

            assert all(p.suffix == ".md" for p in result)

    class DescribeReadMarkdownContent:

        def should_return_file_content(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            md_file = tmp_path / "notes.md"
            md_file.write_text("# Hello\n\nWorld", encoding="utf-8")

            result = markdown_files.read_markdown_content(md_file)

            assert result == "# Hello\n\nWorld"

    class DescribeWriteMarkdownContent:

        def should_write_content_to_file(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            md_file = tmp_path / "notes.md"

            markdown_files.write_markdown_content(md_file, "# Written\n")

            assert md_file.read_text(encoding="utf-8") == "# Written\n"

        def should_overwrite_existing_content(
            self, tmp_path: Path, markdown_files: FilesystemMarkdownFiles
        ):
            md_file = tmp_path / "notes.md"
            md_file.write_text("# Original", encoding="utf-8")

            markdown_files.write_markdown_content(md_file, "# Updated\n")

            assert md_file.read_text(encoding="utf-8") == "# Updated\n"
