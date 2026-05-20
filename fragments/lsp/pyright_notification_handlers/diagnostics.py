from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_pyright


@handle_from_pyright(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
async def publish_diagnostics(message: REQUESTS | NOTIFICATIONS) -> None:
    notification = cast(types.PublishDiagnosticsNotification, message)
    uri = notification.params.uri

    if based_proxy.PARSE_ERRORS.get(uri) is not None:
        return

    file_state = based_proxy.FILE_STATES.get(uri)

    if file_state is None or file_state.vanilla:
        based_proxy.proxy().notify(notification)
        return

    remapped_diagnostics: list[types.Diagnostic] = []
    for diagnostic in notification.params.diagnostics:
        remapped_range = file_state.unmap_range(diagnostic.range)
        if remapped_range is None:
            continue
        diagnostic.range = remapped_range
        remapped_diagnostics.append(diagnostic)

    notification.params.diagnostics = remapped_diagnostics
    based_proxy.proxy().notify(notification)
