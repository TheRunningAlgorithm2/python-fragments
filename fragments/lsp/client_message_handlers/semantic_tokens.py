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
    # Unmap every token to an absolute source position first. The transpiler does not always emit code in source order
    # (e.g. `if` / `for` expressions come after the element body), so the unmapped tokens must be re-sorted before
    # being delta-encoded - the LSP spec requires tokens in document order with unsigned deltas.
    unmapped: list[tuple[int, int, int, int, int]] = []
    transpiled_line = transpiled_character = 0
    for i in range(0, len(raw_data), 5):
        delta_line, delta_character, length, token_type, token_modifiers = raw_data[i : i + 5]
        transpiled_line += delta_line
        transpiled_character = delta_character if delta_line != 0 else transpiled_character + delta_character
        if transpiled_line >= len(file_state.transpiled_line_starts):
            continue
        original_position = file_state.unmap_position(types.Position(line=transpiled_line, character=transpiled_character))
        if original_position is None:
            continue
        unmapped.append((original_position.line, original_position.character, length, token_type, token_modifiers))

    unmapped.sort(key=lambda token: (token[0], token[1]))

    output: list[int] = []
    previous_line = previous_character = 0
    for line, character, length, token_type, token_modifiers in unmapped:
        delta_line = line - previous_line
        delta_character = character if delta_line != 0 else character - previous_character
        output.extend([delta_line, delta_character, length, token_type, token_modifiers])
        previous_line, previous_character = line, character

    response.result.data = output
    based_proxy.proxy().respond(original_id, response)
