import pytest

from checkapi.github_source import fetch_page_text


class FakeResponse:
    def __init__(self, text, status_ok=True):
        self.text = text
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("404 Not Found")


def test_fetch_page_text_builds_correct_request(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse("# Quickstart\n\nSome content.\n")

    monkeypatch.setattr("checkapi.github_source.requests.get", fake_get)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    text = fetch_page_text("langchain-ai/docs", "docs/quickstart.mdx")

    assert text == "# Quickstart\n\nSome content.\n"
    assert captured["url"] == "https://api.github.com/repos/langchain-ai/docs/contents/docs/quickstart.mdx"
    assert captured["headers"]["Accept"] == "application/vnd.github.raw+json"
    assert "Authorization" not in captured["headers"]


def test_fetch_page_text_adds_auth_header_when_token_set(monkeypatch):
    monkeypatch.setattr(
        "checkapi.github_source.requests.get", lambda url, headers=None, timeout=None: FakeResponse("x")
    )
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")

    fetch_page_text("langchain-ai/docs", "docs/quickstart.mdx")


def test_fetch_page_text_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(
        "checkapi.github_source.requests.get",
        lambda url, headers=None, timeout=None: FakeResponse("", status_ok=False),
    )
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with pytest.raises(RuntimeError):
        fetch_page_text("langchain-ai/docs", "docs/missing.mdx")
