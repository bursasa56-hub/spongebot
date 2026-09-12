from pathlib import Path

from bot.db.session import ensure_db_dir


def test_ensure_db_dir_creates_nested_directory(tmp_path):
    target = tmp_path / "data" / "nested" / "bot.db"
    ensure_db_dir(str(target))
    assert target.parent.is_dir()


def test_ensure_db_dir_memory_is_noop():
    ensure_db_dir(":memory:")
