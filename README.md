# docs-drift-detector

Portfolio demonstration of docs-drift detection, code-sample testing, and
AI-assisted update drafting, built config-driven against LangChain first,
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
found there the first time a database volume is created. On a *fresh* volume the
schema is therefore applied for you and there is no separate migrate step. On an
already-provisioned database, see the next section. After editing
`schema/001_init.sql`, recreate the volume to pick the change up:

    docker compose down -v && docker compose up -d

## Applying a new schema migration to an existing database

`docker-entrypoint-initdb.d` only runs on a *fresh* database volume. If you
already have a running Postgres instance (a pre-existing local volume, or any
hosted database), apply new schema files manually:

    psql "$DATABASE_URL" -f schema/002_rate_limit.sql

Do this once per new schema file added after your database was first created.
Skipping it fails loudly: every `/api/check` request starts with a rate-limit
lookup against the table `schema/002_rate_limit.sql` creates, so the endpoint
returns 500 on every call until the file is applied.

## Deploying to Vercel

Vercel's Python builder (as of CLI 59.16.0, `uv`-based) does not auto-detect
`api/check.py`'s `handler` class the way earlier builders did. Two things
`pyproject.toml` must declare, or the build fails:

    [project]
    name = "docs-drift-detector"
    version = "0.1.0"
    dependencies = [ ... ]  # mirror requirements.txt

    [tool.vercel]
    entrypoint = "api.check:handler"

The `[tool.vercel]` entrypoint line alone isn't enough: `uv lock` also
requires a valid PEP 621 `[project]` table, or the build fails with
`No 'project' table found`. Once `pyproject.toml` exists, Vercel's build
installs dependencies from it, not from `requirements.txt`.
**The two files are separate manifests that must be kept in sync by hand.**
`requirements.txt` still drives local dev (`pip install -r requirements.txt`);
`pyproject.toml`'s `dependencies` list drives the Vercel build. Adding a new
package means updating both. `pytest` is deliberately excluded from
`pyproject.toml` since the deployed function doesn't need it.

Beyond that, a working deploy needs:
- The env vars in `.env.example` set in the Vercel project's Environment
  Variables settings (`DATABASE_URL` pointing at a real Postgres instance,
  plus `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GITHUB_TOKEN`; see that file's
  comments for what each is for)
- `schema/001_init.sql` and `schema/002_rate_limit.sql` applied to that
  Postgres instance manually (see "Applying a new schema migration" above;
  Vercel Postgres/Supabase don't run `docker-entrypoint-initdb.d`)
- The discovery job run at least once against that same database, so the
  catalog has rows for `/api/check` to check (see "Run discovery manually"
  below)

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
