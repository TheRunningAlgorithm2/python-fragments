from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_CODE_ACTION)
async def code_action(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.CodeActionRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_range = file_state.map_range(request.params.range)
    if mapped_range is None:
        based_proxy.proxy().respond(original_id, types.CodeActionResponse(id=original_id, result=[]))
        return

    request.params.range = mapped_range
    response = cast(types.CodeActionResponse, await based_proxy.pyright().request(request))

    for action in response.result or []:
        if isinstance(action, types.CodeAction) and action.edit is not None:
            for change in action.edit.document_changes or []:
                if isinstance(change, types.TextDocumentEdit) and (state := based_proxy.FILE_STATES.get(change.text_document.uri)):
                    for edit in change.edits:
                        if not isinstance(edit, types.SnippetTextEdit) and (r := state.unmap_range(edit.range)) is not None:
                            edit.range = r

    based_proxy.proxy().respond(original_id, response)
