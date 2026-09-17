import os

import psycopg


def get_connection() -> psycopg.Connection:
    dsn = os.environ["DATABASE_URL"]
    return psycopg.connect(dsn)


def apply_schema(conn: psycopg.Connection, schema_path) -> None:
    # psycopg3 only allows multiple statements in one execute() call when
    # the query has no parameters, schema DDL has none, so this is safe.
    # Do not add %s placeholders to a multi-statement call built this way.
    with open(schema_path, "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
