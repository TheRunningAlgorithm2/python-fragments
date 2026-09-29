from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client
from fragments.formatter import format_source


def formatting_edits(original: str) -> list[types.TextEdit]:
    """Build the edits needed to format a document, or none if it is already formatted or cannot be formatted."""
    try:
        formatted = format_source(original)
    except ValueError:  # black.InvalidInput: syntax errors are already reported as diagnostics
        return []

    if formatted == original:
        return []

    lines = original.split("\n")
    whole_document = types.Range(
        start=types.Position(line=0, character=0),
        end=types.Position(line=len(lines) - 1, character=len(lines[-1])),
    )
    return [types.TextEdit(range=whole_document, new_text=formatted)]


@handle_from_client(types.TEXT_DOCUMENT_FORMATTING)
async def formatting(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.DocumentFormattingRequest, message)
    original_id = request.id
    file_state = based_proxy.FILE_STATES.get(request.params.text_document.uri)

    # No file state means the document currently fails to parse, so leave it alone.
    try:
        edits = [] if file_state is None else formatting_edits(file_state.original)
    except Exception as error:  # e.g. black is not installed; always respond so the client's request never hangs
        based_proxy.proxy().respond(
            original_id,
            types.ResponseErrorMessage(id=original_id, error=types.ResponseError(code=types.ErrorCodes.InternalError, message=str(error))),
        )
        return

    based_proxy.proxy().respond(original_id, types.DocumentFormattingResponse(id=original_id, result=edits))
