# VS Code

Type checking, completions, hover docs, go-to-definition, and rename work out of the box.

![VS Code completions demo](../assets/vscode.gif)

## Installation

Install the [Python Fragments extension](https://marketplace.visualstudio.com/items?itemName=tra-technologies-ltd.python-fragments) from the VS Code Marketplace.

Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and select the interpreter for the environment where `python-fragments[lsp]` is installed. The extension will automatically start `fragments-lsp` from that environment.

If a conflicting Python language server (such as Pylance) is active, the extension will prompt you to disable it on first activation.

### Building from source

To build and install the extension manually:

```bash
npm install -g @vscode/vsce
cd vscode-extension
npm install
vsce package
code --install-extension <filename>.vsix
```

## Configuration

| Setting | Default | Description |
|---|---|---|
| `fragments.serverPath` | _(derived from active interpreter)_ | Override path to the `fragments-lsp` executable. Only needed if auto-detection fails. |
