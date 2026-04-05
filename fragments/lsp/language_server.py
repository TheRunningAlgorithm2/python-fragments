import json

from lsprotocol import types
from lsprotocol.converters import get_converter
from pygls.server import LanguageServer

from fragments.lsp import pyright

converter = get_converter()
ls = LanguageServer("fragments-lsp", "0.0.1")


@ls.feature(types.INITIALIZE)
def initialize(params: types.InitializeParams):
    ls.show_message_log("[fragments-lsp] Initialize request (started)")
    ls.show_message_log(f"[fragments-lsp] InitializeParams.rootUri: {params.root_uri}")
    ls.show_message_log(f"[fragments-lsp] InitializeParams.workspaceFolders: {params.workspace_folders}")
    response = pyright.send({"method": types.INITIALIZE, "params": params}, converter)
    ls.show_message_log(f"[fragments-lsp] Initialize response capabilities: {response.body.get('capabilities', {}).keys() if isinstance(response.body, dict) else 'N/A'}")
    ls.show_message_log(f"[fragments-lsp] Initialize request (completed)")
    return response.body


@ls.feature(types.INITIALIZED)
def initialized(params: types.InitializedParams):
    ls.show_message_log(f"[fragments-lsp] Initialize notification (started)")
    pyright.send_notification({"method": types.INITIALIZED}, converter)


@ls.feature(types.TEXT_DOCUMENT_DID_OPEN)
def text_document_did_open(params: types.DidOpenTextDocumentParams):
    ls.show_message_log(f"[fragments-lsp] textDocument/didOpen (started)")
    params.text_document.uri = params.text_document.uri.replace(".pyf", ".py")
    params.text_document.text = params.text_document.text.replace("<>", '"""').replace("</>", '"""')
    params.text_document.language_id = "python"
    pyright.send_notification({"method": types.TEXT_DOCUMENT_DID_OPEN, "params": params}, converter)


@ls.feature(types.TEXT_DOCUMENT_HOVER)
def text_document_hover(params: types.HoverParams):
    ls.show_message_log(f"[fragments-lsp] textDocument/hover (started)")

    # Create new params with modified URI instead of mutating
    py_uri = params.text_document.uri.replace(".pyf", ".py")
    new_params = types.HoverParams(text_document=types.TextDocumentIdentifier(uri=py_uri), position=params.position, work_done_token=params.work_done_token)

    ls.show_message_log(f"[fragments-lsp] textDocument/hover (params): {new_params}")
    response = pyright.send({"method": types.TEXT_DOCUMENT_HOVER, "params": new_params}, converter)
    ls.show_message_log(f"[fragments-lsp] textDocument/hover (completed)")
    return response.body


@pyright.debug_listener
def on_debug(response: pyright._PyrightResponse):
    ls.show_message_log(f"[fragments-lsp] Debug response: {response.body}")


@pyright.listener("client/registerCapability")
def on_register_capability(response: pyright._PyrightResponse):
    ls.show_message_log(f"[fragments-lsp] Received client/registerCapability request")
    pyright.send_response({"id": response.body["id"], "method": "client/registerCapability", "result": None}, converter)
