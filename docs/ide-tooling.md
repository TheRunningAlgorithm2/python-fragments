# IDE Tooling

Python Fragments ships a language server and VS Code extension that provide full IDE support for fragment syntax inside `.py` files.

## Features

- **Diagnostics** — type errors and undefined names reported inline
- **Hover** — type information and docstrings on hover
- **Completions** — attribute, method, and name completions including trigger-on-dot
- **Semantic tokens** — type-aware syntax highlighting for Python code inside fragments
- **Syntax highlighting** — structural highlighting for `<>`, tags, and `{{ }}` interpolations

Not yet implemented:

- **Go-to-definition** — jump to the definition of a symbol
- **Find references** — list all usages of a symbol
- **Rename** — rename a symbol across the file
- **Fragments-specific syntax** — autocompletion and syntax highlighting for fragments blocks

## Install the LSP

```bash
pip install python-fragments[lsp]
```

Then start the language server:

```bash
fragments-lsp
```

## VS Code

Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and select the interpreter for the environment where `python-fragments[lsp]` is installed. The extension will automatically start `fragments-lsp` from that environment.

If a conflicting Python language server (such as Pylance) is active, the extension will prompt you to disable it on first activation.

Install the extension from the `vscode-extension/` directory:

```bash
cd vscode-extension
npm install
npm run compile
```

Then open the folder in VS Code and press `F5` to launch a development host, or package and install it manually.

### Configuration

| Setting | Default | Description |
|---|---|---|
| `fragments.serverPath` | _(derived from active interpreter)_ | Override path to the `fragments-lsp` executable. Only needed if auto-detection fails. |
