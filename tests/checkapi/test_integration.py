from discovery.catalog import upsert_catalog_entries, make_snippet_id

from checkapi import orchestrator
from checkapi.fix_drafter import FixResult

PAGE_TEXT = (
    "Step one, set up the client:\n"
    "old_call(x)\n\n"
    "Full example:\n"
    "print('works')\n\n"
    "Another full example:\n"
    "old_call(x)\n"
)


class FakeTarget:
    name = "langchain"
    docs_repo = "langchain-ai/docs"


def test_check_page_end_to_end_pass_and_verified_fix(monkeypatch, db_conn):
    page_group_id = upsert_catalog_entries(
        db_conn, "langchain", "docs/quickstart.mdx", ["print('works')", "old_call(x)"]
    )

    monkeypatch.setattr(orchestrator, "load_target", lambda name: FakeTarget())
    monkeypatch.setattr(orchestrator.github_source, "fetch_page_text", lambda repo, path: PAGE_TEXT)

    def fake_run_in_sandbox(code, install_cache=None):
        from checkapi.sandbox import ExecutionResult

        if code == "print('works')":
            return ExecutionResult("pass", "works\n", "", None)
        if code == "old_call(x)":
            return ExecutionResult("fail", "", "", "AttributeError: module 'x' has no attribute 'old_call'")
        return ExecutionResult("pass", "", "", None)  # the drafted-fix re-verify call

    monkeypatch.setattr(orchestrator, "run_in_sandbox", fake_run_in_sandbox)
    monkeypatch.setattr(
        orchestrator.fix_drafter,
        "draft_and_verify_fix",
        lambda doc_text, error_text, source_code, execute_fn, llm_client=None: FixResult(
            verified=True, diff="--- original\n+++ fixed\n"
        ),
    )

    summary = orchestrator.check_page(db_conn, "langchain", page_group_id)

    assert summary["snippets_checked"] == 2
    assert summary["pass"] == 1
    assert summary["fail"] == 1

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT snippet_id, status, drafted_fix_diff, flagged_locations FROM run "
            "WHERE page_group_id = %s ORDER BY snippet_id",
            (page_group_id,),
        )
        rows = cur.fetchall()

    by_snippet = {row[0]: row for row in rows}

    expected_fail_id = make_snippet_id("docs/quickstart.mdx", "old_call(x)")
    expected_pass_id = make_snippet_id("docs/quickstart.mdx", "print('works')")

    fail_row = by_snippet[expected_fail_id]
    assert fail_row[1] == "fail"
    assert fail_row[2] == "--- original\n+++ fixed\n"
    assert fail_row[3] == [{"line": 2, "text": "old_call(x)"}]

    pass_row = by_snippet[expected_pass_id]
    assert pass_row[1] == "pass"
    assert pass_row[2] is None
    assert pass_row[3] == []
