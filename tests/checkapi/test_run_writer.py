from checkapi.run_writer import write_run_record


def test_write_run_record_persists_all_fields(db_conn):
    write_run_record(
        db_conn,
        "langchain",
        "gid-1",
        "docs/quickstart.mdx#0",
        "fail",
        error_text="ValueError: boom",
        drafted_fix_diff="--- original\n+++ fixed\n",
        flagged_locations=[{"line": 3, "text": "old_call(x)"}],
    )

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT target_project, page_group_id, snippet_id, status, error_text, "
            "drafted_fix_diff, flagged_locations FROM run"
        )
        row = cur.fetchone()

    assert row[0] == "langchain"
    assert row[1] == "gid-1"
    assert row[2] == "docs/quickstart.mdx#0"
    assert row[3] == "fail"
    assert row[4] == "ValueError: boom"
    assert row[5] == "--- original\n+++ fixed\n"
    assert row[6] == [{"line": 3, "text": "old_call(x)"}]


def test_write_run_record_defaults_flagged_locations_to_empty_list(db_conn):
    write_run_record(db_conn, "langchain", "gid-1", "docs/quickstart.mdx#0", "pass")

    with db_conn.cursor() as cur:
        cur.execute("SELECT flagged_locations FROM run")
        row = cur.fetchone()

    assert row[0] == []
