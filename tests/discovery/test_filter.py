from discovery.filter import is_runnable_candidate

SELF_CONTAINED = """
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
response = llm.invoke("Say hello in one word.")
print(response.content)
"""

FRAGMENT_NO_IMPORT = """
llm = ChatOpenAI(model="gpt-4o-mini")
"""

FRAGMENT_UNRESOLVED_NAME = """
import json

print(json.dumps(config))
"""

INVALID_SYNTAX = """
def broken(:
    pass
"""


def test_self_contained_snippet_is_candidate():
    assert is_runnable_candidate(SELF_CONTAINED) is True


def test_fragment_without_import_is_rejected():
    assert is_runnable_candidate(FRAGMENT_NO_IMPORT) is False


def test_fragment_with_unresolved_name_is_rejected():
    assert is_runnable_candidate(FRAGMENT_UNRESOLVED_NAME) is False


def test_invalid_syntax_is_rejected():
    assert is_runnable_candidate(INVALID_SYNTAX) is False
