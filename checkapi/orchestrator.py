import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

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


def run_in_sandbox(code: str, install_cache: dict | None = None) -> ExecutionResult:
    """Execute `code` with its imports installed into a throwaway target dir.

    When `install_cache` is given (a dict keyed by the resolved package set, as
    built by `check_page`), an already-installed directory for the same package
    set is reused instead of running pip again. The caller owns the cache and is
    responsible for deleting the directories it holds.
    """
    packages = imports.resolve_packages(code)

    if install_cache is None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            install_packages(packages, Path(tmp_dir))
            return execute_snippet(code, extra_sys_path=Path(tmp_dir))

    key = frozenset(packages)
    cached_dir = install_cache.get(key)
    if cached_dir is None:
        cached_dir = Path(tempfile.mkdtemp())
        try:
            install_packages(packages, cached_dir)
        except BaseException:
            shutil.rmtree(cached_dir, ignore_errors=True)
            raise
        install_cache[key] = cached_dir
    return execute_snippet(code, extra_sys_path=cached_dir)


def check_snippet(
    snippet_text: str, page_text: str, install_cache: dict | None = None
) -> tuple[str, str | None, str | None, list]:
    def execute(code: str) -> ExecutionResult:
        # Every execution on this snippet's behalf — the first run, the
        # transient retry, and the fix re-verification — goes through here, so
        # they all share one installed-package directory per package set.
        if install_cache is None:
            return run_in_sandbox(code)
        return run_in_sandbox(code, install_cache)

    try:
        result = execute(snippet_text)
    except (HarnessError, subprocess.TimeoutExpired) as exc:
        # The harness itself failed (e.g. a guessed pip package name doesn't
        # exist), not the snippet under test. Retrying a deterministic
        # install failure won't help, so report inconclusive immediately.
        return "inconclusive", str(exc), None, []

    if result.status == "fail" and is_transient_error(result.error_text):
        try:
            result = execute(snippet_text)
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
        page_text, result.error_text, snippet_text, execute_fn=execute
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

    try:
        page_text = github_source.fetch_page_text(target.docs_repo, rows[0].doc_page)
    except requests.exceptions.RequestException as exc:
        # No page text means no snippet on this page can be checked. A GitHub
        # hiccup (rate limit, network blip, renamed page) is exactly the
        # "transient provider problem" the inconclusive status is for, so
        # record that per row rather than failing the whole request.
        for row in rows:
            run_writer.write_run_record(
                conn,
                target.name,
                page_group_id,
                row.snippet_id,
                "inconclusive",
                error_text=f"failed to fetch doc page: {exc}",
            )
            summary["snippets_checked"] += 1
            summary["inconclusive"] += 1
        return summary

    # One installed-package directory per distinct package set, shared by every
    # snippet on the page (and by fix re-verification) so a page whose snippets
    # share imports installs them once, not once per execution.
    install_cache: dict[frozenset, Path] = {}
    try:
        for row in rows:
            status, error_text, drafted_fix_diff, flagged = check_snippet(
                row.snippet_text, page_text, install_cache
            )
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
    finally:
        for cached_dir in install_cache.values():
            shutil.rmtree(cached_dir, ignore_errors=True)
    return summary
