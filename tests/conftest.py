import os
from pathlib import Path

import psycopg
import pytest

from discovery.db import apply_schema

SCHEMA_DIR = Path(__file__).parent.parent / "schema"


@pytest.fixture
def db_conn():
    dsn = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/docs_drift_test"
    )
    conn = psycopg.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    for schema_path in sorted(SCHEMA_DIR.glob("*.sql")):
        apply_schema(conn, schema_path)
    yield conn
    conn.close()
