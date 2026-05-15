from __future__ import annotations

import asyncio
import bisect
import sys
from dataclasses import dataclass, field

from lsprotocol import types
from lsprotocol.converters import get_converter
from pygls.server import LanguageServer

from fragments.lsp.pyright import PyrightClient
from fragments.lsp.source_map import (
    Segment,
    orig_to_trans,
    trans_to_orig,
    transpile_with_map,
)


def _build_line_starts(source: str) -> list[int]:
    starts = [0]
    for i, c in enumerate(source):
        if c == "\n":
            starts.append(i + 1)
    return starts


def _to_offset(line_starts: list[int], line: int, char: int) -> int:
    return line_starts[line] + char


def _to_position(line_starts: list[int], offset: int) -> dict:
    line = bisect.bisect_right(line_starts, offset) - 1
    return {"line": line, "character": offset - line_starts[line]}


@dataclass
class _FileState:
    original: str
    transpiled: str
    segments: list[Segment]
    orig_line_starts: list[int] = field(init=False)
    trans_line_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.orig_line_starts = _build_line_starts(self.original)
        self.trans_line_starts = _build_line_starts(self.transpiled)


class FragmentsServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(
            "fragments-lsp",
            "v0.1",
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )
        self._pyright: PyrightClient | None = None
        self._files: dict[str, _FileState] = {}

    def _on_pyright_notification(self, msg: dict) -> None:
        if msg.get("method") == "textDocument/publishDiagnostics":
            asyncio.ensure_future(self._publish_diagnostics(msg["params"]))

    async def _on_pyright_request(self, msg: dict) -> object:
        if msg["method"] == "workspace/configuration":
            items = msg["params"]["items"]
            editor_configs = await self.get_configuration_async(
                types.ConfigurationParams(items=[
                    types.ConfigurationItem(scope_uri=item.get("scopeUri"), section=item.get("section", ""))
                    for item in items
                ])
            )
            result = []
            for item, config in zip(items, editor_configs):
                if item.get("section") == "python":
                    config = {**(config or {}), "pythonPath": sys.executable, "defaultInterpreterPath": sys.executable}
                result.append(config)
            return result
        return None

    async def _publish_diagnostics(self, params: dict) -> None:
        uri = params["uri"]
        state = self._files.get(uri)
        diagnostics = []
        for d in params["diagnostics"]:
            if state is not None:
                d = _map_diagnostic(d, state)
                if d is None:
                    continue
            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(
                            line=d["range"]["start"]["line"],
                            character=d["range"]["start"]["character"],
                        ),
                        end=types.Position(
                            line=d["range"]["end"]["line"],
                            character=d["range"]["end"]["character"],
                        ),
                    ),
                    message=d["message"],
                    severity=types.DiagnosticSeverity(d["severity"]) if d.get("severity") is not None else None,
                    code=d.get("code"),
                    source=d.get("source"),
                )
            )
        self.publish_diagnostics(uri, diagnostics)


server = FragmentsServer()


def _map_diagnostic(diag: dict, state: _FileState) -> dict | None:
    start = diag["range"]["start"]
    orig_start = trans_to_orig(
        _to_offset(state.trans_line_starts, start["line"], start["character"]), state.segments
    )
    if orig_start is None:
        return None

    end = diag["range"]["end"]
    orig_end = trans_to_orig(
        _to_offset(state.trans_line_starts, end["line"], end["character"]), state.segments
    )
    if orig_end is None:
        return None

    return {
        **diag,
        "range": {
            "start": _to_position(state.orig_line_starts, orig_start),
            "end": _to_position(state.orig_line_starts, orig_end),
        },
    }


def _remap_range(range_: dict, state: _FileState) -> dict | None:
    start = trans_to_orig(
        _to_offset(state.trans_line_starts, range_["start"]["line"], range_["start"]["character"]),
        state.segments,
    )
    end = trans_to_orig(
        _to_offset(state.trans_line_starts, range_["end"]["line"], range_["end"]["character"]),
        state.segments,
    )
    if start is None or end is None:
        return None
    return {
        "start": _to_position(state.orig_line_starts, start),
        "end": _to_position(state.orig_line_starts, end),
    }


_converter = get_converter()


def _remap_completion_items(items: list, state: _FileState) -> list:
    out = []
    for item in items:
        item = dict(item)
        if "textEdit" in item:
            te = item["textEdit"]
            if "range" in te:
                r = _remap_range(te["range"], state)
                if r is None:
                    continue
                item["textEdit"] = {**te, "range": r}
            else:
                insert = _remap_range(te["insert"], state)
                replace = _remap_range(te["replace"], state)
                if insert is None or replace is None:
                    continue
                item["textEdit"] = {**te, "insert": insert, "replace": replace}
        if "additionalTextEdits" in item:
            item["additionalTextEdits"] = [
                {**e, "range": r}
                for e in item["additionalTextEdits"]
                if (r := _remap_range(e["range"], state)) is not None
            ]
        out.append(item)
    return out


@server.feature(types.INITIALIZED)
async def initialized(ls: FragmentsServer, _params: types.InitializedParams) -> None:
    root_uri = ls.workspace.root_uri
    workspace_folders = [
        {"uri": f.uri, "name": f.name} for f in ls.workspace.folders.values()
    ]

    pyright = PyrightClient(ls._on_pyright_notification, ls._on_pyright_request)
    ls._pyright = pyright
    await pyright.start()
    await pyright.request(
        "initialize",
        {
            "processId": None,
            "rootUri": root_uri,
            "workspaceFolders": workspace_folders or None,
            "capabilities": {
                    "workspace": {"configuration": True},
                    "textDocument": {
                        "hover": {"contentFormat": ["markdown", "plaintext"]},
                        "semanticTokens": {
                            "requests": {"full": True},
                            "tokenTypes": _TOKEN_TYPES,
                            "tokenModifiers": _TOKEN_MODIFIERS,
                            "formats": ["relative"],
                        },
                    },
                },
        },
    )
    pyright.notify("initialized", {})


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: FragmentsServer, params: types.DidOpenTextDocumentParams) -> None:
    doc = params.text_document
    transpiled, segments = transpile_with_map(doc.text)
    ls._files[doc.uri] = _FileState(doc.text, transpiled, segments)

    if ls._pyright:
        ls._pyright.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": doc.uri,
                    "languageId": doc.language_id,
                    "version": doc.version,
                    "text": transpiled,
                }
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: FragmentsServer, params: types.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.content_changes[-1].text
    transpiled, segments = transpile_with_map(text)
    ls._files[uri] = _FileState(text, transpiled, segments)

    if ls._pyright:
        ls._pyright.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": params.text_document.version},
                "contentChanges": [{"text": transpiled}],
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: FragmentsServer, params: types.DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    ls._files.pop(uri, None)

    if ls._pyright:
        ls._pyright.notify("textDocument/didClose", {"textDocument": {"uri": uri}})


@server.feature(types.TEXT_DOCUMENT_HOVER)
async def hover(ls: FragmentsServer, params: types.HoverParams) -> types.Hover | None:
    if ls._pyright is None:
        return None

    uri = params.text_document.uri
    state = ls._files.get(uri)
    if state is None:
        return None

    pos = params.position
    orig_offset = _to_offset(state.orig_line_starts, pos.line, pos.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)
    result = await ls._pyright.request(
        "textDocument/hover",
        {"textDocument": {"uri": uri}, "position": trans_pos},
    )

    hover_result = result.get("result")
    if not hover_result:
        return None

    range_ = hover_result.get("range")
    if range_ is not None:
        remapped = _remap_range(range_, state)
        hover_result = (
            {**hover_result, "range": remapped}
            if remapped is not None
            else {k: v for k, v in hover_result.items() if k != "range"}
        )

    return _converter.structure(hover_result, types.Hover)


@server.feature(types.TEXT_DOCUMENT_COMPLETION, types.CompletionOptions(trigger_characters=["."]))
async def completion(
    ls: FragmentsServer, params: types.CompletionParams
) -> types.CompletionList | None:
    if ls._pyright is None:
        return None

    uri = params.text_document.uri
    state = ls._files.get(uri)
    if state is None:
        return None

    pos = params.position
    orig_offset = _to_offset(state.orig_line_starts, pos.line, pos.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)

    context = None
    if params.context is not None:
        context = {
            "triggerKind": params.context.trigger_kind.value,
            "triggerCharacter": params.context.trigger_character,
        }

    result = await ls._pyright.request(
        "textDocument/completion",
        {"textDocument": {"uri": uri}, "position": trans_pos, "context": context},
    )

    completion_result = result.get("result")
    if not completion_result:
        return None

    if isinstance(completion_result, list):
        raw_items, is_incomplete = completion_result, False
    else:
        raw_items = completion_result.get("items", [])
        is_incomplete = completion_result.get("isIncomplete", False)

    items = [_converter.structure(i, types.CompletionItem) for i in _remap_completion_items(raw_items, state)]
    return types.CompletionList(is_incomplete=is_incomplete, items=items)


_TOKEN_TYPES = [
    "namespace", "type", "class", "enum", "typeParameter", "parameter",
    "variable", "property", "enumMember", "function", "method", "keyword",
    "decorator", "selfParameter", "clsParameter",
]
_TOKEN_MODIFIERS = [
    "declaration", "definition", "readonly", "static", "async",
    "defaultLibrary", "builtin", "classMember", "parameter",
]


@server.feature(
    types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    types.SemanticTokensLegend(token_types=_TOKEN_TYPES, token_modifiers=_TOKEN_MODIFIERS),
)
async def semantic_tokens_full(
    ls: FragmentsServer, params: types.SemanticTokensParams
) -> types.SemanticTokens:
    state = ls._files.get(params.text_document.uri)
    if state is None or ls._pyright is None:
        return types.SemanticTokens(data=[])

    result = await ls._pyright.request(
        "textDocument/semanticTokens/full",
        {"textDocument": {"uri": params.text_document.uri}},
    )
    raw = (result.get("result") or {}).get("data") or []

    out: list[int] = []
    trans_line = trans_char = prev_line = prev_char = 0
    for i in range(0, len(raw), 5):
        dl, dc, length, tt, tm = raw[i : i + 5]
        trans_line += dl
        trans_char = dc if dl > 0 else trans_char + dc
        orig_offset = trans_to_orig(_to_offset(state.trans_line_starts, trans_line, trans_char), state.segments)
        if orig_offset is None:
            continue
        orig_pos = _to_position(state.orig_line_starts, orig_offset)
        line, char = orig_pos["line"], orig_pos["character"]
        dl = line - prev_line
        out.extend([dl, char if dl > 0 else char - prev_char, length, tt, tm])
        prev_line, prev_char = line, char

    return types.SemanticTokens(data=out)


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
