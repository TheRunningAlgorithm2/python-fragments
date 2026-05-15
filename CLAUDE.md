# Overview

This project is a transpiler designed to bring HTML into Python, similar to how Babel and JSX brings HTML into JavaScript.

# Project Structure

This repo contains:

* The transpiler library code (in `fragments/`)
* Example implementations in `examples/`
* Documentation in `docs/`
* VS Code extension in `vscode-extension/`

# Docs

The `docs/` directory contains full project documentation built with MkDocs. At the start of any new task, read whichever docs pages are relevant to what you're working on before making changes.

# LSP Architecture

The LSP stack is: **Editor ↔ pygls `FragmentsServer` ↔ basedpyright subprocess**.

`FragmentsServer` (`fragments/lsp/server.py`) is a pygls `LanguageServer` that:
- Transpiles each file on open/change and stores a `_FileState` (original source, transpiled source, source-map segments, precomputed line-start offset arrays)
- Forwards all document requests to a `PyrightClient` (`fragments/lsp/pyright.py`) subprocess after remapping positions from original→transpiled coordinates
- Remaps results (diagnostics, hover ranges, completion text edits, semantic tokens) back from transpiled→original coordinates before returning to the editor

Key design decisions:
- **No `[tool.basedpyright]` in `pyproject.toml`** — basedpyright config (type checking mode, paths, etc.) comes from the editor's normal workspace settings via `workspace/configuration` passthrough. The server forwards all `workspace/configuration` requests from basedpyright to the editor via `get_configuration_async`, only injecting `pythonPath`/`defaultInterpreterPath` for the `"python"` section.
- **Source map segments** — `transpile_with_map` returns `Segment(orig_start, orig_end, trans_start, trans_end)` objects. `orig_to_trans` returns `None` inside fragment syntax blocks; `trans_to_orig` returns `None` inside transpiled fragment boilerplate. Both return `None` results are used to silently drop tokens/diagnostics that live in untranslatable regions.
- **Line-start offset arrays** — stored in `_FileState.__post_init__` for O(1) offset lookup and O(log N) position lookup via `bisect`. Never call the module-level `to_offset`/`to_position` from `source_map.py` inside the server's hot paths.

# VS Code Extension Architecture

The extension (`vscode-extension/`) has two layers:

1. **TextMate grammar** (`syntaxes/fragments.tmLanguage.json`) — syntactic highlighting for fragment syntax (`<>`, `</>`, tags, `{{ }}`). Injected with `L:source.python` (the `L:` prefix means prepend/higher priority — do not remove it). The interpolation rule does **not** include `source.python` patterns; semantic tokens cover interpolation content.

2. **LSP client** — starts `fragments-lsp` and connects it as a `LanguageClient`. Pyright's semantic tokens provide type-aware highlighting for Python code; the TextMate grammar provides structural highlighting for fragment syntax. These two layers are complementary and non-overlapping.
