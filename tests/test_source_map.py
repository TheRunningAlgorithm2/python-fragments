from fragments.lsp.source_map import transpile_with_map


def test_no_fragments():
    source = "x = 1\n"
    result, segments = transpile_with_map(source)
    assert segments == []
    assert result == "from fragments.html.elements import el, sequence\nx = 1\n"


def test_single_fragment():
    source = "return <>\n    <h1>Hello</h1>\n</>"
    result, segments = transpile_with_map(source)

    assert len(segments) == 1
    seg = segments[0]
    assert source[seg.orig_start : seg.orig_end] == "<>\n    <h1>Hello</h1>\n</>"
    assert result[seg.trans_start : seg.trans_end] == 'sequence([el("h1", ["Hello"], {}, False)])'


def test_python_before_fragment():
    source = "x = 1\nreturn <>\n    <p>Hi</p>\n</>"
    result, segments = transpile_with_map(source)

    assert len(segments) == 1
    seg = segments[0]
    assert source[seg.orig_start : seg.orig_end] == "<>\n    <p>Hi</p>\n</>"
    assert result[seg.trans_start : seg.trans_end] == 'sequence([el("p", ["Hi"], {}, False)])'


def test_python_after_fragment():
    source = "return <>\n    <p>Hi</p>\n</>\nx = 1\n"
    result, segments = transpile_with_map(source)

    assert len(segments) == 1
    # verify the python after the fragment lands at the right offset in the result
    seg = segments[0]
    after_orig = source[seg.orig_end :]
    after_trans = result[seg.trans_end :]
    assert after_orig == after_trans


def test_multiple_fragments():
    source = "return <>\n    <h1>Hello</h1>\n</>\nreturn <>\n    <p>World</p>\n</>"
    result, segments = transpile_with_map(source)

    assert len(segments) == 2
    assert source[segments[0].orig_start : segments[0].orig_end] == "<>\n    <h1>Hello</h1>\n</>"
    assert source[segments[1].orig_start : segments[1].orig_end] == "<>\n    <p>World</p>\n</>"


def test_segment_offsets_are_contiguous():
    # nothing is lost or double-counted between segments
    source = "a = 1\nreturn <>\n    <h1>Hi</h1>\n</>\nb = 2\nreturn <>\n    <p>Bye</p>\n</>\nc = 3\n"
    result, segments = transpile_with_map(source)

    assert len(segments) == 2
    s0, s1 = segments

    # gap between the two fragments in the original should match the gap in the transpiled output
    orig_between = source[s0.orig_end : s1.orig_start]
    trans_between = result[s0.trans_end : s1.trans_start]
    assert orig_between == trans_between
