from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL)
async def semantic_tokens_full(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.SemanticTokensRequest, message)
    original_id = request.id
    uri = request.params.text_document.uri
    response = cast(types.SemanticTokensResponse, await based_proxy.pyright().request(request))

    file_state = based_proxy.FILE_STATES.get(uri)
    if file_state is None or file_state.vanilla or response.result is None:
        based_proxy.proxy().respond(original_id, response)
        return

    raw_data = response.result.data
    output: list[int] = []
    transpiled_line = transpiled_character = previous_line = previous_character = 0
    for i in range(0, len(raw_data), 5):
        delta_line, delta_character, length, token_type, token_modifiers = raw_data[i : i + 5]
        transpiled_line += delta_line
        transpiled_character = delta_character if delta_line > 0 else transpiled_character + delta_character
        if transpiled_line >= len(file_state.transpiled_line_starts):
            continue
        original_position = file_state.unmap_position(types.Position(line=transpiled_line, character=transpiled_character))
        if original_position is None:
            continue
        line, character = original_position.line, original_position.character
        delta_line = line - previous_line
        output.extend([delta_line, character if delta_line > 0 else character - previous_character, length, token_type, token_modifiers])
        previous_line, previous_character = line, character

    response.result.data = output
    based_proxy.proxy().respond(original_id, response)
