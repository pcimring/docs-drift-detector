from checkapi import handler_logic


def test_build_response_rejects_rate_limited_ip(monkeypatch):
    monkeypatch.setattr(handler_logic.rate_limit, "is_rate_limited", lambda conn, ip: True)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not check the page when rate-limited")

    monkeypatch.setattr(handler_logic.orchestrator, "check_page", fail_if_called)

    status_code, body = handler_logic.build_response(conn=None, target_name="langchain", page_group_id="gid-1", client_ip="1.2.3.4")

    assert status_code == 429
    assert body == {"error": "rate_limited"}


def test_build_response_returns_check_page_summary(monkeypatch):
    recorded = []
    monkeypatch.setattr(handler_logic.rate_limit, "is_rate_limited", lambda conn, ip: False)
    monkeypatch.setattr(handler_logic.rate_limit, "record_request", lambda conn, ip: recorded.append(ip))
    monkeypatch.setattr(
        handler_logic.orchestrator,
        "check_page",
        lambda conn, target_name, page_group_id: {"snippets_checked": 1, "pass": 1},
    )

    status_code, body = handler_logic.build_response(conn=None, target_name="langchain", page_group_id="gid-1", client_ip="1.2.3.4")

    assert status_code == 200
    assert body == {"snippets_checked": 1, "pass": 1}
    assert recorded == ["1.2.3.4"]
