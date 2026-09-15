from checkapi.fix_drafter import draft_and_verify_fix
from checkapi.sandbox import ExecutionResult


class FakeContent:
    def __init__(self, text):
        self.text = text


class FakeMessage:
    def __init__(self, text):
        self.content = [FakeContent(text)]


class FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeMessage(response)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def test_verified_fix_returns_diff():
    client = FakeClient(["```python\nprint('fixed')\n```"])

    def fake_execute(code):
        assert code == "print('fixed')"
        return ExecutionResult(status="pass", stdout="fixed\n", stderr="", error_text=None)

    result = draft_and_verify_fix(
        "doc text", "NameError: boom", "print('broken')", fake_execute, llm_client=client
    )

    assert result.verified is True
    assert "print('fixed')" in result.diff
    assert "print('broken')" in result.diff


def test_fix_that_still_fails_is_not_verified():
    client = FakeClient(["```python\nprint('still broken')\n```"])

    def fake_execute(code):
        return ExecutionResult(status="fail", stdout="", stderr="", error_text="still broken")

    result = draft_and_verify_fix(
        "doc text", "NameError: boom", "print('broken')", fake_execute, llm_client=client
    )

    assert result.verified is False
    assert result.diff is None


def test_llm_failure_retries_once_then_gives_up_without_executing():
    client = FakeClient([RuntimeError("provider hiccup"), RuntimeError("still down")])
    executed = []

    result = draft_and_verify_fix(
        "doc text", "NameError: boom", "print('broken')", executed.append, llm_client=client
    )

    assert result.verified is False
    assert result.diff is None
    assert client.messages.calls == 2
    assert executed == []


class FakeMessageWithEmptyContent:
    def __init__(self):
        self.content = []


class FakeMessagesReturningEmptyContent:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return FakeMessageWithEmptyContent()


class FakeClientWithEmptyContent:
    def __init__(self):
        self.messages = FakeMessagesReturningEmptyContent()


def test_malformed_response_with_empty_content_fails_gracefully():
    client = FakeClientWithEmptyContent()

    def fake_execute(code):
        raise AssertionError("execute_fn should not be called")

    result = draft_and_verify_fix(
        "doc text", "NameError: boom", "print('broken')", fake_execute, llm_client=client
    )

    assert result.verified is False
    assert result.diff is None


def test_execute_fn_error_fails_gracefully():
    client = FakeClient(["```python\nprint('fixed')\n```"])

    def fake_execute(code):
        raise RuntimeError("execution sandbox crashed")

    result = draft_and_verify_fix(
        "doc text", "NameError: boom", "print('broken')", fake_execute, llm_client=client
    )

    assert result.verified is False
    assert result.diff is None
