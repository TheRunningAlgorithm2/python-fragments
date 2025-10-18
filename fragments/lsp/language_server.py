from lsprotocol import types
from lsprotocol.converters import get_converter
from pygls.server import LanguageServer

from fragments import transpiler
from fragments.lsp import pyright

converter = get_converter()
ls = LanguageServer("fragments-lsp", "0.0.1")


@ls.feature(types.INITIALIZE)
def initialize(params: types.InitializeParams):
    ls.show_message_log("[fragments-lsp] Initialize request (started)")
    response = pyright.send({"method": types.INITIALIZE, "params": params}, converter)
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
    params.text_document.text = ""
    params.text_document.language_id = "python"
    pyright.send_notification({"method": types.TEXT_DOCUMENT_DID_OPEN, "params": params}, converter)


@ls.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def text_document_document_symbol(params: types.DocumentSymbolParams):
    ls.show_message_log(f"[fragments-lsp] textDocument/documentSymbol (started)")
    params.text_document.uri = params.text_document.uri.replace(".pyf", ".py")
    response = pyright.send({"method": types.TEXT_DOCUMENT_DOCUMENT_SYMBOL, "params": params}, converter)
    ls.show_message_log(f"[fragments-lsp] textDocument/documentSymbol (completed)")
    return response.body


@ls.feature(types.TEXT_DOCUMENT_HOVER)
def text_document_hover(params: types.HoverParams):
    ls.show_message_log(f"[fragments-lsp] textDocument/hover (started)")
    params.text_document.uri = params.text_document.uri.replace(".pyf", ".py")
    ls.show_message_log(f"[fragments-lsp] textDocument/hover (params): {params}")
    response = pyright.send({"method": types.TEXT_DOCUMENT_HOVER, "params": params}, converter)
    ls.show_message_log(f"[fragments-lsp] textDocument/hover (completed)")
    return response.body


@pyright.debug_listener
def on_debug(response: pyright._PyrightResponse):
    ls.show_message_log(f"[fragments-lsp] Debug response: {response.body}")
