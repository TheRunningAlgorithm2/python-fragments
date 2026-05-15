from dataclasses import dataclass

from fragments.lsp.source_map import IMPORT_PREFIX, Segment, transpile_with_map


@dataclass
class _FileState:
    original: str
    transpiled: str
    segments: list[Segment]


def _to_offset(source: str, line: int, character: int) -> int:
    lines = source.split("\n")
    return sum(len(lines[i]) + 1 for i in range(line)) + character


def _to_position(source: str, offset: int) -> dict:
    lines = source[:offset].split("\n")
    return {"line": len(lines) - 1, "character": len(lines[-1])}


def _trans_to_orig(trans_offset: int, state: _FileState) -> int | None:
    """Map a char offset in the transpiled source to the original. Returns None if inside a fragment."""
    prefix = len(IMPORT_PREFIX)
    if trans_offset < prefix:
        return None

    orig_cursor = 0
    trans_cursor = prefix

    for seg in state.segments:
        gap = seg.trans_start - trans_cursor
        if trans_offset < trans_cursor + gap:
            return orig_cursor + (trans_offset - trans_cursor)
        orig_cursor += gap
        trans_cursor += gap

        frag_trans = seg.trans_end - seg.trans_start
        if trans_offset < trans_cursor + frag_trans:
            return None
        orig_cursor += seg.orig_end - seg.orig_start
        trans_cursor += frag_trans

    return orig_cursor + (trans_offset - trans_cursor)


def _map_diagnostic(diag: dict, state: _FileState) -> dict | None:
    start = diag["range"]["start"]
    orig_start = _trans_to_orig(_to_offset(state.transpiled, start["line"], start["character"]), state)
    if orig_start is None:
        return None

    end = diag["range"]["end"]
    orig_end = _trans_to_orig(_to_offset(state.transpiled, end["line"], end["character"]), state)
    if orig_end is None:
        return None

    return {
        **diag,
        "range": {
            "start": _to_position(state.original, orig_start),
            "end": _to_position(state.original, orig_end),
        },
    }


class Interceptor:
    def __init__(self) -> None:
        self._states: dict[str, _FileState] = {}

    async def on_from_editor(self, msg: dict) -> dict | None:
        method = msg.get("method")

        if method == "textDocument/didOpen":
            params = msg["params"]
            doc = params["textDocument"]
            uri = doc["uri"]
            original = doc["text"]
            transpiled, segments = transpile_with_map(original)
            self._states[uri] = _FileState(original, transpiled, segments)
            return {**msg, "params": {**params, "textDocument": {**doc, "text": transpiled}}}

        if method == "textDocument/didChange":
            params = msg["params"]
            uri = params["textDocument"]["uri"]
            changes = params["contentChanges"]
            original = changes[-1]["text"]
            transpiled, segments = transpile_with_map(original)
            self._states[uri] = _FileState(original, transpiled, segments)
            return {**msg, "params": {**params, "contentChanges": [{**changes[-1], "text": transpiled}]}}

        if method == "textDocument/didClose":
            self._states.pop(msg["params"]["textDocument"]["uri"], None)
            return msg

        return msg

    async def on_from_pyright(self, msg: dict) -> dict | None:
        if msg.get("method") != "textDocument/publishDiagnostics":
            return msg

        params = msg["params"]
        state = self._states.get(params["uri"])
        if state is None:
            return msg

        mapped = [_map_diagnostic(d, state) for d in params["diagnostics"]]
        return {**msg, "params": {**params, "diagnostics": [d for d in mapped if d is not None]}}
