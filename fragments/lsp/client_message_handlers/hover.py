from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_HOVER)
async def hover(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.HoverRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        response = await based_proxy.pyright().request(request)
        based_proxy.proxy().respond(original_id, response)
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.HoverResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    response = cast(types.HoverResponse, await based_proxy.pyright().request(request))

    if response.result is not None and response.result.range is not None:
        start = file_state.unmap_position(response.result.range.start)
        end = file_state.unmap_position(response.result.range.end)
        response.result.range = types.Range(start=start, end=end) if start is not None and end is not None else None

    based_proxy.proxy().respond(original_id, response)
