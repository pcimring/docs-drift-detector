import json
from unittest.mock import MagicMock

import pytest

from checkapi import main as check_main

SUMMARY = {
    "snippets_checked": 2,
    "pass": 1,
    "fail": 1,
    "unresolved": 0,
    "timeout": 0,
    "inconclusive": 0,
}


def _run(monkeypatch, argv, summary):
    conn = MagicMock()
    check_page = MagicMock(return_value=summary)
    monkeypatch.setattr(check_main, "load_dotenv", lambda: None)
    monkeypatch.setattr(check_main, "get_connection", lambda: conn)
    monkeypatch.setattr(check_main, "check_page", check_page)
    monkeypatch.setattr("sys.argv", ["checkapi.main", *argv])
    return conn, check_page


def test_main_checks_the_page_and_prints_the_summary(monkeypatch, capsys):
    conn, check_page = _run(monkeypatch, ["langchain", "abc123"], SUMMARY)

    check_main.main()

    check_page.assert_called_once_with(conn, "langchain", "abc123")
    conn.close.assert_called_once()
    assert json.loads(capsys.readouterr().out) == SUMMARY


def test_main_exits_with_error_when_page_has_no_samples(monkeypatch, capsys):
    empty = {key: 0 for key in SUMMARY}
    _run(monkeypatch, ["langchain", "unknown"], empty)

    with pytest.raises(SystemExit) as exc:
        check_main.main()

    assert exc.value.code == 1
    assert "No samples found for page_group_id unknown" in capsys.readouterr().err


def test_main_prints_usage_with_wrong_argument_count(monkeypatch, capsys):
    _run(monkeypatch, ["langchain"], SUMMARY)

    with pytest.raises(SystemExit) as exc:
        check_main.main()

    assert exc.value.code == 1
    assert "Usage:" in capsys.readouterr().out
