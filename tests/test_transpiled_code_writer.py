import pytest

from fragments.source_map import Segment, SourceMap
from fragments.transpiled_code_writer import TranspiledCodeWriter


def test_write_appends_code_without_mapping():
    writer = TranspiledCodeWriter("<>{{ obj }}</>")
    writer.write('""')
    writer.write("+")

    assert writer.transpiled_content() == '""+'
    assert writer.source_map().segments == []


def test_map_copies_source_verbatim():
    source = "<>{{ obj.value }}</>"
    writer = TranspiledCodeWriter(source)
    writer.write('""+str(')
    writer.map(source.index("obj"), source.index(" }}"))
    writer.write(")")

    assert writer.transpiled_content() == '""+str(obj.value)'
    assert writer.source_map().segments == [Segment(source_start=5, transpiled_start=7, length=9)]


@pytest.mark.parametrize("span", [(-1, 2), (3, 2), (0, 100)])
def test_map_rejects_spans_outside_the_source(span: tuple[int, int]):
    writer = TranspiledCodeWriter("<>{{ obj }}</>")
    with pytest.raises(ValueError):
        writer.map(*span)


def test_segments_always_match_the_source():
    """The invariant every transpiled node relies on - guaranteed by construction, since `map` copies the source itself."""
    source = "x = 1\n<><li for={{ item in items }}>{{ item.value }}</li></>\ny = 2\n"
    writer = TranspiledCodeWriter(source)
    writer.map(0, source.index("<>"))
    writer.write("''.join(str(f\"<li>\"+str(")
    writer.map(source.index("item.value"), source.index("item.value") + len("item.value"))
    writer.write(')+"</li>") for ')
    writer.map(source.index("item in items"), source.index("item in items") + len("item in items"))
    writer.write(")")
    writer.map(source.index("</>") + 3, len(source))

    transpiled = writer.transpiled_content()
    for segment in writer.source_map().segments:
        assert transpiled[segment.transpiled_start : segment.transpiled_end] == source[segment.source_start : segment.source_end]


# ---------------------------------------------------------------------------
# SourceMap lookups
# ---------------------------------------------------------------------------


def test_offsets_inside_a_segment_round_trip():
    source_map = SourceMap([Segment(source_start=10, transpiled_start=50, length=5)])

    for offset in range(10, 16):
        transpiled = source_map.map_offset(offset)
        assert transpiled == offset + 40
        assert source_map.unmap_offset(transpiled) == offset


def test_offsets_outside_segments_do_not_map():
    source_map = SourceMap([Segment(source_start=10, transpiled_start=50, length=5)])

    assert source_map.map_offset(9) is None
    assert source_map.map_offset(16) is None
    assert source_map.unmap_offset(49) is None
    assert source_map.unmap_offset(56) is None


def test_segment_end_is_inclusive():
    """A cursor just after the last character of `obj` (e.g. before typing `.`) is still inside it."""
    source_map = SourceMap([Segment(source_start=10, transpiled_start=50, length=3)])

    assert source_map.map_offset(13) == 53
    assert source_map.unmap_offset(53) == 13


def test_touching_segments_prefer_the_later_segment():
    """An offset at the end of one segment and the start of the next belongs to the one that owns its character."""
    source_map = SourceMap([Segment(source_start=0, transpiled_start=0, length=5), Segment(source_start=5, transpiled_start=20, length=5)])

    assert source_map.map_offset(5) == 20
    assert source_map.map_offset(4) == 4


def test_empty_segment_maps_its_single_offset():
    """An empty interpolation `{{ }}` still needs a cursor position inside it, e.g. for completions."""
    source_map = SourceMap([Segment(source_start=7, transpiled_start=30, length=0)])

    assert source_map.map_offset(7) == 30
    assert source_map.unmap_offset(30) == 7
    assert source_map.map_offset(8) is None


def test_segments_out_of_order_map_in_both_directions():
    """`<li for={{ items }}>{{ item }}</li>` transpiles the body before the loop - the reverse of source order."""
    body = Segment(source_start=30, transpiled_start=10, length=4)
    loop = Segment(source_start=12, transpiled_start=25, length=5)
    source_map = SourceMap([body, loop])

    assert source_map.map_offset(31) == 11
    assert source_map.map_offset(13) == 26
    assert source_map.unmap_offset(11) == 31
    assert source_map.unmap_offset(26) == 13
