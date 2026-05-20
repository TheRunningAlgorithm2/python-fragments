from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT)
async def document_highlight(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.DocumentHighlightRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.DocumentHighlightResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.DocumentHighlightResponse, await based_proxy.pyright().request(request))

    if response.result:
        remapped: list[types.DocumentHighlight] = []
        for highlight in response.result:
            new_range = file_state.unmap_range(highlight.range)
            if new_range is None:
                continue
            highlight.range = new_range
            remapped.append(highlight)
        response.result = remapped

    based_proxy.proxy().respond(original_id, response)
