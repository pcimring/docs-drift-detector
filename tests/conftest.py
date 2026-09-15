import os
from pathlib import Path

import psycopg
import pytest

from discovery.db import apply_schema

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "001_init.sql"


@pytest.fixture
def db_conn():
    dsn = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/docs_drift_test"
    )
    conn = psycopg.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    apply_schema(conn, SCHEMA_PATH)
    yield conn
    conn.close()
