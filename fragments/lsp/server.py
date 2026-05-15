from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from lsprotocol import types
from pygls.server import LanguageServer

from fragments.lsp.pyright import PyrightClient
from fragments.lsp.source_map import (
    Segment,
    orig_to_trans,
    to_offset,
    to_position,
    trans_to_orig,
    transpile_with_map,
)


@dataclass
class _FileState:
    original: str
    transpiled: str
    segments: list[Segment]


class FragmentsServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(
            "fragments-lsp",
            "v0.1",
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )
        self._pyright: PyrightClient | None = None
        self._files: dict[str, _FileState] = {}

    def _on_pyright_notification(self, msg: dict) -> None:
        if msg.get("method") == "textDocument/publishDiagnostics":
            asyncio.ensure_future(self._publish_diagnostics(msg["params"]))

    async def _on_pyright_request(self, msg: dict) -> object:
        if msg["method"] == "workspace/configuration":
            return [
                self._config_for_section(item.get("section", ""))
                for item in msg["params"]["items"]
            ]
        return None

    def _config_for_section(self, section: str) -> object:
        if section == "python":
            return {"pythonPath": sys.executable, "defaultInterpreterPath": sys.executable}
        if section in ("basedpyright", "basedpyright.analysis", "python.analysis"):
            project_root = str(Path(__file__).parent.parent.parent)
            return {"typeCheckingMode": "basic", "openFilesOnly": True, "extraPaths": [project_root]}
        return None

    async def _publish_diagnostics(self, params: dict) -> None:
        uri = params["uri"]
        state = self._files.get(uri)
        diagnostics = []
        for d in params["diagnostics"]:
            if state is not None:
                d = _map_diagnostic(d, state)
                if d is None:
                    continue
            diagnostics.append(
                types.Diagnostic(
                    range=types.Range(
                        start=types.Position(
                            line=d["range"]["start"]["line"],
                            character=d["range"]["start"]["character"],
                        ),
                        end=types.Position(
                            line=d["range"]["end"]["line"],
                            character=d["range"]["end"]["character"],
                        ),
                    ),
                    message=d["message"],
                    severity=types.DiagnosticSeverity(d["severity"]) if d.get("severity") is not None else None,
                    code=d.get("code"),
                    source=d.get("source"),
                )
            )
        self.publish_diagnostics(uri, diagnostics)


server = FragmentsServer()


def _map_diagnostic(diag: dict, state: _FileState) -> dict | None:
    start = diag["range"]["start"]
    orig_start = trans_to_orig(
        to_offset(state.transpiled, start["line"], start["character"]), state.segments
    )
    if orig_start is None:
        return None

    end = diag["range"]["end"]
    orig_end = trans_to_orig(
        to_offset(state.transpiled, end["line"], end["character"]), state.segments
    )
    if orig_end is None:
        return None

    return {
        **diag,
        "range": {
            "start": to_position(state.original, orig_start),
            "end": to_position(state.original, orig_end),
        },
    }


def _remap_range(range_: dict, state: _FileState) -> dict | None:
    start = trans_to_orig(
        to_offset(state.transpiled, range_["start"]["line"], range_["start"]["character"]),
        state.segments,
    )
    end = trans_to_orig(
        to_offset(state.transpiled, range_["end"]["line"], range_["end"]["character"]),
        state.segments,
    )
    if start is None or end is None:
        return None
    return {
        "start": to_position(state.original, start),
        "end": to_position(state.original, end),
    }


@server.feature(types.INITIALIZED)
async def initialized(ls: FragmentsServer, _params: types.InitializedParams) -> None:
    root_uri = ls.workspace.root_uri
    workspace_folders = [
        {"uri": f.uri, "name": f.name} for f in ls.workspace.folders.values()
    ]

    pyright = PyrightClient(ls._on_pyright_notification, ls._on_pyright_request)
    ls._pyright = pyright
    await pyright.start()
    await pyright.request(
        "initialize",
        {
            "processId": None,
            "rootUri": root_uri,
            "workspaceFolders": workspace_folders or None,
            "capabilities": {"workspace": {"configuration": True}},
        },
    )
    pyright.notify("initialized", {})


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: FragmentsServer, params: types.DidOpenTextDocumentParams) -> None:
    doc = params.text_document
    transpiled, segments = transpile_with_map(doc.text)
    ls._files[doc.uri] = _FileState(doc.text, transpiled, segments)

    if ls._pyright:
        ls._pyright.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": doc.uri,
                    "languageId": doc.language_id,
                    "version": doc.version,
                    "text": transpiled,
                }
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: FragmentsServer, params: types.DidChangeTextDocumentParams) -> None:
    uri = params.text_document.uri
    text = params.content_changes[-1].text
    transpiled, segments = transpile_with_map(text)
    ls._files[uri] = _FileState(text, transpiled, segments)

    if ls._pyright:
        ls._pyright.notify(
            "textDocument/didChange",
            {
                "textDocument": {"uri": uri, "version": params.text_document.version},
                "contentChanges": [{"text": transpiled}],
            },
        )


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def did_close(ls: FragmentsServer, params: types.DidCloseTextDocumentParams) -> None:
    uri = params.text_document.uri
    ls._files.pop(uri, None)

    if ls._pyright:
        ls._pyright.notify("textDocument/didClose", {"textDocument": {"uri": uri}})


@server.feature(types.TEXT_DOCUMENT_HOVER)
async def hover(ls: FragmentsServer, params: types.HoverParams) -> types.Hover | None:
    if ls._pyright is None:
        return None

    uri = params.text_document.uri
    state = ls._files.get(uri)
    if state is None:
        return None

    pos = params.position
    orig_offset = to_offset(state.original, pos.line, pos.character)
    trans_offset = orig_to_trans(orig_offset, state.segments)
    if trans_offset is None:
        return None

    trans_pos = to_position(state.transpiled, trans_offset)
    result = await ls._pyright.request(
        "textDocument/hover",
        {"textDocument": {"uri": uri}, "position": trans_pos},
    )

    hover_result = result.get("result")
    if not hover_result:
        return None

    range_ = hover_result.get("range")
    if range_ is not None:
        remapped = _remap_range(range_, state)
        hover_result = (
            {**hover_result, "range": remapped}
            if remapped is not None
            else {k: v for k, v in hover_result.items() if k != "range"}
        )

    contents = hover_result.get("contents", "")
    if isinstance(contents, dict):
        markup = types.MarkupContent(
            kind=types.MarkupKind(contents["kind"]),
            value=contents["value"],
        )
    elif isinstance(contents, list):
        markup = types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value="\n\n---\n\n".join(
                c["value"] if isinstance(c, dict) else c for c in contents
            ),
        )
    else:
        markup = types.MarkupContent(kind=types.MarkupKind.PlainText, value=str(contents))

    hover_range = None
    if "range" in hover_result:
        r = hover_result["range"]
        hover_range = types.Range(
            start=types.Position(line=r["start"]["line"], character=r["start"]["character"]),
            end=types.Position(line=r["end"]["line"], character=r["end"]["character"]),
        )

    return types.Hover(contents=markup, range=hover_range)


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
