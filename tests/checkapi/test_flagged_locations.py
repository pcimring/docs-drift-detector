from checkapi.flagged_locations import extract_broken_identifier, find_flagged_locations


def test_extract_identifier_from_name_error():
    assert extract_broken_identifier("NameError: name 'old_helper' is not defined") == "old_helper"


def test_extract_identifier_from_attribute_error():
    err = "AttributeError: module 'langchain_core' has no attribute 'old_call'"
    assert extract_broken_identifier(err) == "old_call"


def test_extract_identifier_from_module_not_found():
    assert extract_broken_identifier("ModuleNotFoundError: No module named 'old_pkg'") == "old_pkg"


def test_extract_identifier_returns_none_for_unrecognized_error():
    assert extract_broken_identifier("RuntimeError: something else broke") is None


def test_find_flagged_locations_skips_the_already_checked_block():
    page_text = (
        "Step one:\n"
        "old_call(x)\n"
        "\n"
        "Full example:\n"
        "old_call(y)\n"
    )
    exclude_block = "old_call(y)\n"

    flagged = find_flagged_locations(page_text, "old_call", exclude_block)

    assert flagged == [{"line": 2, "text": "old_call(x)"}]


def test_find_flagged_locations_returns_empty_without_identifier():
    assert find_flagged_locations("old_call(x)\n", None, "") == []


def test_find_flagged_locations_excludes_only_the_specific_block_position():
    """
    When the same line text appears in multiple places,
    position-based exclusion ensures we exclude only the specific checked block,
    not other occurrences of the same text elsewhere on the page.
    This prevents silently dropping unverified duplicates.
    """
    page_text = (
        "# First example:\n"
        "old_call(x)\n"
        "\n"
        "# Full example to verify:\n"
        "old_call(x)\n"
        "print(result)\n"
    )
    # Only the second "old_call(x)" (with surrounding context) was catalogued and executed
    exclude_block = "old_call(x)\nprint(result)\n"

    flagged = find_flagged_locations(page_text, "old_call", exclude_block)

    # Should return only line 2 (the first unchecked occurrence),
    # not silently drop it because identical text exists in the exclude_block
    assert flagged == [{"line": 2, "text": "old_call(x)"}]


def test_find_flagged_locations_uses_rfind_tiebreak_when_exclude_block_is_ambiguous():
    """
    When exclude_block appears multiple times verbatim on the page,
    rfind (last occurrence) is used by convention as a tiebreak.
    This pins the behavior: the LAST occurrence is excluded, other occurrences are flagged.
    """
    page_text = (
        "Step one:\n"
        "old_call(x)\n"
        "\n"
        "Full example:\n"
        "print('works')\n"
        "\n"
        "Another full example:\n"
        "old_call(x)\n"
    )
    # exclude_block appears twice verbatim (lines 2 and 8) with no disambiguating context
    exclude_block = "old_call(x)"

    flagged = find_flagged_locations(page_text, "old_call", exclude_block)

    # rfind chooses the LAST occurrence (line 8), so line 2 should be flagged
    assert flagged == [{"line": 2, "text": "old_call(x)"}]
