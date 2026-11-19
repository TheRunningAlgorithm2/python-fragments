from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname
from typing import cast

from lsprotocol import types
from lsprotocol.types import NOTIFICATIONS, REQUESTS

from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


def formatting_edits(original: str, path: Path | None = None) -> list[types.TextEdit]:
    """Build the edits needed to format a document, or none if it is already formatted or cannot be formatted."""
    try:
        from fragments.formatter import format_source, load_configuration
    except ModuleNotFoundError as error:
        if error.name != "black":
            raise
        raise RuntimeError("Formatting requires black: pip install python-fragments[format]") from error

    mode = None
    if path is not None:
        # Raises ConfigurationError for a broken config, which the handler reports to the editor.
        configuration = load_configuration([path])
        if not configuration.sources:  # excluded by force-exclude, or not a .py file
            return []
        mode = configuration.mode
    try:
        formatted = format_source(original, mode)
    except ValueError:
        # black.InvalidInput: syntax errors are already reported as diagnostics
        return []

    if formatted == original:
        return []

    lines = original.split("\n")
    whole_document = types.Range(
        start=types.Position(line=0, character=0),
        end=types.Position(line=len(lines) - 1, character=len(lines[-1])),
    )
    return [types.TextEdit(range=whole_document, new_text=formatted)]


def _uri_to_path(uri: str) -> Path | None:
    """NOTE: Replace with Path.from_uri() if/when upgrading to python >=3.13"""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    return Path(url2pathname(parsed.path))


@handle_from_client(types.TEXT_DOCUMENT_FORMATTING)
async def formatting(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.DocumentFormattingRequest, message)
    original_id = request.id
    uri = request.params.text_document.uri
    file_state = based_proxy.FILE_STATES.get(uri)
    file_path = _uri_to_path(uri)

    # No file state means the document currently fails to parse, so leave it alone.
    try:
        edits = [] if file_state is None else formatting_edits(file_state.original, file_path)
    except Exception as error:
        # e.g. black is not installed; always respond so the client's request never hangs
        based_proxy.proxy().respond(
            original_id,
            types.ResponseErrorMessage(
                id=original_id,
                error=types.ResponseError(code=types.ErrorCodes.InternalError, message=str(error)),
            ),
        )
        return

    based_proxy.proxy().respond(
        original_id, types.DocumentFormattingResponse(id=original_id, result=edits)
    )
