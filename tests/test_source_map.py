import pytest
from fragments.lsp.file_state import FileState
from lsprotocol import types
from fragments.ast_nodes import IMPORT_PREFIX_LEN


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
        assert state.source_map.map_offset(k) == IMPORT_PREFIX_LEN + k
    # Import prefix is not mappable from any source position
    for k in range(IMPORT_PREFIX_LEN):
        assert state.source_map.unmap_offset(k) is None
    # Python content maps back correctly (offset IMPORT_PREFIX_LEN is excluded)
    for k in range(1, len(source)):
        assert state.source_map.unmap_offset(IMPORT_PREFIX_LEN + k) == k


def test_no_fragments_content():
    source = "x = 1\n"
    state = make_state(source)
    # Verify the content at each mapped transpiled offset matches the source.
    # Offset 0 is excluded by exclusive-start range semantics.
    for k in range(1, len(source)):
        t = state.source_map.map_offset(k)
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
    source = "<>\n    <p>{{ title in titles }}</p>\n</>"
    state = make_state(source)
    interp_start = source.index("{{")
    # expression 'title' starts after '{{ ' (2 + 1 space)
    expr_start = interp_start + 3
    expr = "title in titles"

    # Characters of the expression are mappable (first char excluded by exclusive-start).
    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} should be mappable"
        assert state.source_map.map_offset(expr_start + k - 1) == t - 1
        assert state.transpiled[t] == expr[k]

    # Characters in the white space after an expression are not mappable

    # Round-trip
    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == expr_start + k


def test_html_text_not_mappable():
    source = "<>\n    <p>Hello</p>\n</>"
    state = make_state(source)
    text_start = source.index("Hello")
    for k in range(len("Hello")):
        assert state.source_map.map_offset(text_start + k) is None


def test_fragment_delimiters_not_mappable():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    # Interior fragment structure is not mappable.
    # Note: "<>" at the boundary of the preceding Python span is excluded separately.
    for char in ("<p>", "</p>", "</>"):
        pos = source.index(char)
        assert state.source_map.map_offset(pos) is None


def test_import_prefix_not_mappable():
    state = make_state("x = 1\n")
    for k in range(IMPORT_PREFIX_LEN):
        assert state.source_map.unmap_offset(k) is None
    # IMPORT_PREFIX_LEN maps to source offset 0 (start of the Python content)
    assert state.source_map.unmap_offset(IMPORT_PREFIX_LEN) == 0
    assert state.source_map.unmap_offset(IMPORT_PREFIX_LEN + 1) == 1


# ---------------------------------------------------------------------------
# Python code before and after a fragment
# ---------------------------------------------------------------------------


def test_python_before_fragment():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>"
    state = make_state(source)
    python_part = "x = 1\n"
    # First character excluded by exclusive-start range semantics.
    for k in range(1, len(python_part)):
        t = state.source_map.map_offset(k)
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
        t = state.source_map.map_offset(python_after_start + k)
        assert t is not None, f"char {k!r} of python-after-fragment should be mappable"
        assert state.transpiled[t] == python_after[k], f"transpiled[{t}] = {state.transpiled[t]!r}, expected {python_after[k]!r}"


def test_python_after_fragment_round_trip():
    source = "x = 1\n<>\n    <p>Hi</p>\n</>\ny = 2\n"
    state = make_state(source)
    python_after = "\ny = 2\n"
    python_after_start = source.index(python_after)

    # First character excluded by exclusive-start range semantics.
    for k in range(1, len(python_after)):
        t = state.source_map.map_offset(python_after_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == python_after_start + k


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
        t = state.source_map.map_offset(between_start + k)
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
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside attribute interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_html_attribute_interpolation_round_trip():
    source = "<><div class={{ expr }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == expr_start + k


# ---------------------------------------------------------------------------
# Control node interpolation mapping (if / for)
# ---------------------------------------------------------------------------


def test_if_interpolation_is_mappable():
    source = "<><div if={{ condition }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # skip '{{ '
    expr = "condition"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside if-interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_if_interpolation_round_trip():
    source = "<><div if={{ condition }}>text</div></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "condition"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == expr_start + k


def test_for_interpolation_is_mappable():
    source = "<><li for={{ item in items }}>{{ item }}</li></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # first {{ is the for attribute
    expr = "item in items"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside for-interpolation should be mappable"
        assert state.transpiled[t] == expr[k]


def test_for_interpolation_round_trip():
    source = "<><li for={{ item in items }}>{{ item }}</li></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "item in items"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == expr_start + k


# ---------------------------------------------------------------------------
# Component argument interpolation mapping
# ---------------------------------------------------------------------------


def test_component_argument_interpolation_is_mappable():
    source = "<><MyComp value={{ expr }} /></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3  # skip '{{ '
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None, f"offset {expr_start + k} inside component argument should be mappable"
        assert state.transpiled[t] == expr[k]


def test_component_argument_interpolation_round_trip():
    source = "<><MyComp value={{ expr }} /></>"
    state = make_state(source)
    expr_start = source.index("{{") + 3
    expr = "expr"

    for k in range(1, len(expr)):
        t = state.source_map.map_offset(expr_start + k)
        assert t is not None
        assert state.source_map.unmap_offset(t) == expr_start + k


# ---------------------------------------------------------------------------
# Children of components
#
# Regression tests for misaligned LSP features (semantic tokens, inlay hints,
# hover) inside component children, e.g. `obj.value` highlighted as `o` +
# `bj.valu`. Element parents are included as a control: they map correctly.
# ---------------------------------------------------------------------------

PARENTS = {
    "element": ("<div>", "</div>"),
    "component": ("<Layout>", "</Layout>"),
}
CHILD_LAYOUTS = {
    "inline": "{{ greet(obj.value) }}<Comp value={{ obj.value }} />",
    "whitespace": "\n        {{ greet(obj.value) }}\n        <Comp value={{ obj.value }} />\n    ",
}


def _identifier_offsets(source: str) -> list[int]:
    """Source offsets of every character of every `obj` / `value` / `greet` inside an interpolation."""
    offsets = []
    search_from = 0
    while (open_index := source.find("{{", search_from)) != -1:
        close_index = source.index("}}", open_index)
        for name in ("greet", "obj", "value"):
            start = open_index
            while (start := source.find(name, start, close_index)) != -1:
                offsets.extend(range(start, start + len(name)))
                start += len(name)
        search_from = close_index
    return sorted(set(offsets))


@pytest.mark.parametrize("layout", CHILD_LAYOUTS)
@pytest.mark.parametrize("parent", PARENTS)
def test_children_interpolations_map_to_same_characters(parent: str, layout: str):
    opening, closing = PARENTS[parent]
    source = f"<>\n    {opening}{CHILD_LAYOUTS[layout]}{closing}\n</>"
    state = make_state(source)

    for offset in _identifier_offsets(source):
        t = state.source_map.map_offset(offset)
        assert t is not None, f"source offset {offset} ({source[offset]!r}) should be mappable"
        assert state.transpiled[t] == source[offset], f"source {source[offset]!r}@{offset} mapped to transpiled {state.transpiled[t]!r}@{t}"


@pytest.mark.parametrize("layout", CHILD_LAYOUTS)
@pytest.mark.parametrize("parent", PARENTS)
def test_children_interpolations_unmap_to_same_characters(parent: str, layout: str):
    """unmap_offset is what semantic tokens and inlay hints rely on."""
    opening, closing = PARENTS[parent]
    source = f"<>\n    {opening}{CHILD_LAYOUTS[layout]}{closing}\n</>"
    state = make_state(source)

    fragment_start = state.transpiled.index('""+')
    for t in range(fragment_start, len(state.transpiled)):
        o = state.source_map.unmap_offset(t)
        if o is None or not (state.transpiled[t].isalnum() or (o < len(source) and source[o].isalnum())):
            continue
        assert state.transpiled[t] == source[o], f"transpiled {state.transpiled[t]!r}@{t} unmapped to source {source[o]!r}@{o}"


def test_component_child_interpolation_start_offset():
    source = "<><Layout>{{ obj }}</Layout></>"
    state = make_state(source)
    expr_start = source.index("obj")

    t = state.source_map.map_offset(expr_start)
    assert t is not None
    assert state.transpiled[t : t + 3] == "obj"
    assert state.source_map.unmap_offset(state.transpiled.rindex("obj")) == expr_start


def test_nested_component_argument_inside_component():
    source = "<><Layout><Comp value={{ obj }} /></Layout></>"
    state = make_state(source)
    expr_start = source.index("obj")

    t = state.source_map.map_offset(expr_start)
    assert t is not None
    assert state.transpiled[t : t + 3] == "obj"
    assert state.source_map.unmap_offset(state.transpiled.rindex("obj")) == expr_start


@pytest.mark.parametrize("source", ["<><Comp value={{ obj }} /></>", "<><div>\n    {{ a }}\n    <Comp value={{ obj }} />\n</div></>"])
def test_component_name_first_character_round_trips(source: str):
    """The token for a component's opening tag starts at its first character - it must not be dropped."""
    state = make_state(source)
    name_start = source.index("Comp")
    transpiled_name_start = state.transpiled.index("Comp(")

    assert state.source_map.map_offset(name_start) == transpiled_name_start
    assert state.source_map.unmap_offset(transpiled_name_start) == name_start
