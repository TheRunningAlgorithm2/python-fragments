from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client


@handle_from_client(types.TEXT_DOCUMENT_DIAGNOSTIC)
async def text_document_diagnostic(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.DocumentDiagnosticRequest, message)
    original_id = request.id
    uri = request.params.text_document.uri
    parse_error = based_proxy.PARSE_ERRORS.get(uri)
    file_state = based_proxy.FILE_STATES.get(uri)

    if parse_error is not None:
        based_proxy.proxy().respond(
            original_id,
            types.DocumentDiagnosticResponse(
                id=original_id,
                result=types.RelatedFullDocumentDiagnosticReport(kind="full", items=[parse_error]),
            ),
        )
        return

    response = cast(types.DocumentDiagnosticResponse, await based_proxy.pyright().request(request))

    if file_state is None or file_state.vanilla or response.result is None:
        based_proxy.proxy().respond(original_id, response)
        return

    if isinstance(response.result, types.RelatedUnchangedDocumentDiagnosticReport):
        based_proxy.proxy().respond(original_id, response)
        return

    remapped_items: list[types.Diagnostic] = []
    for diagnostic in response.result.items or []:
        remapped_range = file_state.unmap_range(diagnostic.range)
        if remapped_range is None:
            continue
        diagnostic.range = remapped_range
        remapped_items.append(diagnostic)

    response.result.items = remapped_items
    based_proxy.proxy().respond(original_id, response)
