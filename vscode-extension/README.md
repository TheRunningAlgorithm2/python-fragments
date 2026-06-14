# Python Fragments Extension for VS Code

VS Code extension for the [Python Fragments](https://github.com/TheRunningAlgorithm2/python-fragments) transpiler - bringing HTML syntax directly into Python, similar to how JSX brings HTML into JavaScript.

![VS Code completions demo](https://raw.githubusercontent.com/TheRunningAlgorithm2/python-fragments/main/docs/assets/vscode.gif)

## Features

- Syntax highlighting for fragment syntax (`<>`, `</>`, tags, `{{ }}` interpolations)
- Full LSP support via `fragments-lsp`: diagnostics, hover, go-to-definition, completions, and semantic tokens powered by Pyright

## Requirements

The `fragments-lsp` language server must be installed in your Python environment:

```
pip install fragments-lsp
```

The extension discovers the language server automatically from the Python interpreter selected in the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

## Usage

Open any `.py` file that uses fragment syntax. The extension activates automatically for Python files.

## Configuration

| Setting | Description |
|---|---|
| `fragments.serverPath` | Override the path to the `fragments-lsp` executable. By default it is derived from the active Python interpreter. |

## Commands

| Command | Description |
|---|---|
| `Python Fragments: Restart Language Server` | Restart the LSP if it gets into a bad state. |
