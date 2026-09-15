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

ASYNC_FUNCTION = """
import asyncio

async def greet():
    await asyncio.sleep(0)
    return "hello"

print(asyncio.run(greet()))
"""

FUNCTION_PARAMETERS = """
from langchain_core.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    return a * b

print(multiply.invoke({"a": 2, "b": 3}))
"""

VARIADIC_PARAMETERS = """
import json

def dump(*values, indent=2, **options):
    return json.dumps(values, indent=indent, **options)

print(dump(1, 2))
"""

ANNOTATED_ASSIGNMENT = """
from langchain_openai import ChatOpenAI

llm: ChatOpenAI = ChatOpenAI(model="gpt-4o-mini")
print(llm.invoke("hi").content)
"""

COMPREHENSION_TARGET = """
import json

payloads = [json.dumps({"topic": topic}) for topic in ["cats", "dogs"]]
print(payloads)
"""

EXCEPT_HANDLER_NAME = """
import json

try:
    json.loads("{not json}")
except ValueError as error:
    print(error)
"""

LAMBDA_PARAMETER = """
import json

serialize = lambda value: json.dumps(value)
print(serialize({"a": 1}))
"""

WALRUS_ASSIGNMENT = """
import math

if (floored := math.floor(5.5)) > 1:
    print(floored)
"""

ASYNC_WITH = """
import asyncio

async def guarded():
    lock = asyncio.Lock()
    async with lock as acquired:
        return acquired

print(asyncio.run(guarded()))
"""

# `registry` / `cached` are only ever read, so the global/nonlocal statement
# is the only thing that can resolve them, which is the point of the test.
GLOBAL_DECLARATION = """
import json

def report():
    global registry
    print(json.dumps(registry))
"""

NONLOCAL_DECLARATION = """
import json

def outer():
    def inner():
        nonlocal cached
        print(json.dumps(cached))
    inner()
"""

ATTRIBUTE_TARGET_DEFINED_OBJ = """
from argparse import Namespace

config = Namespace()
config.debug = True
print(config.debug)
"""

ATTRIBUTE_TARGET_UNDEFINED_OBJ = """
import json

config.debug = json.dumps({"debug": True})
"""


def test_self_contained_snippet_is_candidate():
    assert is_runnable_candidate(SELF_CONTAINED) is True


def test_fragment_without_import_is_rejected():
    assert is_runnable_candidate(FRAGMENT_NO_IMPORT) is False


def test_fragment_with_unresolved_name_is_rejected():
    assert is_runnable_candidate(FRAGMENT_UNRESOLVED_NAME) is False


def test_invalid_syntax_is_rejected():
    assert is_runnable_candidate(INVALID_SYNTAX) is False


def test_async_function_is_candidate():
    assert is_runnable_candidate(ASYNC_FUNCTION) is True


def test_function_parameters_are_candidate():
    assert is_runnable_candidate(FUNCTION_PARAMETERS) is True


def test_variadic_and_keyword_only_parameters_are_candidate():
    assert is_runnable_candidate(VARIADIC_PARAMETERS) is True


def test_annotated_assignment_is_candidate():
    assert is_runnable_candidate(ANNOTATED_ASSIGNMENT) is True


def test_comprehension_target_is_candidate():
    assert is_runnable_candidate(COMPREHENSION_TARGET) is True


def test_except_handler_name_is_candidate():
    assert is_runnable_candidate(EXCEPT_HANDLER_NAME) is True


def test_lambda_parameter_is_candidate():
    assert is_runnable_candidate(LAMBDA_PARAMETER) is True


def test_walrus_assignment_is_candidate():
    assert is_runnable_candidate(WALRUS_ASSIGNMENT) is True


def test_async_with_is_candidate():
    assert is_runnable_candidate(ASYNC_WITH) is True


def test_global_declaration_is_candidate():
    assert is_runnable_candidate(GLOBAL_DECLARATION) is True


def test_nonlocal_declaration_is_candidate():
    assert is_runnable_candidate(NONLOCAL_DECLARATION) is True


def test_attribute_target_with_defined_object_is_candidate():
    assert is_runnable_candidate(ATTRIBUTE_TARGET_DEFINED_OBJ) is True


def test_attribute_target_does_not_define_the_object_itself():
    # `config.debug = ...` reads `config`; it must not make `config` resolved.
    assert is_runnable_candidate(ATTRIBUTE_TARGET_UNDEFINED_OBJ) is False
