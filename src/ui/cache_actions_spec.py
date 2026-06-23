"""Tests for cache_actions orchestration functions."""

from unittest.mock import Mock

from operations.ports import CacheClearerPort
from ui.cache_actions import clear_cache, resolve_cache_target


def should_resolve_cache_dir_under_cache_root(tmp_path):
    clearer = Mock(spec=CacheClearerPort)
    clearer.ensure_layout.return_value = tmp_path
    clearer.cache_exists.return_value = True

    target = resolve_cache_target(tmp_path, clearer)

    clearer.ensure_layout.assert_called_once_with(tmp_path)
    clearer.cache_exists.assert_called_once_with(tmp_path / "cache")
    assert target.cache_dir == tmp_path / "cache"
    assert target.exists is True


def should_report_missing_cache_when_not_present(tmp_path):
    clearer = Mock(spec=CacheClearerPort)
    clearer.ensure_layout.return_value = tmp_path
    clearer.cache_exists.return_value = False

    target = resolve_cache_target(tmp_path, clearer)

    assert target.exists is False


def should_default_to_cwd_when_folder_is_none(tmp_path, mocker):
    clearer = Mock(spec=CacheClearerPort)
    clearer.ensure_layout.return_value = tmp_path
    clearer.cache_exists.return_value = False
    mock_cwd = mocker.patch("ui.cache_actions.Path.cwd", return_value=tmp_path)

    resolve_cache_target(None, clearer)

    clearer.ensure_layout.assert_called_once_with(mock_cwd.return_value)


def should_clear_cache_via_port(tmp_path):
    clearer = Mock(spec=CacheClearerPort)
    cache_dir = tmp_path / "cache"

    result = clear_cache(cache_dir, clearer)

    clearer.clear.assert_called_once_with(cache_dir)
    assert result.success is True
    assert result.error_message is None


def should_return_error_result_on_io_failure(tmp_path):
    clearer = Mock(spec=CacheClearerPort)
    cache_dir = tmp_path / "cache"
    clearer.clear.side_effect = OSError("permission denied")

    result = clear_cache(cache_dir, clearer)

    assert result.success is False
    assert "permission denied" in (result.error_message or "")
