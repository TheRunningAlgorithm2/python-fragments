# VS Code

Type checking, completions, hover docs, go-to-definition, and rename work out of the box.

![VS Code completions demo](../assets/vscode.gif)

## Installation

Install the extension from the [VS Code Extension Marketplace]().

Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and select the interpreter for the environment where `python-fragments[lsp]` is installed. The extension will automatically start `fragments-lsp` from that environment.

If a conflicting Python language server (such as Pylance) is active, the extension will prompt you to disable it on first activation.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `fragments.serverPath` | _(derived from active interpreter)_ | Override path to the `fragments-lsp` executable. Only needed if auto-detection fails. |
