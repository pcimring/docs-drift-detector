import json
from io import BytesIO

import api.check as check_module


def make_handler(path):
    """Build a `handler` instance without running BaseHTTPRequestHandler's
    normal __init__ (which parses and dispatches a request immediately off
    a real socket). We only need to exercise do_POST's own logic."""
    instance = check_module.handler.__new__(check_module.handler)
    instance.path = path
    instance.headers = {}
    instance.client_address = ("9.9.9.9", 54321)
    instance.rfile = BytesIO()
    instance.wfile = BytesIO()
    instance._status = None

    def send_response(code):
        instance._status = code

    def send_header(name, value):
        pass

    def end_headers():
        pass

    instance.send_response = send_response
    instance.send_header = send_header
    instance.end_headers = end_headers
    return instance


def test_do_post_returns_500_json_when_get_connection_raises(monkeypatch):
    monkeypatch.setattr(
        check_module,
        "get_connection",
        lambda: (_ for _ in ()).throw(RuntimeError("db unreachable")),
    )

    instance = make_handler("/api/check?page_group_id=gid-1&target=langchain")
    instance.do_POST()

    assert instance._status == 500
    assert json.loads(instance.wfile.getvalue()) == {"error": "internal_error"}


def test_do_post_returns_500_json_when_build_response_raises(monkeypatch):
    closed = []

    class FakeConn:
        def close(self):
            closed.append(True)

    monkeypatch.setattr(check_module, "get_connection", lambda: FakeConn())

    def raise_error(conn, target_name, page_group_id, client_ip):
        raise RuntimeError("unknown target")

    monkeypatch.setattr(check_module, "build_response", raise_error)

    instance = make_handler("/api/check?page_group_id=gid-1&target=bogus-target")
    instance.do_POST()

    assert instance._status == 500
    assert json.loads(instance.wfile.getvalue()) == {"error": "internal_error"}
    assert closed == [True]
