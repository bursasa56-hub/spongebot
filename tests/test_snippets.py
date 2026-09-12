from bot.services.snippets import build_snippet


def test_build_snippet_with_values():
    snippet = build_snippet(
        "https://api.example.com/", "secret-key", task_id=42
    )
    assert "/partner/confirm" in snippet
    assert "secret-key" in snippet
    assert "task_id" in snippet
    assert "curl" in snippet


def test_build_snippet_placeholders():
    snippet = build_snippet(None, None, sponsor_id=7)
    assert "<ВАШ_АДРЕС>" in snippet
    assert "<КЛЮЧ_ПАРТНЁРА>" in snippet
    assert "sponsor_id" in snippet
