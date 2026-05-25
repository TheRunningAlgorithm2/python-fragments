from fragments.lsp.file_state import FileState
from lsprotocol import types

IMPORT_PREFIX = "from fragments.html.elements import el, sequence, comment\n"
IMPORT_PREFIX_LEN = len(IMPORT_PREFIX)


def make_state(source_str: str) -> FileState:
    return FileState(source_str)


# ---------------------------------------------------------------------------
# Python-only (no fragments)
# ---------------------------------------------------------------------------


def test_no_fragments_offset():
    source = "x = 1\n"
    state = make_state(source)
    # Offsets map to source_offset + IMPORT_PREFIX_LEN in transpiled.
    # Offset 0 is excluded by the exclusive-start range semantics.
    for k in range(1, len(source)):
        assert state.ast_module.map_offset(k) == IMPORT_PREFIX_LEN + k
    # Import prefix is not mappable from any source position
    for k in range(IMPORT_PREFIX_LEN):
        assert state.ast_module.unmap_offset(k) is None
    # Python content maps back correctly (offset IMPORT_PREFIX_LEN is excluded)
    for k in range(1, len(source)):
        assert state.ast_module.unmap_offset(IMPORT_PREFIX_LEN + k) == k


def test_no_fragments_content():
    source = "x = 1\n"
    state = make_state(source)
    # Verify the content at each mapped transpiled offset matches the source.
    # Offset 0 is excluded by exclusive-start range semantics.
    for k in range(1, len(source)):
        t = state.ast_module.map_offset(k)
        assert t is not None
        assert state.transpiled[t] == source[k]


def test_no_fragments_position_mapping():
    # "x = 1\ny = 2\n" — character 0 on each line is excluded by exclusive-start.
    state = make_state("x = 1\ny = 2\n")
    pos = state.map_position(types.Position(line=0, character=1))
    assert pos is not None
    assert pos.line == 1
    assert pos.character == 1

    pos2 = state.map_position(types.Position(line=1, character=4))
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

    # Characters of the expression are mappable (first char excluded by exclusive-start).
    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} should be mappable"
        assert state.transpiled[t] == expr[k]

    # Round-trip
    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == expr_start + k


def test_html_text_not_mappable():
    source = "<>\n    <p>Hello</p>\n</>"
    state = make_state(source)
    text_start = source.index("Hello")
    for k in range(len("Hello")):
        assert state.ast_module.map_offset(text_start + k) is None


def test_fragment_delimiters_not_mappable():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    # Interior fragment structure is not mappable.
    # Note: "<>" at the boundary of the preceding Python span is excluded separately.
    for char in ("<p>", "</p>", "</>"):
        pos = source.index(char)
        assert state.ast_module.map_offset(pos) is None


def test_import_prefix_not_mappable():
    state = make_state("x = 1\n")
    for k in range(IMPORT_PREFIX_LEN):
        assert state.ast_module.unmap_offset(k) is None
    # IMPORT_PREFIX_LEN maps to source offset 0 (start of the Python content)
    assert state.ast_module.unmap_offset(IMPORT_PREFIX_LEN) == 0
    assert state.ast_module.unmap_offset(IMPORT_PREFIX_LEN + 1) == 1


# ---------------------------------------------------------------------------
# Python code before and after a fragment
# ---------------------------------------------------------------------------


def test_python_before_fragment():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    python_part = "x = 1\n"
    # First character excluded by exclusive-start range semantics.
    for k in range(1, len(python_part)):
        t = state.ast_module.map_offset(k)
        assert t is not None
        assert state.transpiled[t] == python_part[k]


def test_python_after_fragment_content():
    # Python code after a fragment must map to the correct position in transpiled
    source = "x = 1\n<>\n    <p>Hi</p>\n</>\ny = 2\n"
    state = make_state(source)
    python_after = "\ny = 2\n"
    python_after_start = source.index(python_after)

    # First character excluded by exclusive-start range semantics.
    for k in range(1, len(python_after)):
        t = state.ast_module.map_offset(python_after_start + k)
        assert t is not None, f"char {k!r} of python-after-fragment should be mappable"
        assert state.transpiled[t] == python_after[k], f"transpiled[{t}] = {state.transpiled[t]!r}, expected {python_after[k]!r}"


def test_python_after_fragment_round_trip():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>\ny = 2\n"
    state = make_state(source)
    python_after = "\ny = 2\n"
    python_after_start = source.index(python_after)

    # First character excluded by exclusive-start range semantics.
    for k in range(1, len(python_after)):
        t = state.ast_module.map_offset(python_after_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == python_after_start + k


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
        t = state.ast_module.map_offset(between_start + k)
        assert t is not None
        assert state.transpiled[t] == between[k]


# ---------------------------------------------------------------------------
# HTML element attribute interpolation mapping
# ---------------------------------------------------------------------------


def test_html_attribute_interpolation_is_mappable():
    source = "<><div class={{ expr }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # skip '{{ '
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside attribute interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_html_attribute_interpolation_round_trip():
    source = "<><div class={{ expr }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == expr_start + k


# ---------------------------------------------------------------------------
# Control node interpolation mapping (if / for)
# ---------------------------------------------------------------------------


def test_if_interpolation_is_mappable():
    source = "<><div if={{ condition }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # skip '{{ '
    expr = "condition"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside if-interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_if_interpolation_round_trip():
    source = "<><div if={{ condition }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "condition"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == expr_start + k


def test_for_interpolation_is_mappable():
    source = "<><li for={{ item in items }}>{{ item }}</li></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # first {{ is the for attribute
    expr = "item in items"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside for-interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_for_interpolation_round_trip():
    source = "<><li for={{ item in items }}>{{ item }}</li></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "item in items"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == expr_start + k


# ---------------------------------------------------------------------------
# Component argument interpolation mapping
# ---------------------------------------------------------------------------


def test_component_argument_interpolation_is_mappable():
    source = "<><MyComp value={{ expr }} /></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # skip '{{ '
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside component argument should be mappable"
        assert state.transpiled[t] == expr[k]


def test_component_argument_interpolation_round_trip():
    source = "<><MyComp value={{ expr }} /></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.ast_module.map_offset(expr_start + k)
        assert t is not None
        assert state.ast_module.unmap_offset(t) == expr_start + k
