# Running Python Commands

Activate the venv with `source venv/bin/activate` before running Python or pip commands. Run it once at the start of a multi-command sequence rather than chaining it with `&&` on every line.

# Coding Style

- **Never abbreviate names.** Write `original` not `orig`, `transpiled` not `trans`, `interpolation` not `interp`, `expression` not `expr`, `offset` not `off`, etc. Full words everywhere — variables, parameters, methods, and local names.

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
- Transpiles each file on open/change and stores a `_FileState` (original source, transpiled source, parsed `ASTModule`, precomputed line-start offset arrays)
- Forwards all document requests to a `PyrightClient` (`fragments/lsp/pyright.py`) subprocess after remapping positions from original→transpiled coordinates
- Remaps results (diagnostics, hover ranges, completion text edits, semantic tokens) back from transpiled→original coordinates before returning to the editor

Key design decisions:
- **No `[tool.basedpyright]` in `pyproject.toml`** — basedpyright config (type checking mode, paths, etc.) comes from the editor's normal workspace settings via `workspace/configuration` passthrough. The server forwards all `workspace/configuration` requests from basedpyright to the editor via `get_configuration_async`, only injecting `pythonPath`/`defaultInterpreterPath` for the `"python"` section.
- **AST-based source map** — after `module.transpile()`, every AST node carries `source_start/source_end` and `transpiled_start/transpiled_end`. Position mapping walks the AST directly: `ASTPython` nodes map 1:1, `ASTInterpolation` nodes map their expression text 1:1 (skipping the `{{ }}` delimiters), and all fragment structure syntax is unmappable (returns `None`). `None` results silently drop tokens/diagnostics that live in untranslatable regions.
- **Line-start offset arrays** — stored in `_FileState.__post_init__` for O(1) offset lookup and O(log N) position lookup via `bisect`.

# VS Code Extension Architecture

The extension (`vscode-extension/`) has two layers:

1. **TextMate grammar** (`syntaxes/fragments.tmLanguage.json`) — syntactic highlighting for fragment syntax (`<>`, `</>`, tags, `{{ }}`). Injected with `L:source.python` (the `L:` prefix means prepend/higher priority — do not remove it). The interpolation rule does **not** include `source.python` patterns; semantic tokens cover interpolation content.

2. **LSP client** — starts `fragments-lsp` and connects it as a `LanguageClient`. Pyright's semantic tokens provide type-aware highlighting for Python code; the TextMate grammar provides structural highlighting for fragment syntax. These two layers are complementary and non-overlapping.
