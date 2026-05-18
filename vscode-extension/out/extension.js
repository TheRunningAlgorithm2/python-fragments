"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const python_extension_1 = require("@vscode/python-extension");
const node_1 = require("vscode-languageclient/node");
let client;
let serverWatcher;
async function checkPylanceConflict() {
    const languageServer = vscode.workspace.getConfiguration("python").get("languageServer");
    if (languageServer === "None")
        return;
    const choice = await vscode.window.showWarningMessage("Python Fragments detected an active Python language server that will conflict with it. Would you like to disable it?", "Yes", "No");
    if (choice === "Yes") {
        await vscode.workspace.getConfiguration("python").update("languageServer", "None", vscode.ConfigurationTarget.Workspace);
    }
}
function watchForServer(serverPath, workspaceFolder, pythonApi) {
    serverWatcher?.close();
    const directory = path.dirname(serverPath);
    if (!fs.existsSync(directory))
        return;
    serverWatcher = fs.watch(directory, () => {
        if (fs.existsSync(serverPath)) {
            serverWatcher?.close();
            serverWatcher = undefined;
            restart(workspaceFolder, pythonApi);
        }
    });
}
async function restart(workspaceFolder, pythonApi) {
    serverWatcher?.close();
    serverWatcher = undefined;
    if (client) {
        await client.stop();
        client = undefined;
    }
    const override = vscode.workspace.getConfiguration("fragments").get("serverPath");
    let serverPath;
    if (override) {
        serverPath = override;
    }
    else {
        const envPath = pythonApi.environments.getActiveEnvironmentPath(workspaceFolder?.uri);
        if (!envPath?.path)
            return;
        serverPath = path.join(path.dirname(envPath.path), "fragments-lsp");
    }
    if (!fs.existsSync(serverPath)) {
        const choice = await vscode.window.showWarningMessage("`fragments-lsp` was not found in the active Python environment. Run `pip install python-fragments[lsp]` to enable language features.", "Restart Once Installed", "Dismiss");
        if (choice === "Restart Once Installed") {
            watchForServer(serverPath, workspaceFolder, pythonApi);
        }
        return;
    }
    const serverOptions = {
        command: serverPath,
        options: { cwd: workspaceFolder?.uri.fsPath },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "python" }],
        outputChannelName: "Python Fragments",
    };
    client = new node_1.LanguageClient("python-fragments", "Python Fragments", serverOptions, clientOptions);
    client.start();
}
function activate(context) {
    checkPylanceConflict();
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    python_extension_1.PythonExtension.api().then((pythonApi) => {
        restart(workspaceFolder, pythonApi);
        context.subscriptions.push(pythonApi.environments.onDidChangeActiveEnvironmentPath(() => restart(workspaceFolder, pythonApi)), vscode.commands.registerCommand("fragments.restartLanguageServer", () => restart(workspaceFolder, pythonApi)));
    });
}
function deactivate() {
    serverWatcher?.close();
    return client?.stop();
}
//# sourceMappingURL=extension.js.map