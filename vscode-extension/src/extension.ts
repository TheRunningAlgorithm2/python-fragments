import * as path from "path";
import * as vscode from "vscode";
import { PythonExtension } from "@vscode/python-extension";
import { LanguageClient, LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";

let client: LanguageClient | undefined;

async function checkPylanceConflict(): Promise<void> {
  const languageServer = vscode.workspace.getConfiguration("python").get<string>("languageServer");
  if (languageServer === "None") return;

  const choice = await vscode.window.showWarningMessage(
    "Python Fragments detected an active Python language server that will conflict with it. Would you like to disable it?",
    "Yes",
    "No"
  );

  if (choice === "Yes") {
    await vscode.workspace.getConfiguration("python").update("languageServer", "None", vscode.ConfigurationTarget.Workspace);
  }
}

async function restart(workspaceFolder: vscode.WorkspaceFolder | undefined, pythonApi: PythonExtension): Promise<void> {
  if (client) {
    await client.stop();
    client = undefined;
  }

  const override = vscode.workspace.getConfiguration("fragments").get<string>("serverPath");
  let serverPath: string;
  if (override) {
    serverPath = override;
  } else {
    const envPath = pythonApi.environments.getActiveEnvironmentPath(workspaceFolder?.uri);
    if (!envPath?.path) return;
    serverPath = path.join(path.dirname(envPath.path), "fragments-lsp");
  }

  const serverOptions: ServerOptions = {
    command: serverPath,
    options: { cwd: workspaceFolder?.uri.fsPath },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "python" }],
    outputChannelName: "Python Fragments",
  };

  client = new LanguageClient("python-fragments", "Python Fragments", serverOptions, clientOptions);
  client.start();
}

export function activate(context: vscode.ExtensionContext): void {
  checkPylanceConflict();

  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];

  PythonExtension.api().then((pythonApi) => {
    restart(workspaceFolder, pythonApi);
    context.subscriptions.push(
      pythonApi.environments.onDidChangeActiveEnvironmentPath(() => restart(workspaceFolder, pythonApi))
    );
  });
}

export function deactivate(): Thenable<void> | undefined {
  return client?.stop();
}
