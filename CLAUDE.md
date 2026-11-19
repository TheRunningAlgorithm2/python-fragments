# Coding Style

- **Never abbreviate names.** Write `original` not `orig`, `transpiled` not `trans`, `interpolation` not `interp`, `expression` not `expr`, `offset` not `off`, etc. Full words everywhere — variables, parameters, methods, and local names.
- **Use guard clauses.** Prefer early returns over wrapping code in if blocks. Write `if not condition: return` rather than `if condition: { ... }`.
- **Never use `# type: ignore` comments.** Fix the type error properly — correct the type annotation, use the right type, or restructure the code so the types are accurate. A `# type: ignore` is always a sign that the types are wrong, not that the type checker is wrong.
- **Always add type annotations** You must always add type annotations, it is not acceptible to use `object` and `Any` should always be used sparingly. It is almost never correct.

# Overview

This project is a transpiler designed to bring HTML into Python, similar to how Babel and JSX brings HTML into JavaScript.

# Project Structure

This repo contains:

* The transpiler library code (in `fragments/`)
* Example implementations in `examples/`
* Documentation in `docs/`
* VS Code extension in `vscode-extension/`

# Docs

The `docs/` directory contains full project documentation built with MkDocs. Refer to it as the canonical reference for project behaviour and design decisions.

# LSP Architecture

Key design decisions:

- **No `[tool.basedpyright]` in `pyproject.toml`** — basedpyright config (type checking mode, paths, etc.) comes from the editor's normal workspace settings via `workspace/configuration` passthrough. The server forwards all `workspace/configuration` requests from basedpyright to the editor via `get_configuration_async`, only injecting `pythonPath`/`defaultInterpreterPath` for the `"python"` section.
- **Writer-built source map**: AST nodes only carry `source_start/source_end`. `module.transpile(writer)` emits code through a `TranspiledCodeWriter` (`fragments/transpiled_code_writer.py`): `write()` adds transpiler-generated scaffolding, and `map()` copies a source span verbatim while recording a `Segment`. The writer tracks transpiled offsets itself, so nodes never compute them. `writer.source_map()` returns a `SourceMap` (`fragments/source_map.py`) that translates offsets in both directions. Only `ASTPython` code, interpolation expression text (without the `{{ }}` delimiters), component names and component argument names are mapped. All other fragment syntax is unmappable (returns `None`). `None` results silently drop tokens/diagnostics that live in untranslatable regions.

# VS Code Extension Architecture

The extension (`vscode-extension/`) has two layers:

1. **TextMate grammar** (`syntaxes/fragments.tmLanguage.json`) — syntactic highlighting for fragment syntax (`<>`, `</>`, tags, `{{ }}`). Injected with `L:source.python` (the `L:` prefix means prepend/higher priority — do not remove it). The interpolation rule includes `source.python` for baseline highlighting, which Pyright's semantic tokens then refine. `<script>` and `<style>` bodies embed `source.js` and `source.css`; they are never mapped to Python, so TextMate is their only highlighting layer.

2. **LSP client** — starts `fragments-lsp` and connects it as a `LanguageClient`. Pyright's semantic tokens provide type-aware highlighting for Python code; the TextMate grammar provides structural highlighting for fragment syntax. Semantic tokens take precedence wherever both apply.
