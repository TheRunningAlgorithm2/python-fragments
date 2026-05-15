"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const node_1 = require("vscode-languageclient/node");
let client;
function activate(context) {
    const config = vscode.workspace.getConfiguration("fragments");
    const serverPath = config.get("serverPath", "fragments-lsp");
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const serverOptions = {
        command: serverPath,
        options: { cwd: workspaceRoot },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "python" }],
        outputChannelName: "Python Fragments",
    };
    client = new node_1.LanguageClient("python-fragments", "Python Fragments", serverOptions, clientOptions);
    client.start();
}
function deactivate() {
    return client?.stop();
}
//# sourceMappingURL=extension.js.map