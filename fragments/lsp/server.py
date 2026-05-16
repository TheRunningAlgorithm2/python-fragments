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
    for i, character in enumerate(source):
        if character == "\n":
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

    def _on_pyright_notification(self, message: dict) -> None:
        if message.get("method") == "textDocument/publishDiagnostics":
            asyncio.ensure_future(self._publish_diagnostics(message["params"]))

    async def _on_pyright_request(self, message: dict) -> object:
        if message["method"] == "workspace/configuration":
            items = message["params"]["items"]
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
        for diagnostic in params["diagnostics"]:
            if state is not None:
                diagnostic = _map_diagnostic(diagnostic, state)
                if diagnostic is None:
                    continue
            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(
                            line=diagnostic["range"]["start"]["line"],
                            character=diagnostic["range"]["start"]["character"],
                        ),
                        end=types.Position(
                            line=diagnostic["range"]["end"]["line"],
                            character=diagnostic["range"]["end"]["character"],
                        ),
                    ),
                    message=diagnostic["message"],
                    severity=types.DiagnosticSeverity(diagnostic["severity"]) if diagnostic.get("severity") is not None else None,
                    code=diagnostic.get("code"),
                    source=diagnostic.get("source"),
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


def _remap_text_edits(text_edits: list[dict], state: _FileState) -> list[dict]:
    return [
        {**text_edit, "range": remapped}
        for text_edit in text_edits
        if (remapped := _remap_range(text_edit["range"], state)) is not None
    ]


def _remap_workspace_edit(edit: dict, files: dict[str, _FileState]) -> dict:
    result = dict(edit)

    if changes := edit.get("changes"):
        result["changes"] = {
            uri: _remap_text_edits(text_edits, state) if (state := files.get(uri)) is not None else text_edits
            for uri, text_edits in changes.items()
        }

    if document_changes := edit.get("documentChanges"):
        remapped_doc_changes = []
        for doc_edit in document_changes:
            if "kind" in doc_edit:
                remapped_doc_changes.append(doc_edit)
                continue
            uri = doc_edit["textDocument"]["uri"]
            state = files.get(uri)
            edits = _remap_text_edits(doc_edit["edits"], state) if state is not None else doc_edit["edits"]
            remapped_doc_changes.append({**doc_edit, "edits": edits})
        result["documentChanges"] = remapped_doc_changes

    return result


def _remap_completion_items(items: list[dict], state: _FileState) -> list[dict]:
    output = []
    for item in items:
        item = dict(item)
        if "textEdit" in item:
            text_edit = item["textEdit"]
            if "range" in text_edit:
                remapped_range = _remap_range(text_edit["range"], state)
                if remapped_range is None:
                    continue
                item["textEdit"] = {**text_edit, "range": remapped_range}
            else:
                insert = _remap_range(text_edit["insert"], state)
                replace = _remap_range(text_edit["replace"], state)
                if insert is None or replace is None:
                    continue
                item["textEdit"] = {**text_edit, "insert": insert, "replace": replace}
        if "additionalTextEdits" in item:
            item["additionalTextEdits"] = [
                {**edit, "range": remapped_range}
                for edit in item["additionalTextEdits"]
                if (remapped_range := _remap_range(edit["range"], state)) is not None
            ]
        output.append(item)
    return output


@server.feature(types.INITIALIZED)
async def initialized(language_server: FragmentsServer, _params: types.InitializedParams) -> None:
    root_uri = language_server.workspace.root_uri
    workspace_folders = [
        {"uri": folder.uri, "name": folder.name} for folder in language_server.workspace.folders.values()
    ]

    pyright = PyrightClient(language_server._on_pyright_notification, language_server._on_pyright_request)
    language_server._pyright = pyright
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
                        "rename": {"prepareSupport": True},
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
def did_open(language_server: FragmentsServer, params: types.DidOpenTextDocumentParams) -> None:
    doc = params.text_document
    transpiled, segments = transpile_with_map(doc.text)
    language_server._files[doc.uri] = _FileState(doc.text, transpiled, segments)

    if language_server._pyright:
        language_server._pyright.notify(
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
def did_change(language_server: FragmentsServer, params: types.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.content_changes[-1].text
    transpiled, segments = transpile_with_map(text)
    language_server._files[uri] = _FileState(text, transpiled, segments)

    if language_server._pyright:
        language_server._pyright.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": params.text_document.version},
                "contentChanges": [{"text": transpiled}],
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(language_server: FragmentsServer, params: types.DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    language_server._files.pop(uri, None)

    if language_server._pyright:
        language_server._pyright.notify("textDocument/didClose", {"textDocument": {"uri": uri}})


@server.feature(types.TEXT_DOCUMENT_HOVER)
async def hover(language_server: FragmentsServer, params: types.HoverParams) -> types.Hover | None:
    if language_server._pyright is None:
        return None

    uri = params.text_document.uri
    state = language_server._files.get(uri)
    if state is None:
        return None

    position = params.position
    orig_offset = _to_offset(state.orig_line_starts, position.line, position.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)
    result = await language_server._pyright.request(
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
    language_server: FragmentsServer, params: types.CompletionParams
) -> types.CompletionList | None:
    if language_server._pyright is None:
        return None

    uri = params.text_document.uri
    state = language_server._files.get(uri)
    if state is None:
        return None

    position = params.position
    orig_offset = _to_offset(state.orig_line_starts, position.line, position.character)
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

    result = await language_server._pyright.request(
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

    items = [_converter.structure(item, types.CompletionItem) for item in _remap_completion_items(raw_items, state)]
    return types.CompletionList(is_incomplete=is_incomplete, items=items)


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
async def definition(
    language_server: FragmentsServer, params: types.DefinitionParams
) -> list[types.Location] | None:
    if language_server._pyright is None:
        return None

    uri = params.text_document.uri
    state = language_server._files.get(uri)
    if state is None:
        return None

    position = params.position
    orig_offset = _to_offset(state.orig_line_starts, position.line, position.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)
    result = await language_server._pyright.request(
        "textDocument/definition",
        {"textDocument": {"uri": uri}, "position": trans_pos},
    )

    definition_result = result.get("result")
    if not definition_result:
        return None

    locations = [definition_result] if isinstance(definition_result, dict) else definition_result

    output = []
    for loc in locations:
        target_state = language_server._files.get(loc["uri"])
        if target_state is not None:
            remapped = _remap_range(loc["range"], target_state)
            if remapped is None:
                continue
            loc = {**loc, "range": remapped}
        output.append(_converter.structure(loc, types.Location))

    return output or None


@server.feature(types.TEXT_DOCUMENT_PREPARE_RENAME)
async def prepare_rename(
    language_server: FragmentsServer, params: types.PrepareRenameParams
) -> types.Range | None:
    if language_server._pyright is None:
        return None

    uri = params.text_document.uri
    state = language_server._files.get(uri)
    if state is None:
        return None

    position = params.position
    orig_offset = _to_offset(state.orig_line_starts, position.line, position.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)
    result = await language_server._pyright.request(
        "textDocument/prepareRename",
        {"textDocument": {"uri": uri}, "position": trans_pos},
    )

    prepare_result = result.get("result")
    if not prepare_result:
        return None

    # Normalise to a plain Range (discard placeholder / defaultBehavior variants)
    range_ = prepare_result.get("range", prepare_result) if isinstance(prepare_result, dict) else prepare_result
    if not isinstance(range_, dict) or "start" not in range_:
        return None

    remapped = _remap_range(range_, state)
    if remapped is None:
        return None

    return _converter.structure(remapped, types.Range)


@server.feature(types.TEXT_DOCUMENT_RENAME)
async def rename(
    language_server: FragmentsServer, params: types.RenameParams
) -> types.WorkspaceEdit | None:
    if language_server._pyright is None:
        return None

    uri = params.text_document.uri
    state = language_server._files.get(uri)
    if state is None:
        return None

    position = params.position
    orig_offset = _to_offset(state.orig_line_starts, position.line, position.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = _to_position(state.trans_line_starts, trans_offset)
    result = await language_server._pyright.request(
        "textDocument/rename",
        {"textDocument": {"uri": uri}, "position": trans_pos, "newName": params.new_name},
    )

    rename_result = result.get("result")
    if not rename_result:
        return None

    return _converter.structure(_remap_workspace_edit(rename_result, language_server._files), types.WorkspaceEdit)


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
    language_server: FragmentsServer, params: types.SemanticTokensParams
) -> types.SemanticTokens:
    state = language_server._files.get(params.text_document.uri)
    if state is None or language_server._pyright is None:
        return types.SemanticTokens(data=[])

    result = await language_server._pyright.request(
        "textDocument/semanticTokens/full",
        {"textDocument": {"uri": params.text_document.uri}},
    )
    raw_data = (result.get("result") or {}).get("data") or []

    output: list[int] = []
    trans_line = trans_char = prev_line = prev_char = 0
    for i in range(0, len(raw_data), 5):
        delta_line, delta_char, length, token_type, token_modifiers = raw_data[i : i + 5]
        trans_line += delta_line
        trans_char = delta_char if delta_line > 0 else trans_char + delta_char
        if trans_line >= len(state.trans_line_starts):
            continue
        orig_offset = trans_to_orig(_to_offset(state.trans_line_starts, trans_line, trans_char), state.segments)
        if orig_offset is None:
            continue
        orig_pos = _to_position(state.orig_line_starts, orig_offset)
        line, char = orig_pos["line"], orig_pos["character"]
        delta_line = line - prev_line
        output.extend([delta_line, char if delta_line > 0 else char - prev_char, length, token_type, token_modifiers])
        prev_line, prev_char = line, char

    return types.SemanticTokens(data=output)


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
