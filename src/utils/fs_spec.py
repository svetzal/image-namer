import hashlib
from pathlib import Path

from utils.fs import sha256_file, ensure_cache_layout
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
