# Running Python Commands

The venv is already activated. **Never run `. venv/bin/activate` or `source venv/bin/activate`.** Run Python commands directly. The venv is in `venv/` if you need to reference executables directly (`venv/bin/python`, `venv/bin/pip`, etc.).

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

The `docs/` directory contains full project documentation built with MkDocs. At the start of any new task, read every single page in docs.

# LSP Architecture

Key design decisions:

- **No `[tool.basedpyright]` in `pyproject.toml`** — basedpyright config (type checking mode, paths, etc.) comes from the editor's normal workspace settings via `workspace/configuration` passthrough. The server forwards all `workspace/configuration` requests from basedpyright to the editor via `get_configuration_async`, only injecting `pythonPath`/`defaultInterpreterPath` for the `"python"` section.
- **AST-based source map** — after `module.transpile()`, every AST node carries `source_start/source_end` and `transpiled_start/transpiled_end`. Position mapping walks the AST directly: `ASTPython` nodes map 1:1, `ASTInterpolation` nodes map their expression text 1:1 (skipping the `{{ }}` delimiters), and all fragment structure syntax is unmappable (returns `None`). `None` results silently drop tokens/diagnostics that live in untranslatable regions.

# VS Code Extension Architecture

The extension (`vscode-extension/`) has two layers:

1. **TextMate grammar** (`syntaxes/fragments.tmLanguage.json`) — syntactic highlighting for fragment syntax (`<>`, `</>`, tags, `{{ }}`). Injected with `L:source.python` (the `L:` prefix means prepend/higher priority — do not remove it). The interpolation rule does **not** include `source.python` patterns; semantic tokens cover interpolation content.

2. **LSP client** — starts `fragments-lsp` and connects it as a `LanguageClient`. Pyright's semantic tokens provide type-aware highlighting for Python code; the TextMate grammar provides structural highlighting for fragment syntax. These two layers are complementary and non-overlapping.
