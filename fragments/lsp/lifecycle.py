from __future__ import annotations

import asyncio

from lsprotocol import types

from fragments import grammar
from fragments.lsp.pyright import PyrightClient
from fragments.lsp.server import FragmentsServer, _build_file_state, _converter, _parse_error_to_diagnostic, server

_DEBOUNCE_SECONDS = 0.15


@server.feature(types.INITIALIZED)
async def initialized(language_server: FragmentsServer, _params: types.InitializedParams) -> None:
    root_uri = language_server.workspace.root_uri
    workspace_folders = [{"uri": folder.uri, "name": folder.name} for folder in language_server.workspace.folders.values()]

    pyright = PyrightClient(language_server._on_pyright_notification, language_server._on_pyright_request)
    language_server._pyright = pyright
    await pyright.start()
    await pyright.request(
        "initialize",
        {
            "processId": None,
            "rootUri": root_uri,
            "workspaceFolders": workspace_folders or None,
            "capabilities": _converter.unstructure(language_server.client_capabilities),
        },
    )
    pyright.notify("initialized", {})


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
async def did_open(language_server: FragmentsServer, params: types.DidOpenTextDocumentParams) -> None:
    document = params.text_document
    try:
        state, content_for_pyright = await asyncio.get_running_loop().run_in_executor(None, _build_file_state, document.text)
        language_server._parse_errors[document.uri] = None
    except grammar.ParsingError as error:
        state = None
        content_for_pyright = document.text
        language_server._parse_errors[document.uri] = _parse_error_to_diagnostic(document.text, error)
        language_server._republish_diagnostics(document.uri)
    language_server._files[document.uri] = state

    if not language_server._pyright:
        return
    language_server._pyright.notify(
        "textDocument/didOpen",
        {
            "textDocument": {
                "uri": document.uri,
                "languageId": document.language_id,
                "version": document.version,
                "text": content_for_pyright,
            }
        },
    )


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(language_server: FragmentsServer, params: types.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.content_changes[-1].text

    existing = language_server._debounce_tasks.pop(uri, None)
    if existing:
        existing.cancel()

    async def _apply_change() -> None:
        await asyncio.sleep(_DEBOUNCE_SECONDS)
        language_server._debounce_tasks.pop(uri, None)
        try:
            state, content_for_pyright = await asyncio.get_running_loop().run_in_executor(None, _build_file_state, text)
            language_server._parse_errors[uri] = None
            language_server._files[uri] = state
            if not language_server._pyright:
                return
            language_server._pyright.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": uri, "version": params.text_document.version},
                    "contentChanges": [{"text": content_for_pyright}],
                },
            )
        except grammar.ParsingError as error:
            language_server._parse_errors[uri] = _parse_error_to_diagnostic(text, error)
            language_server._republish_diagnostics(uri)

    language_server._debounce_tasks[uri] = asyncio.ensure_future(_apply_change())


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(language_server: FragmentsServer, params: types.DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    language_server._files.pop(uri, None)
    language_server._parse_errors.pop(uri, None)
    language_server._pyright_diagnostics.pop(uri, None)

    existing = language_server._debounce_tasks.pop(uri, None)
    if existing:
        existing.cancel()

    if not language_server._pyright:
        return
    language_server._pyright.notify("textDocument/didClose", {"textDocument": {"uri": uri}})


@server.feature(types.WORKSPACE_DID_CHANGE_WATCHED_FILES)
def did_change_watched_files(language_server: FragmentsServer, params: types.DidChangeWatchedFilesParams) -> None:
    if not language_server._pyright:
        return
    language_server._pyright.notify("workspace/didChangeWatchedFiles", _converter.unstructure(params))
