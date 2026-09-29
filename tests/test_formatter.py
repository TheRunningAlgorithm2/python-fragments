import pytest

pytest.importorskip("black")

from fragments.formatter import format_source  # noqa: E402
from fragments.transpiler import transpile  # noqa: E402

UNFORMATTED = """import os
def page(title,items):
    x   = {'a':1}
    return <>
        <h1>{{title}}</h1>
          <ul><li for={{i in items}}>{{i}}</li></ul>
    </>
y = foo( <><b>hi</b></>,   2)
"""


def test_python_is_formatted():
    formatted = format_source(UNFORMATTED)
    assert 'x = {"a": 1}' in formatted
    assert "y = foo(<><b>hi</b></>, 2)" in formatted


def test_fragments_are_untouched():
    formatted = format_source(UNFORMATTED)
    assert "<h1>{{title}}</h1>\n          <ul><li for={{i in items}}>{{i}}</li></ul>" in formatted


def test_idempotent():
    once = format_source(UNFORMATTED)
    assert format_source(once) == once


def test_transpiled_output_unchanged():
    import black

    normalize = lambda source: black.format_str(transpile(source), mode=black.Mode())
    assert normalize(format_source(UNFORMATTED)) == normalize(UNFORMATTED)


def test_placeholder_collision():
    source = "__fragment_0__ = <><b>hi</b></>\n"
    assert format_source(source) == source


def test_formatting_edits_replace_whole_document():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    (edit,) = formatting_edits(UNFORMATTED)
    assert edit.new_text == format_source(UNFORMATTED)
    assert (edit.range.start.line, edit.range.start.character) == (0, 0)
    assert (edit.range.end.line, edit.range.end.character) == (UNFORMATTED.count("\n"), 0)


def test_formatting_edits_empty_when_already_formatted():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    assert formatting_edits(format_source(UNFORMATTED)) == []


def test_formatting_edits_empty_when_python_is_invalid():
    from fragments.lsp.client_message_handlers.formatting import formatting_edits

    assert formatting_edits("def broken(:\n") == []


def test_formatting_handler_responds_with_error_when_formatting_fails(monkeypatch: pytest.MonkeyPatch):
    import asyncio

    from lsprotocol import types

    from fragments.lsp import based_proxy
    from fragments.lsp.client_message_handlers import formatting
    from fragments.lsp.file_state import FileState

    class RecordingProxy:
        def __init__(self) -> None:
            self.responses: list[types.ResponseErrorMessage] = []

        def respond(self, request_id: int | str, response: types.ResponseErrorMessage) -> None:
            self.responses.append(response)

    def fail(original: str) -> list[types.TextEdit]:
        raise RuntimeError("Formatting requires black")

    proxy = RecordingProxy()
    monkeypatch.setattr(based_proxy, "_PROXY", proxy)
    monkeypatch.setitem(based_proxy.FILE_STATES, "file:///t.py", FileState(UNFORMATTED))
    monkeypatch.setattr(formatting, "formatting_edits", fail)

    request = types.DocumentFormattingRequest(
        id=7,
        params=types.DocumentFormattingParams(
            text_document=types.TextDocumentIdentifier(uri="file:///t.py"),
            options=types.FormattingOptions(tab_size=4, insert_spaces=True),
        ),
    )
    asyncio.run(formatting.formatting(request))

    (response,) = proxy.responses
    assert response.error is not None
    assert "black" in response.error.message
