from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_INLAY_HINT)
async def inlay_hint(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.InlayHintRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    start = file_state.map_position(request.params.range.start)
    if start is None:
        start = types.Position(line=0, character=0)

    end = file_state.map_position(request.params.range.end)
    if end is None:
        last_line = len(file_state.transpiled_line_starts) - 1
        last_character = len(file_state.transpiled) - file_state.transpiled_line_starts[last_line]
        end = types.Position(line=last_line, character=last_character)

    request.params.range = types.Range(start=start, end=end)
    response = cast(types.InlayHintResponse, await based_proxy.pyright().request(request))

    if response.result:
        remapped: list[types.InlayHint] = []
        for hint in response.result:
            new_position = file_state.unmap_position(hint.position)
            if new_position is None:
                continue
            hint.position = new_position
            remapped.append(hint)
        response.result = remapped

    based_proxy.proxy().respond(original_id, response)
