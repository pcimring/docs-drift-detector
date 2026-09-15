import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from discovery.config import load_target

from checkapi import fix_drafter, flagged_locations, github_source, imports, run_writer
from checkapi.catalog_reader import get_page_group
from checkapi.sandbox import (
    ExecutionResult,
    HarnessError,
    execute_snippet,
    install_packages,
    is_transient_error,
)

SUMMARY_KEYS = ("pass", "fail", "unresolved", "timeout", "inconclusive")


def run_in_sandbox(code: str) -> ExecutionResult:
    packages = imports.resolve_packages(code)
    with TemporaryDirectory() as tmp_dir:
        install_packages(packages, Path(tmp_dir))
        return execute_snippet(code, extra_sys_path=Path(tmp_dir))


def check_snippet(snippet_text: str, page_text: str) -> tuple[str, str | None, str | None, list]:
    try:
        result = run_in_sandbox(snippet_text)
    except (HarnessError, subprocess.TimeoutExpired) as exc:
        # The harness itself failed (e.g. a guessed pip package name doesn't
        # exist), not the snippet under test. Retrying a deterministic
        # install failure won't help, so report inconclusive immediately.
        return "inconclusive", str(exc), None, []

    if result.status == "fail" and is_transient_error(result.error_text):
        try:
            result = run_in_sandbox(snippet_text)
        except (HarnessError, subprocess.TimeoutExpired) as exc:
            return "inconclusive", str(exc), None, []
        if result.status == "fail" and is_transient_error(result.error_text):
            return "inconclusive", result.error_text, None, []

    if result.status == "pass":
        return "pass", None, None, []
    if result.status == "timeout":
        return "timeout", result.error_text, None, []

    # Genuine, non-transient failure: attempt a verified fix, and flag other
    # same-page locations referencing the same broken identifier.
    fix_result = fix_drafter.draft_and_verify_fix(
        page_text, result.error_text, snippet_text, execute_fn=run_in_sandbox
    )
    identifier = flagged_locations.extract_broken_identifier(result.error_text)
    flagged = flagged_locations.find_flagged_locations(page_text, identifier, exclude_block=snippet_text)

    if fix_result.verified:
        return "fail", result.error_text, fix_result.diff, flagged
    return "unresolved", result.error_text, None, flagged


def check_page(conn, target_name: str, page_group_id: str) -> dict:
    target = load_target(target_name)
    rows = get_page_group(conn, page_group_id)
    summary = {"snippets_checked": 0, **{key: 0 for key in SUMMARY_KEYS}}
    if not rows:
        return summary

    page_text = github_source.fetch_page_text(target.docs_repo, rows[0].doc_page)

    for row in rows:
        status, error_text, drafted_fix_diff, flagged = check_snippet(row.snippet_text, page_text)
        run_writer.write_run_record(
            conn,
            target.name,
            page_group_id,
            row.snippet_id,
            status,
            error_text=error_text,
            drafted_fix_diff=drafted_fix_diff,
            flagged_locations=flagged,
        )
        summary["snippets_checked"] += 1
        summary[status] += 1
    return summary
