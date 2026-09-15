CREATE TABLE catalog_entry (
    id SERIAL PRIMARY KEY,
    target_project TEXT NOT NULL,
    doc_page TEXT NOT NULL,
    snippet_id TEXT NOT NULL,
    snippet_text TEXT NOT NULL,
    page_group_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (target_project, doc_page, snippet_id)
);

CREATE TYPE run_status AS ENUM ('pass', 'fail', 'unresolved', 'timeout', 'inconclusive');

CREATE TABLE run (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT now(),
    target_project TEXT NOT NULL,
    page_group_id TEXT NOT NULL,
    snippet_id TEXT NOT NULL,
    status run_status NOT NULL,
    error_text TEXT,
    drafted_fix_diff TEXT,
    flagged_locations JSONB NOT NULL DEFAULT '[]'
);
