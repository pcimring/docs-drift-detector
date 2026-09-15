import re

_PATTERNS = [
    r"NameError: name '(\w+)' is not defined",
    r"has no attribute '(\w+)'",
    r"No module named '([\w.]+)'",
]


def extract_broken_identifier(error_text: str | None) -> str | None:
    if not error_text:
        return None
    for pattern in _PATTERNS:
        match = re.search(pattern, error_text)
        if match:
            return match.group(1)
    return None


def find_flagged_locations(page_text: str, identifier: str | None, exclude_block: str) -> list[dict]:
    if not identifier:
        return []

    # Try position-based exclusion first
    exclude_block_stripped = exclude_block.strip()
    exclude_line_range = None

    # Find where the exclude_block appears in page_text. The exclude_block parameter carries
    # no position info, so when its text appears more than once on the page, which occurrence
    # was actually executed is ambiguous. rfind (last occurrence) is used by convention — this
    # is a tiebreak, not a guarantee of correctness. Callers with position info should pass
    # it via wider exclude_block context if disambiguation matters.
    if exclude_block_stripped:
        match_index = page_text.rfind(exclude_block_stripped)
        if match_index != -1:
            # Count lines before the match
            lines_before = page_text[:match_index].count('\n')
            exclude_start_line = lines_before + 1
            # Count how many lines in exclude_block
            lines_in_block = exclude_block_stripped.count('\n')
            exclude_end_line = exclude_start_line + lines_in_block
            exclude_line_range = (exclude_start_line, exclude_end_line)

    # Fall back to content-based if position-based failed
    excluded_lines = None
    if exclude_line_range is None and exclude_block_stripped:
        excluded_lines = {line.strip() for line in exclude_block_stripped.splitlines()}

    pattern = re.compile(rf"\b{re.escape(identifier)}\b")
    flagged = []

    for line_no, line in enumerate(page_text.splitlines(), start=1):
        stripped = line.strip()

        # Skip if in excluded line range (position-based)
        if exclude_line_range is not None:
            if exclude_line_range[0] <= line_no <= exclude_line_range[1]:
                continue
        # Fall back to content-based
        elif excluded_lines is not None and stripped in excluded_lines:
            continue

        if pattern.search(line):
            flagged.append({"line": line_no, "text": stripped})

    return flagged
