# Language Server

Type checking, completions, hover docs, go-to-definition, and rename work out of the box.

![VS Code completions demo](../assets/vscode.gif)


## Features

- **Diagnostics** — type errors and undefined names reported inline
- **Hover** — type information and docstrings on hover
- **Completions** — attribute, method, and name completions including trigger-on-dot
- **Semantic tokens** — type-aware syntax highlighting for Python code inside fragments
- **Syntax highlighting** — structural highlighting for `<>`, tags, and `{{ }}` interpolations
- **Go-to-definition** — jump to the definition of a symbol
- **Find references** — list all usages of a symbol
- **Rename** — rename a symbol across all files in the workspace

All features work on component names and attribute names in component tags — go-to-definition on `<Layout>` jumps to the function, rename propagates across all usages, hover shows parameter types.

Not yet implemented:

- **Fragments-specific syntax** — autocompletion and syntax highlighting for fragments blocks

## Installation

```bash
pip install python-fragments[lsp]
```

Then start the language server:

```bash
fragments-lsp
```
