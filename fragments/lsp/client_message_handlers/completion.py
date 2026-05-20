from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client
from fragments.lsp.file_state import FileState


def _remap_item(item: types.CompletionItem, file_state: FileState) -> bool:
    if isinstance(item.text_edit, types.InsertReplaceEdit):
        insert = file_state.unmap_range(item.text_edit.insert)
        replace = file_state.unmap_range(item.text_edit.replace)
        if insert is None or replace is None:
            return False
        item.text_edit.insert, item.text_edit.replace = insert, replace
    elif item.text_edit is not None:
        if (r := file_state.unmap_range(item.text_edit.range)) is None:
            return False
        item.text_edit.range = r
    if item.additional_text_edits:
        remapped_edits = []
        for edit in item.additional_text_edits:
            if (r := file_state.unmap_range(edit.range)) is not None:
                edit.range = r
                remapped_edits.append(edit)
        item.additional_text_edits = remapped_edits
    return True


@handle_from_client(types.TEXT_DOCUMENT_COMPLETION)
async def completion(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.CompletionRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    if (mapped := file_state.map_position(request.params.position)) is None:
        return
    request.params.position = mapped

    response = cast(types.CompletionResponse, await based_proxy.pyright().request(request))
    items = response.result.items if isinstance(response.result, types.CompletionList) else list(response.result or [])
    remapped = [item for item in items if _remap_item(item, file_state)]
    response.result = remapped
    based_proxy.proxy().respond(original_id, response)


@handle_from_client(types.COMPLETION_ITEM_RESOLVE)
async def completion_item_resolve(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.CompletionResolveRequest, message)
    based_proxy.proxy().respond(request.id, cast(types.CompletionResolveResponse, await based_proxy.pyright().request(request)))
