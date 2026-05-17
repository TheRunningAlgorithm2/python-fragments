from __future__ import annotations

from lsprotocol import types

from fragments.lsp.server import FragmentsServer, _TOKEN_MODIFIERS, _TOKEN_TYPES, server


@server.feature(
    types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    types.SemanticTokensLegend(token_types=_TOKEN_TYPES, token_modifiers=_TOKEN_MODIFIERS),
)
async def semantic_tokens_full(language_server: FragmentsServer, params: types.SemanticTokensParams) -> types.SemanticTokens:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return types.SemanticTokens(data=[])
    state = language_server._files[params.text_document.uri]

    result = await language_server._pyright.request(
        "textDocument/semanticTokens/full",
        {"textDocument": {"uri": params.text_document.uri}},
    )
    raw_data = (result.get("result") or {}).get("data") or []

    if state is None:
        return types.SemanticTokens(data=raw_data)

    output: list[int] = []
    transpiled_line = transpiled_character = previous_line = previous_character = 0
    for i in range(0, len(raw_data), 5):
        delta_line, delta_character, length, token_type, token_modifiers = raw_data[i : i + 5]
        transpiled_line += delta_line
        transpiled_character = delta_character if delta_line > 0 else transpiled_character + delta_character
        if transpiled_line >= len(state.transpiled_line_starts):
            continue
        original_position = state.transpiled_to_original_position(types.Position(line=transpiled_line, character=transpiled_character))
        if original_position is None:
            continue
        line, character = original_position.line, original_position.character
        delta_line = line - previous_line
        output.extend([delta_line, character if delta_line > 0 else character - previous_character, length, token_type, token_modifiers])
        previous_line, previous_character = line, character

    return types.SemanticTokens(data=output)
