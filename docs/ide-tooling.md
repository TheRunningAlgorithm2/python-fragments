# IDE Tooling

Python Fragments ships a language server that provides type checking and autocompletion for fragment syntax inside `.py` files.

## Install the LSP

```bash
pip install python-fragments[lsp]
```

Then start the language server:

```bash
fragments-lsp
```

## VS Code

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
| `fragments.serverPath` | `fragments-lsp` | Path to the `fragments-lsp` executable. Override if it is not on your `PATH`. |
