import hashlib
from pathlib import Path

from utils.fs import collect_image_files, ensure_cache_layout, sha256_file
from constants import RUBRIC_VERSION


def should_compute_sha256_for_small_file(tmp_path: Path) -> None:
    p = tmp_path / "data.bin"
    data = b"hello world\n" * 3 + b"\x00\x01\x02"
    p.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()

    result = sha256_file(p)

    assert result == expected


def should_ensure_cache_layout_and_write_version(tmp_path: Path) -> None:
    root = tmp_path

    cache_root = ensure_cache_layout(root)

    assert cache_root == root / ".image_namer"
    assert (cache_root / "cache" / "analysis").is_dir()
    assert (cache_root / "cache" / "names").is_dir()
    assert (cache_root / "cache" / "refs").is_dir()
    assert (cache_root / "runs").is_dir()

    version_file = cache_root / "version"
    assert version_file.is_file()
    assert version_file.read_text(encoding="utf-8") == f"{RUBRIC_VERSION}\n"

    before = version_file.read_text(encoding="utf-8")

    # Idempotency: calling again should not crash or rewrite different content
    cache_root2 = ensure_cache_layout(root)

    after = version_file.read_text(encoding="utf-8")

    assert cache_root2 == cache_root
    assert before == after


def should_collect_png_and_jpg_files(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.jpg").write_bytes(b"y")
    (tmp_path / "c.txt").write_text("not an image")

    files = collect_image_files(tmp_path, recursive=False)

    assert len(files) == 2
    assert all(f.suffix in {".png", ".jpg"} for f in files)


def should_exclude_non_image_files(tmp_path: Path) -> None:
    (tmp_path / "doc.txt").write_text("text")
    (tmp_path / "data.csv").write_text("csv")

    files = collect_image_files(tmp_path, recursive=False)

    assert files == []


def should_collect_recursively_when_flag_set(tmp_path: Path) -> None:
    (tmp_path / "root.png").write_bytes(b"x")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.png").write_bytes(b"y")

    files = collect_image_files(tmp_path, recursive=True)

    assert len(files) == 2


def should_not_collect_recursively_when_flag_false(tmp_path: Path) -> None:
    (tmp_path / "root.png").write_bytes(b"x")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "nested.png").write_bytes(b"y")

    files = collect_image_files(tmp_path, recursive=False)

    assert len(files) == 1
    assert files[0].name == "root.png"


def should_return_sorted_files(tmp_path: Path) -> None:
    (tmp_path / "c.png").write_bytes(b"x")
    (tmp_path / "a.png").write_bytes(b"y")
    (tmp_path / "b.png").write_bytes(b"z")

    files = collect_image_files(tmp_path, recursive=False)

    assert [f.name for f in files] == ["a.png", "b.png", "c.png"]
