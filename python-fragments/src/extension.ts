import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from "vscode-languageclient/node";

export function activate(context: vscode.ExtensionContext) {
  console.log("[python-fragments] Activating...");
  const pythonPath = vscode.workspace.getConfiguration("python").get<string>("defaultInterpreterPath") || "python3";
  const serverOptions: ServerOptions = {
    command: "/home/matt/python-fragments/venv/bin/python",
    args: ["/home/matt/python-fragments/lsp.py"],
    transport: TransportKind.stdio,
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [
      { scheme: "file", language: "python-fragments" },
      { scheme: "file", pattern: "**/*.pyf" },
    ],
  };

  const client = new LanguageClient("python-fragments", "Python Fragments Language Server", serverOptions, clientOptions);
  client.start();
  context.subscriptions.push({ dispose: () => client.stop() });
  console.log("[python-fragments] Language client started");
}
