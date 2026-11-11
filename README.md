# docs-drift-detector

When a codebase changes and its docs do not, drift occurs. This tool looks for
docs drift and attempts to address it.

The tool goes through a docs repo, runs each code sample, and reports the ones
that fail. It also drafts a fix for each failure and checks that the updated
sample runs without an error.

Results and suggested fixes are saved to a database for human review.

> [!CAUTION]
> The tool does not check the output of a given code snippet. It only checks that it runs without errors.

> [!CAUTION]
> This project is a work in progress. See [Known gaps](#known-gaps).

## How it works

The tool checks one docs repo at a time. You list the
target repos in `config/targets.yaml` (see [Add a target](#add-a-target)), and you
name the target to check each time you run the tool.

> [!NOTE]
> `config/targets.yaml` comes with one target preconfigured, `langchain`, for
> the [LangChain docs repo](https://github.com/langchain-ai/docs).

The tool runs in 2 stages.

### 1. Discovery

A GitHub Actions job runs daily. It scans each `.mdx` page in the target's docs
repo and extracts the Python code samples. It keeps only self-contained
samples: each must import at least one package and define every name it uses.
The job saves these samples to the `catalog_entry` table. It also removes
samples saved on earlier runs that are no longer in the docs.

### 2. Check

The `/api/check` endpoint checks one docs page per request. You pass it the
page's `page_group_id` from the `catalog_entry` table (see
[Check a page](#check-a-page)). The endpoint fetches the current page text from
GitHub. Then, for each sample on the page, it:

1. Installs the packages the sample imports into a temporary directory.
2. Runs the sample in a separate Python process.
3. If the error looks temporary, such as a network error or a rate limit, runs
   the sample once more.
4. If the error is not temporary, sends the page text, the sample and the error
   to Claude, which drafts a corrected sample.
5. Runs the corrected sample, and keeps the fix only if it runs without an
   error.
6. If the error names a missing module, attribute or variable, flags other
   places on the same page that use that name.

Each sample ends with one status:

| Status | Meaning |
| --- | --- |
| `pass` | The sample runs without an error. |
| `fail` | The sample fails, and Claude drafted a fix that runs without an error. |
| `unresolved` | The sample fails, and no drafted fix runs without an error. |
| `timeout` | The sample did not finish in time. |
| `inconclusive` | The check could not run. For example, a package failed to install, the page could not be fetched, or the temporary error happened again. |

The endpoint saves each result to the `run` table, with the error text, the
flagged places (`flagged_locations`) and, for `fail`, the diff of the fix
(`drafted_fix_diff`). To review the fixes:

    SELECT snippet_id, error_text, drafted_fix_diff FROM run WHERE status = 'fail';

## Known gaps

- The tool does not apply fixes or open pull requests. Fixes are stored only
  in the `run` table, and there is no review screen yet.
- A sample passes if it runs without an error. The tool does not check the
  sample's output, so a fix can pass and still be wrong.
- LangChain is the only target. The daily discovery job checks out only the
  LangChain docs repo.
- The check endpoint uses `langchain` if you leave out `target`, and it does
  not check that the page belongs to the target you pass.
- There is no web frontend yet.

## Prerequisites

- Docker, to run the Postgres database
- Python 3
- Git, to clone the target's docs repo
- An Anthropic API key, to draft fixes
- An OpenAI API key, to run LangChain samples that call OpenAI
- A GitHub token (optional), to raise the GitHub API rate limit

## Run it locally

    docker compose up -d
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    pytest

`docker compose up -d` starts Postgres and creates the tables from `schema/`.

In `.env`, set the keys you need:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Drafts the fixes. |
| `OPENAI_API_KEY` | Runs LangChain samples that call OpenAI directly. |
| `GITHUB_TOKEN` | Optional. Raises the GitHub API rate limit for fetching docs pages. |

### Build the catalog

Clone the target's docs repo, then point discovery at it:

    git clone https://github.com/langchain-ai/docs /path/to/langchain-docs
    python -m discovery.main langchain /path/to/langchain-docs

The command exits with an error if the path is not a directory or if it finds
no pages.

### Check a page

Each docs page has a `page_group_id` in the catalog:

    SELECT DISTINCT doc_page, page_group_id FROM catalog_entry;

Send that ID to the endpoint:

    POST /api/check?page_group_id=<id>&target=<target>

Pass the same target you used for discovery.

The response summarizes the page:

    {"snippets_checked": 4, "pass": 3, "fail": 1, "unresolved": 0, "timeout": 0, "inconclusive": 0}

The endpoint allows 10 requests per hour per client IP
(`RATE_LIMIT_MAX_PER_HOUR`).

## Deploy to Vercel

1. Set the variables from `.env.example` in the Vercel project, with
   `DATABASE_URL` pointing at a hosted Postgres database.
2. Apply the files in `schema/` to that database, in order:

       psql "$DATABASE_URL" -f schema/001_init.sql
       psql "$DATABASE_URL" -f schema/002_rate_limit.sql

3. Run discovery once against the same database, so the endpoint has samples
   to check.

Vercel installs dependencies from `pyproject.toml`, and local runs use
`requirements.txt`. Keep the two lists in sync when you add a package.

## Add a target

Add an entry to `config/targets.yaml` with the docs repo, the code repo and the
language.

## Contact

To report a bug or suggest a feature, [open an issue](https://github.com/pcimring/docs-drift-detector/issues). For anything else, contact me on [LinkedIn](https://www.linkedin.com/in/peter-cimring).
