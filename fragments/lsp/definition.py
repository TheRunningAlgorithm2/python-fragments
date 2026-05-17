from __future__ import annotations

from lsprotocol import types

from fragments.lsp.server import FragmentsServer, _converter, server


@server.feature(types.TEXT_DOCUMENT_DEFINITION)
async def definition(language_server: FragmentsServer, params: types.DefinitionParams) -> list[types.Location] | None:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return None
    state = language_server._files[params.text_document.uri]

    if state is None:
        result = await language_server._pyright.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": params.position.line, "character": params.position.character},
            },
        )
    else:
        transpiled_position = state.original_to_transpiled_position(params.position)
        if transpiled_position is None:
            return None
        result = await language_server._pyright.request(
            "textDocument/definition",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": transpiled_position.line, "character": transpiled_position.character},
            },
        )

    raw_result = result.get("result")
    if not raw_result:
        return None

    raw_locations = [raw_result] if isinstance(raw_result, dict) else raw_result
    locations: list[types.Location] = []
    for location in _converter.structure(raw_locations, list[types.Location]):
        target_state = language_server._files.get(location.uri)
        if target_state is not None:
            remapped = target_state.transpiled_to_original_range(location.range)
            if remapped is None:
                continue
            location.range = remapped
        locations.append(location)

    return locations or None
