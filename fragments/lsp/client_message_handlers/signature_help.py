from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_SIGNATURE_HELP)
async def signature_help(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.SignatureHelpRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    mapped_position = file_state.map_position(request.params.position)
    if mapped_position is None:
        based_proxy.proxy().respond(original_id, types.SignatureHelpResponse(id=original_id, result=None))
        return

    request.params.position = mapped_position
    based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
