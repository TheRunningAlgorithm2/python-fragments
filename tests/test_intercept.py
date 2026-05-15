import asyncio

import pytest

from fragments.lsp.intercept import Interceptor, _FileState, _to_offset, _to_position, _trans_to_orig
from fragments.lsp.source_map import IMPORT_PREFIX, transpile_with_map

URI = "file:///test.py"


@pytest.fixture
def interceptor():
    return Interceptor()


def make_state(original: str) -> _FileState:
    transpiled, segments = transpile_with_map(original)
    return _FileState(original, transpiled, segments)


def diag_at(source: str, start_line: int, start_char: int, end_line: int, end_char: int) -> dict:
    """Build a minimal LSP diagnostic with a range expressed in terms of the given source."""
    return {
        "severity": 1,
        "message": "error",
        "range": {
            "start": {"line": start_line, "character": start_char},
            "end": {"line": end_line, "character": end_char},
        },
    }


def pos_in(source: str, offset: int) -> tuple[int, int]:
    """Return (line, character) for a char offset in source."""
    lines = source[:offset].split("\n")
    return len(lines) - 1, len(lines[-1])


def did_open(uri: str, text: str) -> dict:
    return {"method": "textDocument/didOpen", "params": {"textDocument": {"uri": uri, "text": text}}}


def did_change(uri: str, text: str) -> dict:
    return {"method": "textDocument/didChange", "params": {"textDocument": {"uri": uri}, "contentChanges": [{"text": text}]}}


def did_close(uri: str) -> dict:
    return {"method": "textDocument/didClose", "params": {"textDocument": {"uri": uri}}}


def publish_diagnostics(uri: str, diagnostics: list[dict]) -> dict:
    return {"method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": diagnostics}}


# --- position helpers ---

def test_to_offset_first_line():
    assert _to_offset("abc\ndef", 0, 0) == 0
    assert _to_offset("abc\ndef", 0, 2) == 2


def test_to_offset_second_line():
    assert _to_offset("abc\ndef", 1, 0) == 4
    assert _to_offset("abc\ndef", 1, 2) == 6


def test_to_position_roundtrip():
    source = "abc\ndef\nghi"
    for offset in range(len(source)):
        line, char = pos_in(source, offset)
        assert _to_offset(source, line, char) == offset


# --- trans_to_orig ---

def test_trans_to_orig_import_prefix_is_none():
    state = make_state("x = 1\n")
    assert _trans_to_orig(0, state) is None
    assert _trans_to_orig(len(IMPORT_PREFIX) - 1, state) is None


def test_trans_to_orig_no_fragments_maps_1to1():
    state = make_state("x = 1\ny = 2\n")
    prefix = len(IMPORT_PREFIX)
    assert _trans_to_orig(prefix + 0, state) == 0   # x
    assert _trans_to_orig(prefix + 4, state) == 4   # 1


def test_trans_to_orig_inside_fragment_is_none():
    state = make_state("return <>\n    <h1>Hi</h1>\n</>")
    seg = state.segments[0]
    assert _trans_to_orig(seg.trans_start, state) is None
    assert _trans_to_orig(seg.trans_start + 5, state) is None
    assert _trans_to_orig(seg.trans_end - 1, state) is None


def test_trans_to_orig_after_fragment_maps_correctly():
    original = "return <>\n    <h1>Hi</h1>\n</>\nx = 1\n"
    state = make_state(original)
    seg = state.segments[0]
    # First char after the fragment in both sources
    assert _trans_to_orig(seg.trans_end, state) == seg.orig_end


def test_trans_to_orig_between_two_fragments():
    original = "return <>\n    <h1>A</h1>\n</>\ny = 2\nreturn <>\n    <p>B</p>\n</>\n"
    state = make_state(original)
    assert len(state.segments) == 2
    s0, s1 = state.segments
    # "y = 2\n" sits between the two fragments — offsets should map 1:1 with an accumulated delta
    gap_trans = s1.trans_start - s0.trans_end
    gap_orig = s1.orig_start - s0.orig_end
    assert gap_trans == gap_orig  # passthrough region is the same length


# --- on_from_editor ---

def test_did_open_transpiles_text(interceptor):
    result = asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    assert result is not None
    assert result["params"]["textDocument"]["text"].startswith(IMPORT_PREFIX)


def test_did_open_preserves_uri(interceptor):
    result = asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    assert result is not None
    assert result["params"]["textDocument"]["uri"] == URI


def test_did_open_stores_state(interceptor):
    asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    assert URI in interceptor._states


def test_did_change_updates_state(interceptor):
    asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    asyncio.run(interceptor.on_from_editor(did_change(URI, "x = 2\n")))
    assert interceptor._states[URI].original == "x = 2\n"


def test_did_change_transpiles_new_text(interceptor):
    asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    result = asyncio.run(interceptor.on_from_editor(did_change(URI, "y = 99\n")))
    assert result is not None
    text = result["params"]["contentChanges"][-1]["text"]
    assert "y = 99" in text


def test_did_close_removes_state(interceptor):
    asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))
    asyncio.run(interceptor.on_from_editor(did_close(URI)))
    assert URI not in interceptor._states


def test_unhandled_message_passes_through(interceptor):
    msg = {"method": "initialized", "params": {}}
    result = asyncio.run(interceptor.on_from_editor(msg))
    assert result == msg


# --- on_from_pyright ---

def test_non_diagnostic_message_passes_through(interceptor):
    msg = {"method": "window/logMessage", "params": {"message": "hello"}}
    assert asyncio.run(interceptor.on_from_pyright(msg)) == msg


def test_diagnostics_for_unknown_uri_pass_through(interceptor):
    msg = publish_diagnostics("file:///unknown.py", [])
    assert asyncio.run(interceptor.on_from_pyright(msg)) == msg


def test_diagnostic_inside_fragment_is_dropped(interceptor):
    original = "return <>\n    <h1>Hi</h1>\n</>"
    asyncio.run(interceptor.on_from_editor(did_open(URI, original)))
    state = interceptor._states[URI]
    seg = state.segments[0]

    line, char = pos_in(state.transpiled, seg.trans_start + 1)
    diag = diag_at(state.transpiled, line, char, line, char + 1)
    result = asyncio.run(interceptor.on_from_pyright(publish_diagnostics(URI, [diag])))
    assert result is not None
    assert result["params"]["diagnostics"] == []


def test_diagnostic_in_passthrough_is_remapped(interceptor):
    original = "x = bad_call()\nreturn <>\n    <h1>Hi</h1>\n</>\n"
    asyncio.run(interceptor.on_from_editor(did_open(URI, original)))
    state = interceptor._states[URI]

    # "x = bad_call()" is line 0 in original, line 1 in transpiled (after import)
    diag = diag_at(state.transpiled, 1, 0, 1, 14)
    result = asyncio.run(interceptor.on_from_pyright(publish_diagnostics(URI, [diag])))
    assert result is not None
    mapped = result["params"]["diagnostics"]
    assert len(mapped) == 1
    assert mapped[0]["range"]["start"] == {"line": 0, "character": 0}
    assert mapped[0]["range"]["end"] == {"line": 0, "character": 14}


def test_mixed_diagnostics_drops_fragment_keeps_passthrough(interceptor):
    original = "x = bad_call()\nreturn <>\n    <h1>Hi</h1>\n</>\n"
    asyncio.run(interceptor.on_from_editor(did_open(URI, original)))
    state = interceptor._states[URI]
    seg = state.segments[0]

    passthrough_diag = diag_at(state.transpiled, 1, 0, 1, 14)
    frag_line, frag_char = pos_in(state.transpiled, seg.trans_start + 1)
    fragment_diag = diag_at(state.transpiled, frag_line, frag_char, frag_line, frag_char + 1)

    result = asyncio.run(interceptor.on_from_pyright(publish_diagnostics(URI, [passthrough_diag, fragment_diag])))
    assert result is not None
    assert len(result["params"]["diagnostics"]) == 1
    assert result["params"]["diagnostics"][0]["range"]["start"]["line"] == 0


# --- integration: open → edit → diagnostics ---

def test_full_pipeline_open_then_diagnostics(interceptor):
    original = "x = bad_call()\nreturn <>\n    <h1>Hi</h1>\n</>\n"

    open_result = asyncio.run(interceptor.on_from_editor(did_open(URI, original)))
    assert open_result is not None
    transpiled = open_result["params"]["textDocument"]["text"]
    assert transpiled.startswith(IMPORT_PREFIX)

    state = interceptor._states[URI]
    seg = state.segments[0]

    passthrough_diag = diag_at(transpiled, 1, 0, 1, 14)
    frag_line, frag_char = pos_in(transpiled, seg.trans_start + 1)
    fragment_diag = diag_at(transpiled, frag_line, frag_char, frag_line, frag_char + 1)

    diag_result = asyncio.run(interceptor.on_from_pyright(publish_diagnostics(URI, [passthrough_diag, fragment_diag])))
    assert diag_result is not None
    kept = diag_result["params"]["diagnostics"]
    assert len(kept) == 1
    assert kept[0]["range"]["start"] == {"line": 0, "character": 0}


def test_full_pipeline_edit_updates_mapping(interceptor):
    asyncio.run(interceptor.on_from_editor(did_open(URI, "x = 1\n")))

    new_source = "y = bad()\nreturn <>\n    <p>Hi</p>\n</>\n"
    asyncio.run(interceptor.on_from_editor(did_change(URI, new_source)))

    state = interceptor._states[URI]
    assert state.original == new_source

    passthrough_diag = diag_at(state.transpiled, 1, 0, 1, 9)
    result = asyncio.run(interceptor.on_from_pyright(publish_diagnostics(URI, [passthrough_diag])))
    assert result is not None
    assert result["params"]["diagnostics"][0]["range"]["start"]["line"] == 0
