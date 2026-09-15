from discovery.db import get_connection


def test_schema_creates_expected_tables(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
    assert tables == ["catalog_entry", "run"]


def test_get_connection_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/docs_drift_test")
    conn = get_connection()
    assert conn.closed == 0
    conn.close()
