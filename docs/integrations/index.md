# Integrations

Most Python tooling can't parse fragment syntax: running a formatter or linter directly on a file containing `<>...</>` fails. Integrations connect Fragments to these tools, so they work on the Python in your fragment files without breaking the fragments.

Each integration is an optional extra. You only install the tools you use.

| Category   | Tool                          | Extra                        | Command           |
| ---------- | ----------------------------- | ---------------------------- | ----------------- |
| Formatting | [Black](formatting/black.md)  | `python-fragments[black]`    | `fragments black` |

Integrations are available in three places:

- **Command line** — through the `fragments` command.
- **Editors** — through the [language server](../getting-started/lsp.md) and the [VS Code extension](../getting-started/vs-code.md).
- **Pre-commit** — through hooks published from this repository.

Each integration page says which of its tool's features are supported.

More integrations, including Ruff and import sorting, are on the [roadmap](../roadmap.md).
