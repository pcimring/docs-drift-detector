from discovery.catalog import upsert_catalog_entries

from checkapi import orchestrator
from checkapi.fix_drafter import FixResult
from checkapi.sandbox import ExecutionResult, HarnessError


def _stub_sandbox(monkeypatch, results):
    """results: list of ExecutionResult, consumed in call order."""
    calls = []

    def fake_run_in_sandbox(code):
        calls.append(code)
        return results.pop(0)

    monkeypatch.setattr(orchestrator, "run_in_sandbox", fake_run_in_sandbox)
    return calls


def test_check_snippet_pass(monkeypatch):
    _stub_sandbox(monkeypatch, [ExecutionResult("pass", "ok", "", None)])

    status, error_text, diff, flagged = orchestrator.check_snippet("print('ok')", "page text")

    assert (status, error_text, diff, flagged) == ("pass", None, None, [])


def test_check_snippet_transient_failure_retried_then_inconclusive(monkeypatch):
    transient = ExecutionResult("fail", "", "RateLimitError: slow down", "RateLimitError: slow down")
    _stub_sandbox(monkeypatch, [transient, transient])

    status, error_text, diff, flagged = orchestrator.check_snippet("print('x')", "page text")

    assert status == "inconclusive"
    assert diff is None
    assert flagged == []


def test_check_snippet_transient_retry_recovers_to_pass(monkeypatch):
    transient = ExecutionResult("fail", "", "RateLimitError: slow down", "RateLimitError: slow down")
    recovered = ExecutionResult("pass", "ok", "", None)
    _stub_sandbox(monkeypatch, [transient, recovered])

    status, error_text, diff, flagged = orchestrator.check_snippet("print('x')", "page text")

    assert status == "pass"


def test_check_snippet_timeout(monkeypatch):
    _stub_sandbox(monkeypatch, [ExecutionResult("timeout", "", "", "execution timed out")])

    status, error_text, diff, flagged = orchestrator.check_snippet("print('x')", "page text")

    assert status == "timeout"
    assert error_text == "execution timed out"


def test_check_snippet_genuine_failure_with_verified_fix(monkeypatch):
    fail_result = ExecutionResult("fail", "", "old_call(x)", "AttributeError: module has no attribute 'old_call'")
    _stub_sandbox(monkeypatch, [fail_result])
    monkeypatch.setattr(
        orchestrator.fix_drafter,
        "draft_and_verify_fix",
        lambda doc_text, error_text, source_code, execute_fn, llm_client=None: FixResult(
            verified=True, diff="--- original\n+++ fixed\n"
        ),
    )

    page_text = "Step: old_call(y)\n\nFull example:\nold_call(x)\n"
    status, error_text, diff, flagged = orchestrator.check_snippet("old_call(x)", page_text)

    assert status == "fail"
    assert diff == "--- original\n+++ fixed\n"
    assert flagged == [{"line": 1, "text": "Step: old_call(y)"}]


def test_check_snippet_genuine_failure_unresolved_when_fix_not_verified(monkeypatch):
    fail_result = ExecutionResult("fail", "", "", "AttributeError: module has no attribute 'old_call'")
    _stub_sandbox(monkeypatch, [fail_result])
    monkeypatch.setattr(
        orchestrator.fix_drafter,
        "draft_and_verify_fix",
        lambda doc_text, error_text, source_code, execute_fn, llm_client=None: FixResult(
            verified=False, diff=None
        ),
    )

    status, error_text, diff, flagged = orchestrator.check_snippet("old_call(x)", "old_call(x)\n")

    assert status == "unresolved"
    assert diff is None


def test_check_snippet_harness_error_reported_as_inconclusive(monkeypatch):
    def raise_harness_error(code):
        raise HarnessError("pip install failed: No matching distribution found for old_call")

    monkeypatch.setattr(orchestrator, "run_in_sandbox", raise_harness_error)

    status, error_text, diff, flagged = orchestrator.check_snippet("import old_call", "page text")

    assert status == "inconclusive"
    assert "pip install failed" in error_text
    assert diff is None
    assert flagged == []


def test_check_page_writes_a_run_record_per_snippet(monkeypatch, db_conn):
    page_group_id = upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('a')", "print('b')"]
    )

    class FakeTarget:
        name = "langchain"
        docs_repo = "langchain-ai/docs"

    monkeypatch.setattr(orchestrator, "load_target", lambda name: FakeTarget())
    monkeypatch.setattr(orchestrator.github_source, "fetch_page_text", lambda repo, path: "page text")
    monkeypatch.setattr(
        orchestrator,
        "check_snippet",
        lambda snippet_text, page_text: ("pass", None, None, []),
    )

    summary = orchestrator.check_page(db_conn, "langchain", page_group_id)

    assert summary == {
        "snippets_checked": 2,
        "pass": 2,
        "fail": 0,
        "unresolved": 0,
        "timeout": 0,
        "inconclusive": 0,
    }

    with db_conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run WHERE page_group_id = %s", (page_group_id,))
        assert cur.fetchone()[0] == 2


def test_check_page_returns_zero_summary_for_unknown_group(db_conn):
    summary = orchestrator.check_page(db_conn, "langchain", "nonexistent-group")

    assert summary == {
        "snippets_checked": 0,
        "pass": 0,
        "fail": 0,
        "unresolved": 0,
        "timeout": 0,
        "inconclusive": 0,
    }
