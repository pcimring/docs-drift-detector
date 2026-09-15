# docs-drift-detector

Portfolio demonstration of docs-drift detection, code-sample testing, and
AI-assisted update drafting — built config-driven against LangChain first,
Arize Phoenix second. See the design spec for full context.

## Local dev

    docker compose up -d
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    pytest

`docker compose up -d` mounts `schema/` into the container's
`/docker-entrypoint-initdb.d`, and the postgres image runs every `.sql` file
found there the first time a database volume is created. The schema is
therefore applied for you; there is no separate migrate step. After editing
`schema/001_init.sql`, recreate the volume to pick the change up:

    docker compose down -v && docker compose up -d

## Run discovery manually

Discovery reads its connection string from `DATABASE_URL`. The `cp .env.example
.env` step above is enough, because the CLI loads `.env` at startup. To set it
explicitly instead:

    export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docs_drift_test

Then point the job at a local checkout of the target's docs repo:

    python -m discovery.main langchain /path/to/local/langchain-ai-docs-checkout

The command exits non-zero if the path is not a directory, or if it scans zero
pages, so a broken checkout fails instead of reporting an empty run as success.

## Adding a new target

`config/targets.yaml` holds one entry per target. The `target` input on
`.github/workflows/discovery.yml` only selects which entry is *read*. The
docs repo that workflow *checks out* is still hardcoded to
`langchain-ai/docs`. Update that checkout step alongside any new
`targets.yaml` entry, or the new target will be cataloged from LangChain's
docs under the wrong `target_project`.
