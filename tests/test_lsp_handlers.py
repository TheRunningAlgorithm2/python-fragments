"""Run the real LSP handlers against a fake basedpyright to check positions are remapped onto the right source text."""

import asyncio
import re

import pytest
from lsprotocol import types

from fragments.lsp import based_proxy
from fragments.lsp.client_message_handlers.inlay_hints import inlay_hint
from fragments.lsp.client_message_handlers.semantic_tokens import semantic_tokens_full
from fragments.lsp.file_state import FileState

URI = "file:///test_doc.py"

PYTHON_PREAMBLE = "def page(obj):\n    return <>\n"
PARENTS = {
    "element": ("<div>", "</div>"),
    "component": ("<Layout>", "</Layout>"),
}
CHILD_LAYOUTS = {
    "inline": "{{ greet(obj.value) }}<Comp value={{ obj.value }} />",
    "whitespace": "\n            {{ greet(obj.value) }}\n            <Comp value={{ obj.value }} />\n        ",
}


class FakePyright:
    def __init__(self, response: types.SemanticTokensResponse | types.InlayHintResponse) -> None:
        self.response = response

    async def request(self, message):
        return self.response


class FakeClient:
    def __init__(self) -> None:
        self.responses = []

    def respond(self, request_id, response) -> None:
        self.responses.append(response)


def _source(parent: str, layout: str) -> str:
    opening, closing = PARENTS[parent]
    return f"{PYTHON_PREAMBLE}        {opening}{CHILD_LAYOUTS[layout]}{closing}\n    </>\n"


def _position(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset)
    return line, offset - (text.rfind("\n", 0, offset) + 1)


IDENTIFIERS = r"\b(greet|obj|value)\b"


def _fragment_identifiers(text: str, start: int, pattern: str = IDENTIFIERS) -> list[tuple[int, str]]:
    """(offset, name) for each identifier matching `pattern` from `start` onwards, in order."""
    return [(m.start(), m.group()) for m in re.compile(pattern).finditer(text, start)]


def _encode(text: str, identifiers: list[tuple[int, str]]) -> list[int]:
    """Delta-encode tokens the way basedpyright does (identifiers must be in document order)."""
    data: list[int] = []
    previous_line = previous_character = 0
    for offset, name in identifiers:
        line, character = _position(text, offset)
        data += [line - previous_line, character if line != previous_line else character - previous_character, len(name), 0, 0]
        previous_line, previous_character = line, character
    return data


def _decode(text: str, data: list[int]) -> list[str]:
    """Decode tokens per the LSP spec and return the source text each one covers."""
    lines = text.split("\n")
    covered: list[str] = []
    line = character = 0
    for i in range(0, len(data), 5):
        delta_line, delta_character, length = data[i : i + 3]
        line += delta_line
        character = delta_character if delta_line != 0 else character + delta_character
        in_range = 0 <= line < len(lines) and 0 <= character
        covered.append(lines[line][character : character + length] if in_range else "<out of range>")
    return covered


@pytest.fixture
def client(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(based_proxy, "_PROXY", fake_client)
    yield fake_client
    based_proxy.FILE_STATES.pop(URI, None)


def _install(monkeypatch, source: str, response) -> FileState:
    state = FileState(source)
    based_proxy.FILE_STATES[URI] = state
    monkeypatch.setattr(based_proxy, "_PYRIGHT", FakePyright(response))
    return state


@pytest.mark.parametrize("layout", CHILD_LAYOUTS)
@pytest.mark.parametrize("parent", PARENTS)
def _run_semantic_tokens(monkeypatch, source: str, pattern: str = IDENTIFIERS) -> None:
    """Feed the handler the tokens basedpyright would report for every matching identifier in the transpiled code."""
    transpiled = FileState(source).transpiled
    data = _encode(transpiled, _fragment_identifiers(transpiled, transpiled.index('""+'), pattern))
    _install(monkeypatch, source, types.SemanticTokensResponse(id=1, result=types.SemanticTokens(data=data)))
    request = types.SemanticTokensRequest(id=1, params=types.SemanticTokensParams(text_document=types.TextDocumentIdentifier(uri=URI)))
    asyncio.run(semantic_tokens_full(request))


@pytest.mark.parametrize("layout", CHILD_LAYOUTS)
@pytest.mark.parametrize("parent", PARENTS)
def test_semantic_tokens_cover_the_same_identifiers(monkeypatch, client, parent: str, layout: str):
    source = _source(parent, layout)
    _run_semantic_tokens(monkeypatch, source)

    covered = _decode(source, client.responses[0].result.data)
    expected = [name for _, name in _fragment_identifiers(source, source.index("<>"))]
    assert covered == expected


@pytest.mark.parametrize("layout", CHILD_LAYOUTS)
@pytest.mark.parametrize("parent", PARENTS)
def test_inlay_hint_sits_before_the_argument(monkeypatch, client, parent: str, layout: str):
    source = _source(parent, layout)
    transpiled = FileState(source).transpiled

    # basedpyright's `name=` hint goes immediately before the positional argument of `greet(...)`.
    hint_line, hint_character = _position(transpiled, transpiled.index("greet(obj.value)") + len("greet("))
    hint = types.InlayHint(position=types.Position(line=hint_line, character=hint_character), label="name=")

    _install(monkeypatch, source, types.InlayHintResponse(id=1, result=[hint]))
    source_lines = source.split("\n")
    full_range = types.Range(start=types.Position(line=0, character=0), end=types.Position(line=len(source_lines) - 1, character=0))
    request = types.InlayHintRequest(id=1, params=types.InlayHintParams(text_document=types.TextDocumentIdentifier(uri=URI), range=full_range))
    asyncio.run(inlay_hint(request))

    [remapped] = client.responses[0].result
    expected_line, expected_character = _position(source, source.index("greet(obj.value)") + len("greet("))
    assert (remapped.position.line, remapped.position.character) == (expected_line, expected_character)


# ---------------------------------------------------------------------------
# Semantic token ordering
#
# basedpyright returns tokens in transpiled order. Some constructs transpile
# their parts in a different order from the source (component arguments come
# after children; `if` / `for` expressions come after the element body), so the
# unmapped tokens come back out of document order. The LSP spec requires tokens
# sorted by position with unsigned deltas; a negative delta corrupts every token
# after it for clients that decode into unsigned integers.
# ---------------------------------------------------------------------------

ORDER_IDENTIFIERS = r"\b(obj|value|greet|flag|cls|body|items|item|after|later|arg)\b"
TRAILING_PYTHON = "\n\n\ndef later(arg):\n    return arg\n"

OUT_OF_ORDER_FRAGMENTS = {
    "control_no_reordering": "<>\n    <div class={{ cls }}>\n        {{ greet(body) }}\n        <Comp value={{ obj }} />\n    </div>\n    {{ after }}\n</>",
    "component_arguments_and_children": "<><Comp value={{ obj }}>{{ greet(body) }}</Comp>{{ after }}</>",
    "component_arguments_and_children_multiline": "<>\n    <Comp\n        value={{ obj }}>\n        {{ greet(body) }}\n    </Comp>\n    {{ after }}\n</>",
    "for_attribute": "<><li for={{ item in items }}>{{ item.value }}</li>{{ after }}</>",
    "for_attribute_multiline": "<>\n    <li for={{ item in items }}>\n        {{ item.value }}\n    </li>\n    {{ after }}\n</>",
    "if_attribute": "<><p if={{ flag }}>{{ body }}</p>{{ after }}</>",
    "if_attribute_before_other_attribute": "<><p if={{ flag }} class={{ cls }}>text</p>{{ after }}</>",
    "if_attribute_on_component": "<><Comp if={{ flag }} value={{ obj }} />{{ after }}</>",
}


def _order_source(fragment: str) -> str:
    return f"x = {fragment}{TRAILING_PYTHON}"


@pytest.mark.parametrize("fragment", OUT_OF_ORDER_FRAGMENTS)
def test_semantic_tokens_are_unsigned(monkeypatch, client, fragment: str):
    """Every emitted value is a `uinteger` in the LSP spec."""
    _run_semantic_tokens(monkeypatch, _order_source(OUT_OF_ORDER_FRAGMENTS[fragment]), ORDER_IDENTIFIERS)

    data = client.responses[0].result.data
    negative = [(i // 5, tuple(data[i : i + 3])) for i in range(0, len(data), 5) if min(data[i : i + 3]) < 0]
    assert negative == [], f"tokens with negative deltas (index, (delta_line, delta_start, length)): {negative}"


@pytest.mark.parametrize("fragment", OUT_OF_ORDER_FRAGMENTS)
def test_semantic_tokens_are_in_document_order(monkeypatch, client, fragment: str):
    source = _order_source(OUT_OF_ORDER_FRAGMENTS[fragment])
    _run_semantic_tokens(monkeypatch, source, ORDER_IDENTIFIERS)

    covered = _decode(source, client.responses[0].result.data)
    expected = [name for _, name in _fragment_identifiers(source, 0, ORDER_IDENTIFIERS)]
    assert covered == expected


@pytest.mark.parametrize("fragment", OUT_OF_ORDER_FRAGMENTS)
def test_semantic_tokens_after_fragment_survive_unsigned_decoding(monkeypatch, client, fragment: str):
    """A client storing tokens as uint32 (e.g. a Uint32Array) must still place the Python after the fragment correctly."""
    source = _order_source(OUT_OF_ORDER_FRAGMENTS[fragment])
    _run_semantic_tokens(monkeypatch, source, ORDER_IDENTIFIERS)

    unsigned = [value % 2**32 for value in client.responses[0].result.data]
    covered = _decode(source, unsigned)
    assert covered[-3:] == ["later", "arg", "arg"]
