# docs-drift-detector

When a codebase changes and its docs do not, drift occurs. This tool looks for docs drift and attempts to address it.

The tool goes through a docs repo, runs each code sample, and reports the ones that fail. It also drafts a fix for each failure and checks that the updated sample runs without an error.

Results and suggested fixes are saved to a database for human review.

> [!IMPORTANT]
> The tool does not check a sample's output. It only checks that the sample runs without an error.

> [!NOTE]
> This project is a work in progress. See [Known gaps](#known-gaps).

## How it works

The tool runs in 2 stages:

1. Discovery finds the samples. It reads every page in a docs repo, extracts the self-contained Python samples, and saves them to the database. It does not run any code.
2. Check runs the samples. It takes one page from the database, runs each sample on it, has Claude draft a fix for each failure, and saves the results.

Discovery builds the list, and check works through it one page at a time.

### Targets

The docs repo that the tool checks is called the target. You list the targets in `config/targets.yaml` (see [Add a target](#add-a-target)), and you name the target each time you run the tool.

> [!NOTE]
> `config/targets.yaml` comes with one target preconfigured, `langchain`, for the [LangChain docs repo](https://github.com/langchain-ai/docs).

### Discovery

Discovery scans each `.mdx` page in the target's docs repo and extracts the Python code samples. It keeps only self-contained samples: each must import at least one package and define every name it uses. It saves these samples to the `catalog_entry` table, and removes samples saved on earlier runs that are no longer in the docs.

### Check

Check works on one page at a time, identified by the page's `page_group_id` from the `catalog_entry` table. It fetches the current page text from GitHub. Then, for each sample on the page, it:

1. Installs the packages the sample imports into a temporary directory.
2. Runs the sample in a separate Python process.
3. If the error looks temporary, such as a network error or a rate limit, runs the sample once more.
4. If the error is not temporary, sends the page text, the sample and the error to Claude, which drafts a corrected sample.
5. Runs the corrected sample, and keeps the fix only if it runs without an error.
6. If the error names a missing module, attribute or variable, flags other places on the same page that use that name.

Each sample ends with one status:

| Status | Meaning |
| --- | --- |
| `pass` | The sample runs without an error. |
| `fail` | The sample fails, and Claude drafted a fix that runs without an error. |
| `unresolved` | The sample fails, and no drafted fix runs without an error. |
| `timeout` | The sample did not finish in time. |
| `inconclusive` | The check could not run. For example, a package failed to install, the page could not be fetched, or the temporary error happened again. |

Check saves each result to the `run` table. See [Review the results](#review-the-results).

## Requirements for a docs repo

The tool is designed to work with any docs repo on GitHub. Today, a target must meet these requirements:

- Pages are `.mdx` files. Discovery does not read `.md` or `.rst` files.
- Code samples are written in Python.
- Each package installs under the name it is imported as. For example, `import langchain_openai` installs `langchain-openai`. The exceptions are listed in `checkapi/imports.py`. A package that installs under a different name, such as `sklearn` (`scikit-learn`), fails to install, and its samples end as `inconclusive`.
- Samples call only OpenAI or Anthropic. Samples receive only the `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` environment variables, so a sample that needs another service's key fails.

## Known gaps

- The tool does not apply fixes or open pull requests. Fixes are stored only in the `run` table, and there is no review screen yet.
- A sample passes if it runs without an error. The tool does not check the sample's output, so a fix can pass and still be wrong.
- LangChain is the only target so far. The scheduled discovery job checks out only the LangChain docs repo.
- The check endpoint uses `langchain` if you leave out `target`, and it does not check that the page belongs to the target you pass.
- The tests use the same database as local runs, and they delete its data. See [Run the tests](#run-the-tests).
- There is no web frontend yet.

## Prerequisites

- Docker, to run the Postgres database
- Python 3.10 or later
- Git, to clone the target's docs repo
- An Anthropic API key, to draft fixes
- An OpenAI API key, to run LangChain samples that call OpenAI
- A GitHub token (optional), to raise the GitHub API rate limit

## Run it locally

> [!WARNING]
> Check runs code from the target's docs on your machine. Each sample runs in a separate Python process, not in a container. Run the tool only against docs repos you trust.

1. Clone this repo and start the database:

   ```bash
   git clone https://github.com/pcimring/docs-drift-detector
   cd docs-drift-detector
   docker compose up -d
   ```

   Docker starts a Postgres container and creates the tables from the files in `schema/`.

2. Install the dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Create your `.env` file:

   ```bash
   cp .env.example .env
   ```

   `DATABASE_URL` already points at the local database. Set the keys:

   | Variable | Purpose |
   | --- | --- |
   | `ANTHROPIC_API_KEY` | Drafts the fixes. |
   | `OPENAI_API_KEY` | Runs LangChain samples that call OpenAI directly. |
   | `GITHUB_TOKEN` | Optional. Raises the GitHub API rate limit for fetching docs pages. |

4. Clone the target's docs repo, and run discovery on it:

   ```bash
   git clone https://github.com/langchain-ai/docs ../langchain-docs
   python -m discovery.main langchain ../langchain-docs
   ```

   When it finishes, discovery prints a summary:

   ```
   Scanned <pages> pages (<skipped> skipped), found <samples> runnable candidates.
   ```

   If the path is not a directory, or discovery finds no pages, the command exits with an error.

5. Pick a page to check. List some pages and their IDs:

   ```bash
   docker compose exec postgres psql -U postgres -d docs_drift_test -c "SELECT DISTINCT doc_page, page_group_id FROM catalog_entry LIMIT 10;"
   ```

6. Check the page, using its `page_group_id`:

   ```bash
   python -m checkapi.main langchain <page_group_id>
   ```

   When it finishes, check prints a summary of the page:

   ```json
   {"snippets_checked": 4, "pass": 3, "fail": 1, "unresolved": 0, "timeout": 0, "inconclusive": 0}
   ```

   If the page has no samples in the catalog, the command exits with an error.

## Review the results

Until there is a web frontend, the results are in the database. The tool uses 3 tables:

| Table | Contents |
| --- | --- |
| `catalog_entry` | One row per sample that discovery found, with its page (`doc_page`) and `page_group_id`. |
| `run` | One row per checked sample, with its status, the error text, the flagged places (`flagged_locations`) and, for `fail`, the diff of the fix (`drafted_fix_diff`). |
| `rate_limit_event` | Requests to the check endpoint, used for rate limiting. |

To open a SQL prompt:

```bash
docker compose exec postgres psql -U postgres -d docs_drift_test
```

You can also connect any Postgres client to `postgresql://postgres:postgres@localhost:5432/docs_drift_test`.

To count the results by status:

```sql
SELECT status, count(*) FROM run GROUP BY status;
```

To review the drafted fixes:

```sql
SELECT snippet_id, error_text, drafted_fix_diff FROM run WHERE status = 'fail';
```

## Run the tests

> [!CAUTION]
> The tests use the local database and delete all its data before each test, including the catalog and the results.

```bash
pytest
```

## Deploy to Vercel

The repo deploys to Vercel as an API endpoint that runs check. To deploy it:

1. Set the variables from `.env.example` in the Vercel project, with `DATABASE_URL` pointing at a hosted Postgres database.
2. Apply the files in `schema/` to that database, in order:

   ```bash
   psql "$DATABASE_URL" -f schema/001_init.sql
   psql "$DATABASE_URL" -f schema/002_rate_limit.sql
   ```

3. Run discovery once against the same database, so the endpoint has samples to check.

The endpoint takes the same input as the local command:

```
POST /api/check?page_group_id=<page_group_id>&target=langchain
```

It returns the same summary, and allows 10 requests per hour per client IP (`RATE_LIMIT_MAX_PER_HOUR`).

Vercel installs dependencies from `pyproject.toml`, and local runs use `requirements.txt`. Keep the two lists in sync when you add a package.

### Run discovery on a schedule

The workflow in `.github/workflows/discovery.yml` runs discovery every day, and you can also start it by hand from the repo's Actions tab. It needs a repository secret, `DATABASE_URL`, pointing at the hosted database.

## Add a target

Add an entry to `config/targets.yaml` with the docs repo, the code repo and the language. Check first that the docs repo meets the [requirements](#requirements-for-a-docs-repo).

## Contact

To report a bug or suggest a feature, [open an issue](https://github.com/pcimring/docs-drift-detector/issues). For anything else, contact me on [LinkedIn](https://www.linkedin.com/in/peter-cimring).
