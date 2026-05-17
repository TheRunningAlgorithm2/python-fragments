from __future__ import annotations

import asyncio
import bisect
import sys
from dataclasses import dataclass, field
from typing import Any

from lsprotocol import types
from lsprotocol.converters import get_converter
from pygls.server import LanguageServer

from fragments import grammar
from fragments.ast_nodes import ASTHTMLElement, ASTHTMLText, ASTInterpolation, ASTModule, ASTPython
from fragments.lsp.pyright import PyrightClient
from fragments.source import Source

_converter = get_converter()


def _build_line_starts(source: str) -> list[int]:
    starts = [0]
    for i, character in enumerate(source):
        if character == "\n":
            starts.append(i + 1)
    return starts


def _position_to_offset(line_starts: list[int], line: int, character: int) -> int:
    return line_starts[line] + character


def _offset_to_position(line_starts: list[int], offset: int) -> types.Position:
    line = bisect.bisect_right(line_starts, offset) - 1
    return types.Position(line=line, character=offset - line_starts[line])


@dataclass
class _FileState:
    original: str
    transpiled: str
    module: ASTModule
    original_line_starts: list[int] = field(init=False)
    transpiled_line_starts: list[int] = field(init=False)

    def __post_init__(self) -> None:
        self.original_line_starts = _build_line_starts(self.original)
        self.transpiled_line_starts = _build_line_starts(self.transpiled)

    def _interpolation_expression_start(self, interpolation: ASTInterpolation) -> int:
        after = self.original[interpolation.source_start + 2 :]
        return interpolation.source_start + 2 + (len(after) - len(after.lstrip()))

    def _original_offset_to_transpiled_offset(self, original_offset: int) -> int | None:
        for child in self.module.children:
            if isinstance(child, ASTPython):
                if child.source_start <= original_offset < child.source_end:
                    return child.transpiled_start + (original_offset - child.source_start)
            elif child.source_start <= original_offset < child.source_end:
                return self._original_offset_in_nodes(original_offset, child.children)
        return None

    def _original_offset_in_nodes(self, original_offset: int, nodes: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation]) -> int | None:
        for node in nodes:
            if not (node.source_start <= original_offset < node.source_end):
                continue
            if isinstance(node, ASTInterpolation):
                expression_start = self._interpolation_expression_start(node)
                return node.transpiled_start + (original_offset - expression_start) if original_offset >= expression_start else None
            if isinstance(node, ASTHTMLElement):
                for interpolation in [node.if_attribute, node.for_attribute, *(a.interpolation for a in node.attributes.values())]:
                    if interpolation is not None and interpolation.source_start <= original_offset < interpolation.source_end:
                        expression_start = self._interpolation_expression_start(interpolation)
                        return interpolation.transpiled_start + (original_offset - expression_start) if original_offset >= expression_start else None
                return self._original_offset_in_nodes(original_offset, list(node.children))
        return None

    def _transpiled_offset_to_original_offset(self, transpiled_offset: int) -> int | None:
        for child in self.module.children:
            if isinstance(child, ASTPython):
                if child.transpiled_start <= transpiled_offset < child.transpiled_end:
                    return child.source_start + (transpiled_offset - child.transpiled_start)
            elif child.transpiled_start <= transpiled_offset < child.transpiled_end:
                return self._transpiled_offset_in_nodes(transpiled_offset, child.children)
        return None

    def _transpiled_offset_in_nodes(self, transpiled_offset: int, nodes: list[ASTHTMLElement | ASTHTMLText | ASTInterpolation]) -> int | None:
        for node in nodes:
            if not (node.transpiled_start <= transpiled_offset < node.transpiled_end):
                continue
            if isinstance(node, ASTInterpolation):
                return self._interpolation_expression_start(node) + (transpiled_offset - node.transpiled_start)
            if isinstance(node, ASTHTMLElement):
                for interpolation in [node.if_attribute, node.for_attribute, *(a.interpolation for a in node.attributes.values())]:
                    if interpolation is not None and interpolation.transpiled_start <= transpiled_offset < interpolation.transpiled_end:
                        return self._interpolation_expression_start(interpolation) + (transpiled_offset - interpolation.transpiled_start)
                return self._transpiled_offset_in_nodes(transpiled_offset, list(node.children))
        return None

    def original_to_transpiled_position(self, position: types.Position) -> types.Position | None:
        original_offset = _position_to_offset(self.original_line_starts, position.line, position.character)
        transpiled_offset = self._original_offset_to_transpiled_offset(original_offset)
        if transpiled_offset is None:
            return None
        return _offset_to_position(self.transpiled_line_starts, transpiled_offset)

    def transpiled_to_original_position(self, position: types.Position) -> types.Position | None:
        transpiled_offset = _position_to_offset(self.transpiled_line_starts, position.line, position.character)
        original_offset = self._transpiled_offset_to_original_offset(transpiled_offset)
        if original_offset is None:
            return None
        return _offset_to_position(self.original_line_starts, original_offset)

    def transpiled_to_original_range(self, range_: types.Range) -> types.Range | None:
        start = self.transpiled_to_original_position(range_.start)
        end = self.transpiled_to_original_position(range_.end)
        if start is None or end is None:
            return None
        return types.Range(start=start, end=end)


class FragmentsServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(
            "fragments-lsp",
            "v0.1",
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )
        self._pyright: PyrightClient | None = None
        self._files: dict[str, _FileState] = {}

    def _on_pyright_notification(self, message: dict[str, Any]) -> None:
        if message.get("method") == "textDocument/publishDiagnostics":
            _ = asyncio.ensure_future(self._publish_diagnostics(message["params"]))

    async def _on_pyright_request(self, message: dict[str, Any]) -> object:
        if message["method"] == "workspace/configuration":
            items = message["params"]["items"]
            editor_configs = await self.get_configuration_async(
                types.ConfigurationParams(items=[types.ConfigurationItem(scope_uri=item.get("scopeUri"), section=item.get("section", "")) for item in items])
            )
            result: list[dict[str, object] | None] = []
            for item, config in zip(items, editor_configs):
                if item.get("section") == "python":
                    config = {**(config or {}), "pythonPath": sys.executable, "defaultInterpreterPath": sys.executable}
                result.append(config)  # type: ignore[arg-type]
            return result
        return None

    async def _publish_diagnostics(self, params: dict[str, Any]) -> None:
        uri = params["uri"]
        state = self._files.get(uri)
        diagnostics: list[types.Diagnostic] = []

        for raw_diagnostic in params["diagnostics"]:
            diagnostic = _converter.structure(raw_diagnostic, types.Diagnostic)
            if state is not None:
                remapped_range = state.transpiled_to_original_range(diagnostic.range)
                if remapped_range is None:
                    continue
                diagnostic = types.Diagnostic(
                    range=remapped_range,
                    message=diagnostic.message,
                    severity=diagnostic.severity,
                    code=diagnostic.code,
                    source=diagnostic.source,
                )
            diagnostics.append(diagnostic)

        self.publish_diagnostics(uri, diagnostics)


server = FragmentsServer()


def _remap_text_edits(text_edits: list[types.TextEdit], state: _FileState) -> list[types.TextEdit]:
    result: list[types.TextEdit] = []
    for edit in text_edits:
        remapped = state.transpiled_to_original_range(edit.range)
        if remapped is not None:
            edit.range = remapped
            result.append(edit)
    return result


@server.feature(types.INITIALIZED)
async def initialized(language_server: FragmentsServer, _params: types.InitializedParams) -> None:
    root_uri = language_server.workspace.root_uri
    workspace_folders = [{"uri": folder.uri, "name": folder.name} for folder in language_server.workspace.folders.values()]

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
    document = params.text_document
    _, module = grammar.expect_module(Source.from_string(document.text))
    module.transpile()
    language_server._files[document.uri] = _FileState(document.text, module.transpiled_content, module)

    if language_server._pyright:
        language_server._pyright.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": document.uri,
                    "languageId": document.language_id,
                    "version": document.version,
                    "text": module.transpiled_content,
                }
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(language_server: FragmentsServer, params: types.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.content_changes[-1].text
    _, module = grammar.expect_module(Source.from_string(text))
    module.transpile()
    language_server._files[uri] = _FileState(text, module.transpiled_content, module)

    if language_server._pyright:
        language_server._pyright.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": params.text_document.version},
                "contentChanges": [{"text": module.transpiled_content}],
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
    state = language_server._files.get(params.text_document.uri)
    if state is None:
        return None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    result = await language_server._pyright.request(
        "textDocument/hover",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
        },
    )

    raw_hover = result.get("result")
    if not raw_hover:
        return None

    hover_response = _converter.structure(raw_hover, types.Hover)
    if hover_response.range is not None:
        hover_response.range = state.transpiled_to_original_range(hover_response.range)
    return hover_response


@server.feature(types.TEXT_DOCUMENT_COMPLETION, types.CompletionOptions(trigger_characters=["."]))
async def completion(language_server: FragmentsServer, params: types.CompletionParams) -> types.CompletionList | None:
    if language_server._pyright is None:
        return None
    state = language_server._files.get(params.text_document.uri)
    if state is None:
        return None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    context = None
    if params.context is not None:
        context = {
            "triggerKind": params.context.trigger_kind.value,
            "triggerCharacter": params.context.trigger_character,
        }

    result = await language_server._pyright.request(
        "textDocument/completion",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
            "context": context,
        },
    )

    raw_result = result.get("result")
    if not raw_result:
        return None

    if isinstance(raw_result, list):
        raw_items, is_incomplete = raw_result, False
    else:
        raw_items = raw_result.get("items", [])
        is_incomplete = raw_result.get("isIncomplete", False)

    remapped_items: list[types.CompletionItem] = []
    for item in _converter.structure(raw_items, list[types.CompletionItem]):
        if item.text_edit is not None:
            if isinstance(item.text_edit, types.InsertReplaceEdit):
                insert = state.transpiled_to_original_range(item.text_edit.insert)
                replace = state.transpiled_to_original_range(item.text_edit.replace)
                if insert is None or replace is None:
                    continue
                item.text_edit.insert = insert
                item.text_edit.replace = replace
            else:
                remapped = state.transpiled_to_original_range(item.text_edit.range)
                if remapped is None:
                    continue
                item.text_edit.range = remapped
        if item.additional_text_edits:
            item.additional_text_edits = _remap_text_edits(item.additional_text_edits, state)
        remapped_items.append(item)

    return types.CompletionList(is_incomplete=is_incomplete, items=remapped_items)


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
async def definition(language_server: FragmentsServer, params: types.DefinitionParams) -> list[types.Location] | None:
    if language_server._pyright is None:
        return None
    state = language_server._files.get(params.text_document.uri)
    if state is None:
        return None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    result = await language_server._pyright.request(
        "textDocument/definition",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
        },
    )

    raw_result = result.get("result")
    if not raw_result:
        return None

    raw_locations = [raw_result] if isinstance(raw_result, dict) else raw_result
    locations: list[types.Location] = []
    for location in _converter.structure(raw_locations, list[types.Location]):
        target_state = language_server._files.get(location.uri)
        if target_state is not None:
            remapped = target_state.transpiled_to_original_range(location.range)
            if remapped is None:
                continue
            location.range = remapped
        locations.append(location)

    return locations or None


@server.feature(types.TEXT_DOCUMENT_PREPARE_RENAME)
async def prepare_rename(language_server: FragmentsServer, params: types.PrepareRenameParams) -> types.Range | None:
    if language_server._pyright is None:
        return None
    state = language_server._files.get(params.text_document.uri)
    if state is None:
        return None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    result = await language_server._pyright.request(
        "textDocument/prepareRename",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
        },
    )

    raw_result = result.get("result")
    if not raw_result:
        return None

    # Normalise to a plain Range (discard placeholder / defaultBehavior variants)
    range_dict = raw_result.get("range", raw_result) if isinstance(raw_result, dict) else raw_result
    if not isinstance(range_dict, dict) or "start" not in range_dict:
        return None

    return state.transpiled_to_original_range(_converter.structure(range_dict, types.Range))


@server.feature(types.TEXT_DOCUMENT_RENAME)
async def rename(language_server: FragmentsServer, params: types.RenameParams) -> types.WorkspaceEdit | None:
    if language_server._pyright is None:
        return None
    state = language_server._files.get(params.text_document.uri)
    if state is None:
        return None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    result = await language_server._pyright.request(
        "textDocument/rename",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
            "newName": params.new_name,
        },
    )

    raw_result = result.get("result")
    if not raw_result:
        return None

    edit = _converter.structure(raw_result, types.WorkspaceEdit)

    if edit.changes:
        for uri in list(edit.changes):
            file_state = language_server._files.get(uri)
            if file_state is not None:
                edit.changes[uri] = _remap_text_edits(edit.changes[uri], file_state)

    if edit.document_changes:
        for change in edit.document_changes:
            if isinstance(change, types.TextDocumentEdit):
                file_state = language_server._files.get(change.text_document.uri)
                if file_state is not None:
                    remapped_edits: list[types.TextEdit | types.AnnotatedTextEdit] = []
                    for text_edit in change.edits:
                        remapped = file_state.transpiled_to_original_range(text_edit.range)
                        if remapped is not None:
                            text_edit.range = remapped
                            remapped_edits.append(text_edit)
                    change.edits = remapped_edits

    return edit


_TOKEN_TYPES = ["namespace", "type", "class", "enum", "typeParameter", "parameter", "variable", "property", "enumMember", "function", "method", "keyword", "decorator", "selfParameter", "clsParameter"]
_TOKEN_MODIFIERS = ["declaration", "definition", "readonly", "static", "async", "defaultLibrary", "builtin", "classMember", "parameter"]


@server.feature(
    types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    types.SemanticTokensLegend(token_types=_TOKEN_TYPES, token_modifiers=_TOKEN_MODIFIERS),
)
async def semantic_tokens_full(language_server: FragmentsServer, params: types.SemanticTokensParams) -> types.SemanticTokens:
    state = language_server._files.get(params.text_document.uri)
    if state is None or language_server._pyright is None:
        return types.SemanticTokens(data=[])

    result = await language_server._pyright.request(
        "textDocument/semanticTokens/full",
        {"textDocument": {"uri": params.text_document.uri}},
    )
    raw_data = (result.get("result") or {}).get("data") or []

    output: list[int] = []
    transpiled_line = transpiled_character = previous_line = previous_character = 0
    for i in range(0, len(raw_data), 5):
        delta_line, delta_character, length, token_type, token_modifiers = raw_data[i : i + 5]
        transpiled_line += delta_line
        transpiled_character = delta_character if delta_line > 0 else transpiled_character + delta_character
        if transpiled_line >= len(state.transpiled_line_starts):
            continue
        original_position = state.transpiled_to_original_position(types.Position(line=transpiled_line, character=transpiled_character))
        if original_position is None:
            continue
        line, character = original_position.line, original_position.character
        delta_line = line - previous_line
        output.extend([delta_line, character if delta_line > 0 else character - previous_character, length, token_type, token_modifiers])
        previous_line, previous_character = line, character

    return types.SemanticTokens(data=output)


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
