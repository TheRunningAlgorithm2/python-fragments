from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client
from fragments.lsp.file_state import FileState


def _remap_document_symbols(symbols: list[types.DocumentSymbol], file_state: FileState) -> list[types.DocumentSymbol]:
    remapped: list[types.DocumentSymbol] = []
    for symbol in symbols:
        new_range = file_state.unmap_range(symbol.range)
        new_selection_range = file_state.unmap_range(symbol.selection_range)
        if new_range is None or new_selection_range is None:
            continue
        symbol.range = new_range
        symbol.selection_range = new_selection_range
        if symbol.children:
            symbol.children = _remap_document_symbols(list(symbol.children), file_state)
        remapped.append(symbol)
    return remapped


@handle_from_client(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
async def document_symbol(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.DocumentSymbolRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().respond(original_id, await based_proxy.pyright().request(request))
        return

    response = cast(types.DocumentSymbolResponse, await based_proxy.pyright().request(request))

    if not response.result:
        based_proxy.proxy().respond(original_id, response)
        return

    if isinstance(response.result[0], types.SymbolInformation):
        remapped_info: list[types.SymbolInformation] = []
        for symbol in cast(list[types.SymbolInformation], response.result):
            new_range = file_state.unmap_range(symbol.location.range)
            if new_range is None:
                continue
            symbol.location.range = new_range
            remapped_info.append(symbol)
        response.result = remapped_info
    else:
        response.result = _remap_document_symbols(cast(list[types.DocumentSymbol], response.result), file_state)

    based_proxy.proxy().respond(original_id, response)
