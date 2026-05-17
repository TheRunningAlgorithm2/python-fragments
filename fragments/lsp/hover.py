from __future__ import annotations

from lsprotocol import types

from fragments.lsp.server import FragmentsServer, _converter, server


@server.feature(types.TEXT_DOCUMENT_HOVER)
async def hover(language_server: FragmentsServer, params: types.HoverParams) -> types.Hover | None:
    if language_server._pyright is None or params.text_document.uri not in language_server._files:
        return None
    state = language_server._files[params.text_document.uri]

    if state is None:
        result = await language_server._pyright.request(
            "textDocument/hover",
            {
                "textDocument": {"uri": params.text_document.uri},
                "position": {"line": params.position.line, "character": params.position.character},
            },
        )
        raw_hover = result.get("result")
        return _converter.structure(raw_hover, types.Hover) if raw_hover else None

    transpiled_position = state.original_to_transpiled_position(params.position)
    if transpiled_position is None:
        return None

    result = await language_server._pyright.request(
        "textDocument/hover",
        {
            "textDocument": {"uri": params.text_document.uri},
            "position": {"line": transpiled_position.line, "character": transpiled_position.character},
        },
    )

    raw_hover = result.get("result")
    if not raw_hover:
        return None

    hover_response = _converter.structure(raw_hover, types.Hover)
    if hover_response.range is not None:
        hover_response.range = state.transpiled_to_original_range(hover_response.range)
    return hover_response
