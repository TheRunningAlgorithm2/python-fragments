from __future__ import annotations

from lsprotocol import types

from fragments.lsp.server import FragmentsServer, _converter, _remap_text_edits, server


@server.feature(types.TEXT_DOCUMENT_PREPARE_RENAME)
async def prepare_rename(language_server: FragmentsServer, params: types.PrepareRenameParams) -> types.Range | None:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return None
    state = language_server._files[params.text_document.uri]

    if state is None:
        result = await language_server._pyright.request(
            "textDocument/prepareRename",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": params.position.line, "character": params.position.character},
            },
        )
        raw_result = result.get("result")
        if not raw_result:
            return None
        range_dict = raw_result.get("range", raw_result) if isinstance(raw_result, dict) else raw_result
        if not isinstance(range_dict, dict) or "start" not in range_dict:
            return None
        return _converter.structure(range_dict, types.Range)

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

    range_dict = raw_result.get("range", raw_result) if isinstance(raw_result, dict) else raw_result
    if not isinstance(range_dict, dict) or "start" not in range_dict:
        return None

    return state.transpiled_to_original_range(_converter.structure(range_dict, types.Range))


@server.feature(types.TEXT_DOCUMENT_RENAME)
async def rename(language_server: FragmentsServer, params: types.RenameParams) -> types.WorkspaceEdit | None:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return None
    state = language_server._files[params.text_document.uri]

    if state is None:
        result = await language_server._pyright.request(
            "textDocument/rename",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": params.position.line, "character": params.position.character},
                "newName": params.new_name,
            },
        )
    else:
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
