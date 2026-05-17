from fragments import grammar
from fragments.lsp.file_state import _FileState
from fragments.source import Source
from lsprotocol import types

IMPORT_PREFIX = "from fragments.html.elements import el, sequence\n"
IMPORT_PREFIX_LEN = len(IMPORT_PREFIX)  # 49


def make_state(source_str: str) -> _FileState:
    _, module = grammar.expect_module(Source.from_string(source_str))
    module.transpile()
    return _FileState(source_str, module.transpiled_content, module)


# ---------------------------------------------------------------------------
# Python-only (no fragments)
# ---------------------------------------------------------------------------

def test_no_fragments_offset():
    source = "x = 1\n"
    state = make_state(source)
    # Every source offset maps to source_offset + IMPORT_PREFIX_LEN in transpiled
    for k in range(len(source)):
        assert state._original_offset_to_transpiled_offset(k) == IMPORT_PREFIX_LEN + k
    # Import prefix is not mappable from any source position
    for k in range(IMPORT_PREFIX_LEN):
        assert state._transpiled_offset_to_original_offset(k) is None
    # Python content maps back correctly
    for k in range(len(source)):
        assert state._transpiled_offset_to_original_offset(IMPORT_PREFIX_LEN + k) == k


def test_no_fragments_content():
    source = "x = 1\n"
    state = make_state(source)
    # Verify the content at each mapped transpiled offset matches the source
    for k in range(len(source)):
        t = state._original_offset_to_transpiled_offset(k)
        assert t is not None
        assert state.transpiled[t] == source[k]


def test_no_fragments_position_mapping():
    # "x = 1\ny = 2\n" → line 0 col 0 maps to transpiled line 1 col 0 (after import)
    state = make_state("x = 1\ny = 2\n")
    pos = state.original_to_transpiled_position(types.Position(line=0, character=0))
    assert pos is not None
    assert pos.line == 1
    assert pos.character == 0

    pos2 = state.original_to_transpiled_position(types.Position(line=1, character=4))
    assert pos2 is not None
    assert pos2.line == 2
    assert pos2.character == 4


# ---------------------------------------------------------------------------
# Fragment with interpolation
# ---------------------------------------------------------------------------

def test_interpolation_is_mappable():
    source = "<>\n    <p>{{ title }}</p>\n</>"
    state = make_state(source)
    interp_start = source.index("{{")
    # expression 'title' starts after '{{ ' (2 + 1 space)
    expr_start = interp_start + 3
    expr = "title"

    # Every character of the expression is mappable
    for k in range(len(expr)):
        t = state._original_offset_to_transpiled_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} should be mappable"
        assert state.transpiled[t] == expr[k]

    # Round-trip
    for k in range(len(expr)):
        t = state._original_offset_to_transpiled_offset(expr_start + k)
        assert t is not None
        assert state._transpiled_offset_to_original_offset(t) == expr_start + k


def test_html_text_not_mappable():
    source = "<>\n    <p>Hello</p>\n</>"
    state = make_state(source)
    text_start = source.index("Hello")
    for k in range(len("Hello")):
        assert state._original_offset_to_transpiled_offset(text_start + k) is None


def test_fragment_delimiters_not_mappable():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    for char in ("<>", "<p>", "</p>", "</>"):
        pos = source.index(char)
        assert state._original_offset_to_transpiled_offset(pos) is None


def test_import_prefix_not_mappable():
    state = make_state("x = 1\n")
    for k in range(IMPORT_PREFIX_LEN):
        assert state._transpiled_offset_to_original_offset(k) is None
    assert state._transpiled_offset_to_original_offset(IMPORT_PREFIX_LEN) == 0


# ---------------------------------------------------------------------------
# Python code before and after a fragment
# ---------------------------------------------------------------------------

def test_python_before_fragment():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    python_part = "x = 1\n"
    for k in range(len(python_part)):
        t = state._original_offset_to_transpiled_offset(k)
        assert t is not None
        assert state.transpiled[t] == python_part[k]


def test_python_after_fragment_content():
    # Python code after a fragment must map to the correct position in transpiled
    source = "x = 1\n<>\n    <p>Hi</p>\n</>\ny = 2\n"
    state = make_state(source)
    python_after = "\ny = 2\n"
    python_after_start = source.index(python_after)

    for k in range(len(python_after)):
        t = state._original_offset_to_transpiled_offset(python_after_start + k)
        assert t is not None, f"char {k!r} of python-after-fragment should be mappable"
        assert state.transpiled[t] == python_after[k], (
            f"transpiled[{t}] = {state.transpiled[t]!r}, expected {python_after[k]!r}"
        )


def test_python_after_fragment_round_trip():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>\ny = 2\n"
    state = make_state(source)
    python_after = "\ny = 2\n"
    python_after_start = source.index(python_after)

    for k in range(len(python_after)):
        t = state._original_offset_to_transpiled_offset(python_after_start + k)
        assert t is not None
        assert state._transpiled_offset_to_original_offset(t) == python_after_start + k


# ---------------------------------------------------------------------------
# Multiple fragments
# ---------------------------------------------------------------------------

def test_multiple_fragments_python_between():
    source = "a = 1\n<>\n    <p>X</p>\n</>\nb = 2\n<>\n    <p>Y</p>\n</>\nc = 3\n"
    state = make_state(source)

    # Python between the two fragments should be mappable
    between = "b = 2\n"
    between_start = source.index(between)
    for k in range(len(between)):
        t = state._original_offset_to_transpiled_offset(between_start + k)
        assert t is not None
        assert state.transpiled[t] == between[k]
