from __future__ import annotations

import asyncio
import sys
from typing import Any

from lsprotocol import types
from lsprotocol.converters import get_converter
from pygls.server import LanguageServer

from fragments import grammar
from fragments.ast_nodes import ASTFragment
from fragments.lsp.file_state import _FileState, _build_line_starts, _offset_to_position
from fragments.lsp.pyright import PyrightClient
from fragments.source import Source

_converter = get_converter()

_TOKEN_TYPES = ["namespace", "type", "class", "enum", "typeParameter", "parameter", "variable", "property", "enumMember", "function", "method", "keyword", "decorator", "selfParameter", "clsParameter"]
_TOKEN_MODIFIERS = ["declaration", "definition", "readonly", "static", "async", "defaultLibrary", "builtin", "classMember", "parameter"]


class FragmentsServer(LanguageServer):
    def __init__(self) -> None:
        super().__init__(
            "fragments-lsp",
            "v0.1",
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )
        self._pyright: PyrightClient | None = None
        self._files: dict[str, _FileState | None] = {}
        self._debounce_tasks: dict[str, asyncio.Task[None]] = {}
        self._parse_errors: dict[str, types.Diagnostic | None] = {}
        self._pyright_diagnostics: dict[str, list[types.Diagnostic]] = {}

    def _on_pyright_notification(self, message: dict[str, Any]) -> None:
        if message.get("method") == "textDocument/publishDiagnostics":
            _ = asyncio.ensure_future(self._publish_diagnostics(message["params"]))

    async def _on_pyright_request(self, message: dict[str, Any]) -> object:
        if message["method"] == "workspace/configuration":
            items = message["params"]["items"]
            editor_configs = await self.get_configuration_async(
                types.ConfigurationParams(items=[types.ConfigurationItem(scope_uri=item.get("scopeUri"), section=item.get("section", "")) for item in items])
            )
            result: list[dict[str, object] | None] = []
            for item, config in zip(items, editor_configs):
                if item.get("section") == "python":
                    config = {**(config or {}), "pythonPath": sys.executable, "defaultInterpreterPath": sys.executable}
                result.append(config)  # type: ignore[arg-type]
            return result
        return None

    async def _publish_diagnostics(self, params: dict[str, Any]) -> None:
        uri = params["uri"]
        state = self._files.get(uri)
        remapped: list[types.Diagnostic] = []

        for raw_diagnostic in params["diagnostics"]:
            diagnostic = _converter.structure(raw_diagnostic, types.Diagnostic)
            if state is not None:
                remapped_range = state.transpiled_to_original_range(diagnostic.range)
                if remapped_range is None:
                    continue
                diagnostic = types.Diagnostic(
                    range=remapped_range,
                    message=diagnostic.message,
                    severity=diagnostic.severity,
                    code=diagnostic.code,
                    source=diagnostic.source,
                )
            remapped.append(diagnostic)

        self._pyright_diagnostics[uri] = remapped
        self._republish_diagnostics(uri)

    def _republish_diagnostics(self, uri: str) -> None:
        diagnostics = list(self._pyright_diagnostics.get(uri, []))
        parse_error = self._parse_errors.get(uri)
        if parse_error is not None:
            diagnostics.append(parse_error)
        self.publish_diagnostics(uri, diagnostics)


server = FragmentsServer()


def _remap_text_edits(text_edits: list[types.TextEdit], state: _FileState) -> list[types.TextEdit]:
    result: list[types.TextEdit] = []
    for edit in text_edits:
        remapped = state.transpiled_to_original_range(edit.range)
        if remapped is not None:
            edit.range = remapped
            result.append(edit)
    return result


def _parse_error_to_diagnostic(text: str, error: grammar.ParsingError) -> types.Diagnostic:
    line_starts = _build_line_starts(text)
    position = _offset_to_position(line_starts, min(error.source_start, max(0, len(text) - 1)))
    return types.Diagnostic(
        range=types.Range(start=position, end=position),
        message=str(error),
        severity=types.DiagnosticSeverity.Error,
        source="fragments",
    )


def _build_file_state(text: str) -> tuple[_FileState | None, str]:
    """Parse text and return (state, content_for_pyright).

    Returns (None, text) for pure Python files and (_FileState, transpiled) for fragment files.
    """
    if "<>" not in text:
        return None, text
    _, module = grammar.expect_module(Source.from_string(text))
    if not any(isinstance(child, ASTFragment) for child in module.children):
        return None, text
    module.transpile()
    return _FileState(text, module.transpiled_content, module), module.transpiled_content


def main() -> None:
    from fragments.lsp import completion, definition, hover, lifecycle, rename, semantic_tokens  # noqa: F401
    server.start_io()


if __name__ == "__main__":
    main()
