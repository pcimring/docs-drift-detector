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
