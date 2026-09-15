from psycopg.types.json import Jsonb


def write_run_record(
    conn,
    target_project: str,
    page_group_id: str,
    snippet_id: str,
    status: str,
    error_text: str | None = None,
    drafted_fix_diff: str | None = None,
    flagged_locations: list | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO run
                (target_project, page_group_id, snippet_id, status, error_text,
                 drafted_fix_diff, flagged_locations)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                target_project,
                page_group_id,
                snippet_id,
                status,
                error_text,
                drafted_fix_diff,
                Jsonb(flagged_locations or []),
            ),
        )
    conn.commit()
