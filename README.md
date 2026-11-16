# docs-drift-detector

When a codebase changes and its docs do not, drift occurs. This tool looks for docs drift and attempts to address it.

The tool goes through a docs repo, runs each **Python** code sample, and reports the ones that fail. It also drafts a fix for each failure and checks that the updated sample runs without an error.

Results and suggested fixes are saved to a database for human review.

> [!IMPORTANT]
> The tool does not check a sample's output. It only checks that the sample runs without an error.

> [!NOTE]
> Currently only Python code samples in `.mdx` pages are supported. See [Known gaps and limitations](#known-gaps-and-limitations).

## How it works

The tool runs in 2 stages:

1. Discovery finds the samples. It reads every page in a docs repo, extracts the self-contained Python samples, and saves them to the database. It does not run any code.
2. Check runs the samples. It takes one page from the database, runs each sample on it, has Claude draft a fix for each failure, and saves the results.

Discovery builds the list, and check works through it one page at a time.

### Targets

The docs repo that the tool checks is called the target. You [list the targets](#add-a-target) in `config/targets.yaml`, and you name the target each time you run the tool.

> [!NOTE]
> For convenience, `config/targets.yaml` is preconfigured to target the [LangChain docs repo](https://github.com/langchain-ai/docs). You can replace this default target or add more targets. Each docs repo must use `.mdx` files and contain Python code samples. See [Known gaps and limitations](#known-gaps-and-limitations).

### Discovery

You run discovery against a local clone of the target docs repo. You can run it from the command line, or schedule it to run as a GitHub Action.

Discovery scans each `.mdx` page and extracts the Python code samples. It keeps only self-contained samples: each must import at least one package and define every name it uses. It saves these samples to the `catalog_entry` table in the database, and removes samples saved on earlier runs that are no longer in the docs.

### Check

You run check from the command line. It works through the samples that discovery saved to the `catalog_entry` table, one docs page at a time.

Check fetches the current version of the page from GitHub and runs each sample on it. When a sample fails, check sends the sample, the error and the page to Claude, which drafts a fix. Check runs the fix and keeps it only if it runs without an error. It also flags other places on the page that use the same broken name.

Each sample ends with one status:

| Status | Meaning |
| --- | --- |
| `pass` | The sample runs without an error. |
| `fail` | The sample fails, and Claude drafted a fix that runs without an error. |
| `unresolved` | The sample fails, and no drafted fix runs without an error. |
| `timeout` | The sample did not finish in time. |
| `inconclusive` | The check could not run. For example, a package failed to install, the page could not be fetched, or a temporary error, such as a network error, happened twice in a row. |

Check saves each result to the `run` table in the database. See [Review the results](#review-the-results).

To run discovery and check, see [Run it locally](#run-it-locally).

## Requirements for a docs repo

A target can be any docs repo on GitHub that meets the following requirements:

- Pages are `.mdx` files. Discovery does not read `.md` or `.rst` files.
- Code samples are written in Python.
- Each package installs under the name it is imported as. For example, `import langchain_openai` installs `langchain-openai`. The exceptions are listed in `checkapi/imports.py`. A package that installs under a different name, such as `sklearn` (`scikit-learn`), fails to install, and its samples end as `inconclusive`.
- Samples call only OpenAI or Anthropic. Samples receive only the `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` environment variables, so a sample that needs another service's key fails.

## Known gaps and limitations

- Only Python code samples in `.mdx` pages are supported. Discovery does not read `.md` or `.rst` files. It also drops samples in other languages. See also [Requirements for a docs repo](#requirements-for-a-docs-repo).
- Samples are not isolated. Check runs them on your machine in a separate Python process, not in a container.
- A sample passes if it runs without an error. The tool does not check the sample's output, so a fix can pass and still be wrong.
- The tool runs locally only. A future version will include support for deploying to Vercel.
- There is no web frontend yet. Results and drafted fixes are stored only in the database. See [Review the results](#review-the-results).
- The tool does not apply fixes or open pull requests. You review each drafted fix and apply it yourself.

## Prerequisites

- Docker, to run the Postgres database
- Python 3.10 or later
- Git, to clone the target's docs repo
- An Anthropic API key, to draft fixes
- An OpenAI API key, to run LangChain samples that call OpenAI
- A GitHub token (optional), to raise the GitHub API rate limit

## Run it locally

> [!NOTE]
> This version runs locally only. A future version will include support for deploying to Vercel.

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
| `rate_limit_event` | Requests to the hosted check endpoint, used for rate limiting. |

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

## Add a target

Add an entry to `config/targets.yaml` with the docs repo, the code repo and the language. Check first that the docs repo meets the [requirements](#requirements-for-a-docs-repo).

## Contact

To report a bug or suggest a feature, [open an issue](https://github.com/pcimring/docs-drift-detector/issues). For anything else, contact me on [LinkedIn](https://www.linkedin.com/in/peter-cimring).
