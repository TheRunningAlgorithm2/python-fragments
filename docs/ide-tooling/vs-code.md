# VS Code

## Language Server

Install the extension from the `vscode-extension/` directory:

```bash
cd vscode-extension
npm install
npm run compile
```

Then open the folder in VS Code and press `F5` to launch a development host, or package and install it manually.

Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and select the interpreter for the environment where `python-fragments[lsp]` is installed. The extension will automatically start `fragments-lsp` from that environment.

If a conflicting Python language server (such as Pylance) is active, the extension will prompt you to disable it on first activation.

### Configuration

| Setting | Default | Description |
|---|---|---|
| `fragments.serverPath` | _(derived from active interpreter)_ | Override path to the `fragments-lsp` executable. Only needed if auto-detection fails. |

## Emmet

Emmet abbreviations work inside fragment blocks. The extension configures VS Code to activate Emmet's HTML mode within `<>...</>` regions automatically.

One limitation: Emmet's `.` class shorthand always expands to `class="..."`, but Python Fragments uses `classes="..."` (since `class` is a reserved keyword in Python). Use the explicit attribute syntax instead:

```
div[classes="container"]
```

rather than `div.container`.
