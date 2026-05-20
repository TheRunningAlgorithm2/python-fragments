import bisect
from lsprotocol import types
from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import cast
from fragments.lsp import based_proxy
from fragments.lsp.based_proxy import handle_from_client, FILE_STATES
from fragments.lsp.file_state import FileState
from fragments import grammar


def _parse_error_diagnostic(text: str, error: grammar.ParsingError) -> types.Diagnostic:
    line_starts = [0] + [i + 1 for i, char in enumerate(text) if char == "\n"]
    offset = min(error.source_start, max(0, len(text) - 1))
    line = bisect.bisect_right(line_starts, offset) - 1
    character = offset - line_starts[line]
    position = types.Position(line=line, character=character)
    return types.Diagnostic(
        range=types.Range(start=position, end=position),
        message=str(error),
        severity=types.DiagnosticSeverity.Error,
        source="fragments",
    )


def publish_parse_error_diagnostics(uri: str) -> None:
    diagnostics: list[types.Diagnostic] = []
    parse_error = based_proxy.PARSE_ERRORS.get(uri)
    if parse_error is not None:
        diagnostics.append(parse_error)
    based_proxy.proxy().notify(
        types.PublishDiagnosticsNotification(
            params=types.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
        )
    )


@handle_from_client(types.INITIALIZE)
async def initialize(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.InitializeRequest, message)
    original_id = request.id
    pyright_response = cast(types.InitializeResponse, await based_proxy.pyright().request(request))
    assert pyright_response.result is not None
    pyright_response.result.capabilities.text_document_sync = types.TextDocumentSyncKind.Full
    based_proxy.proxy().respond(original_id, pyright_response)


@handle_from_client(types.INITIALIZED)
async def initialized(message: REQUESTS | NOTIFICATIONS) -> None:
    based_proxy.pyright().notify(cast(types.InitializedNotification, message))


@handle_from_client(types.TEXT_DOCUMENT_DID_OPEN)
async def did_open(message: REQUESTS | NOTIFICATIONS) -> None:
    notification = cast(types.DidOpenTextDocumentNotification, message)
    document = notification.params.text_document

    try:
        file_state = FileState(document.text)
        based_proxy.PARSE_ERRORS[document.uri] = None
        FILE_STATES[document.uri] = file_state
        document.text = file_state.transpiled
    except grammar.ParsingError as error:
        based_proxy.PARSE_ERRORS[document.uri] = _parse_error_diagnostic(document.text, error)
        publish_parse_error_diagnostics(document.uri)

    based_proxy.pyright().notify(notification)


@handle_from_client(types.TEXT_DOCUMENT_DID_CHANGE)
async def did_change(message: REQUESTS | NOTIFICATIONS) -> None:
    notification = cast(types.DidChangeTextDocumentNotification, message)
    uri = notification.params.text_document.uri
    text = notification.params.content_changes[-1].text

    FILE_STATES.pop(uri, None)
    had_parse_error = based_proxy.PARSE_ERRORS.get(uri) is not None

    try:
        file_state = FileState(text)
        based_proxy.PARSE_ERRORS[uri] = None
        FILE_STATES[uri] = file_state
        notification.params.content_changes = [types.TextDocumentContentChangeWholeDocument(text=file_state.transpiled)]
        if had_parse_error:
            publish_parse_error_diagnostics(uri)
    except grammar.ParsingError as error:
        based_proxy.PARSE_ERRORS[uri] = _parse_error_diagnostic(text, error)
        publish_parse_error_diagnostics(uri)

    based_proxy.pyright().notify(notification)


@handle_from_client(types.TEXT_DOCUMENT_DID_CLOSE)
async def did_close(message: REQUESTS | NOTIFICATIONS) -> None:
    notification = cast(types.DidCloseTextDocumentNotification, message)
    uri = notification.params.text_document.uri
    FILE_STATES.pop(uri, None)
    based_proxy.PARSE_ERRORS.pop(uri, None)
    based_proxy.pyright().notify(notification)


@handle_from_client(types.WORKSPACE_DID_CHANGE_WATCHED_FILES)
async def did_change_watched_files(message: REQUESTS | NOTIFICATIONS) -> None:
    based_proxy.pyright().notify(cast(types.DidChangeWatchedFilesNotification, message))


@handle_from_client(types.SHUTDOWN)
async def shutdown(message: REQUESTS | NOTIFICATIONS) -> None:
    request = cast(types.ShutdownRequest, message)
    original_id = request.id
    response = await based_proxy.pyright().request(request)
    based_proxy.proxy().respond(original_id, response)


@handle_from_client(types.EXIT)
async def exit_server(message: REQUESTS | NOTIFICATIONS) -> None:
    based_proxy.pyright().notify(cast(types.ExitNotification, message))
    await based_proxy.stop()
