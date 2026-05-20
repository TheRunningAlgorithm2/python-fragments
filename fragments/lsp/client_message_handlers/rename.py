from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_PREPARE_RENAME)
async def prepare_rename(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.PrepareRenameRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.PrepareRenameResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.PrepareRenameResponse, await based_proxy.pyright().request(request))

    if isinstance(response.result, types.Range):
        response.result = file_state.unmap_range(response.result)
    elif isinstance(response.result, types.PrepareRenamePlaceholder):
        response.result.range = file_state.unmap_range(response.result.range) or response.result.range

    based_proxy.proxy().respond(original_id, response)


@handle_from_client(types.TEXT_DOCUMENT_RENAME)
async def rename(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.RenameRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.RenameResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.RenameResponse, await based_proxy.pyright().request(request))

    if response.result is not None:
        for change in response.result.document_changes or []:
            if isinstance(change, types.TextDocumentEdit) and (state := based_proxy.FILE_STATES.get(change.text_document.uri)):
                remapped: list[types.AnnotatedTextEdit | types.TextEdit | types.SnippetTextEdit] = []
                for edit in change.edits:
                    if not isinstance(edit, types.SnippetTextEdit) and (r := state.unmap_range(edit.range)) is not None:
                        edit.range = r
                        remapped.append(edit)
                change.edits = remapped

    based_proxy.proxy().respond(original_id, response)
