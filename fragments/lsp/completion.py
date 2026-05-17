from __future__ import annotations

from lsprotocol import types

from fragments.lsp.server import FragmentsServer, _converter, _remap_text_edits, server


@server.feature(types.TEXT_DOCUMENT_COMPLETION, types.CompletionOptions(trigger_characters=["."]))
async def completion(language_server: FragmentsServer, params: types.CompletionParams) -> types.CompletionList | None:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return None
    state = language_server._files[params.text_document.uri]

    context = None
    if params.context is not None:
        context = {
            "triggerKind": params.context.trigger_kind.value,
            "triggerCharacter": params.context.trigger_character,
        }

    if state is None:
        result = await language_server._pyright.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": params.position.line, "character": params.position.character},
                "context": context,
            },
        )
        raw_result = result.get("result")
        if not raw_result:
            return None
        if isinstance(raw_result, list):
            return types.CompletionList(is_incomplete=False, items=_converter.structure(raw_result, list[types.CompletionItem]))
        return _converter.structure(raw_result, types.CompletionList)

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

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
