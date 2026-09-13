from urllib.parse import urlsplit

import pytest

from bot.db.session import normalize_database_url


@pytest.mark.parametrize(
    "raw",
    [
        "postgres://u:p@h:5432/db",
        "postgresql://u:p@h:5432/db",
    ],
)
def test_normalize_plain_postgres_url(raw):
    url, connect_args = normalize_database_url(raw)

    parts = urlsplit(url)
    assert parts.scheme == "postgresql+asyncpg"
    assert parts.netloc == "u:p@h:5432"
    assert parts.path == "/db"
    assert parts.query == ""
    assert connect_args == {}


def test_normalize_sslmode_require():
    url, connect_args = normalize_database_url(
        "postgres://u:p@h:5432/db?sslmode=require"
    )

    assert connect_args == {"ssl": True}
    assert "sslmode" not in urlsplit(url).query


def test_normalize_sslmode_disable_keeps_ssl_off():
    url, connect_args = normalize_database_url(
        "postgresql://u:p@h:5432/db?sslmode=disable"
    )

    assert connect_args == {}
    assert "sslmode" not in urlsplit(url).query
