"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
const python_extension_1 = require("@vscode/python-extension");
const node_1 = require("vscode-languageclient/node");
let currentState = "Inactive";
let client;
let clientStateListener;
let serverWatcher;
let statusItem;
let resolvedBinaryPath = "";
let pythonApi;
async function transition(state, detail = "") {
    currentState = state;
    updateStatusItem(detail);
    await enterState().catch((error) => {
        console.error(`Python Fragments: unhandled error in state ${state}:`, error);
    });
}
function updateStatusItem(detail) {
    statusItem.text = "Python Fragments";
    switch (currentState) {
        case "Inactive":
            statusItem.text = "";
            statusItem.detail = undefined;
            statusItem.busy = false;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "CheckingExtensionConflicts":
            statusItem.detail = "Checking for conflicts";
            statusItem.busy = true;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "LspConflictDetected":
            statusItem.detail = `Conflict detected: ${detail}`;
            statusItem.busy = false;
            statusItem.severity = vscode.LanguageStatusSeverity.Error;
            statusItem.command = { title: "Resolve Conflict", command: "fragments.resolveConflict" };
            return;
        case "LocatingFragmentsLsp":
            statusItem.detail = "Locating language server";
            statusItem.busy = true;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "FragmentsLspBinaryNotFound":
            statusItem.detail = `Not installed: ${detail}`;
            statusItem.busy = false;
            statusItem.severity = vscode.LanguageStatusSeverity.Warning;
            statusItem.command = { title: "Show installation instructions", command: "fragments.showInstallationInstructions" };
            return;
        case "StartingFragmentsLsp":
            statusItem.detail = "Starting";
            statusItem.busy = true;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "FragmentsLspRunning":
            statusItem.detail = "Ready";
            statusItem.busy = false;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "RestartingFragmentsLsp":
            statusItem.detail = "Restarting";
            statusItem.busy = true;
            statusItem.severity = vscode.LanguageStatusSeverity.Information;
            statusItem.command = undefined;
            return;
        case "FragmentsLspFailed":
            statusItem.detail = `Failed: ${detail}`;
            statusItem.busy = false;
            statusItem.severity = vscode.LanguageStatusSeverity.Error;
            statusItem.command = { title: "Restart", command: "fragments.restartLanguageServer" };
            return;
    }
}
async function enterState() {
    switch (currentState) {
        case "CheckingExtensionConflicts": return enterCheckingExtensionConflicts();
        case "LspConflictDetected": return enterLspConflictDetected();
        case "LocatingFragmentsLsp": return enterLocatingFragmentsLsp();
        case "FragmentsLspBinaryNotFound": return enterFragmentsLspBinaryNotFound();
        case "StartingFragmentsLsp": return enterStartingFragmentsLsp();
        case "FragmentsLspRunning": return enterFragmentsLspRunning();
        case "RestartingFragmentsLsp": return enterRestartingFragmentsLsp();
        case "FragmentsLspFailed": return enterFragmentsLspFailed();
        case "Inactive": return;
    }
}
async function enterCheckingExtensionConflicts() {
    const languageServer = vscode.workspace.getConfiguration("python").get("languageServer");
    const basedPyrightInstalled = vscode.extensions.getExtension("detachhead.basedpyright") !== undefined;
    if (currentState !== "CheckingExtensionConflicts")
        return;
    if (languageServer !== undefined && languageServer !== "None") {
        await transition("LspConflictDetected", `python.languageServer is set to "${languageServer}". Python Fragments must be the only active language server for Python files.`);
        return;
    }
    if (basedPyrightInstalled) {
        await transition("LspConflictDetected", `The BasedPyright extension is installed and active. Python Fragments must be the only active language server for Python files.`);
        return;
    }
    await transition("LocatingFragmentsLsp");
}
async function enterLspConflictDetected() {
    const choice = await vscode.window.showWarningMessage(`Python Fragments: ${statusItem.detail} Click "Resolve Conflict" in the Python Fragments status (bottom-right language indicator) to fix this.`, "Resolve Conflict");
    if (choice === "Resolve Conflict") {
        await resolveConflict();
    }
}
async function resolveConflict() {
    const languageServer = vscode.workspace.getConfiguration("python").get("languageServer");
    if (languageServer !== undefined && languageServer !== "None") {
        const choice = await vscode.window.showWarningMessage(`Disable the Python language server ("${languageServer}") to allow Python Fragments to run?`, "Disable", "Cancel");
        if (choice !== "Disable")
            return;
        await vscode.workspace.getConfiguration("python").update("languageServer", "None", vscode.ConfigurationTarget.Workspace);
    }
    if (vscode.extensions.getExtension("detachhead.basedpyright") !== undefined) {
        await vscode.window.showInformationMessage("Disable the BasedPyright extension for this workspace, then click Restart in the Python Fragments status (bottom-right language indicator).");
        return;
    }
    await transition("CheckingExtensionConflicts");
}
async function enterLocatingFragmentsLsp() {
    serverWatcher?.close();
    serverWatcher = undefined;
    const overridePath = vscode.workspace.getConfiguration("fragments").get("serverPath");
    if (overridePath) {
        resolvedBinaryPath = overridePath;
    }
    else {
        if (!pythonApi) {
            pythonApi = await python_extension_1.PythonExtension.api().catch(() => undefined);
        }
        if (currentState !== "LocatingFragmentsLsp")
            return;
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        const environmentPath = pythonApi?.environments.getActiveEnvironmentPath(workspaceFolder?.uri);
        if (!environmentPath?.path) {
            await transition("FragmentsLspBinaryNotFound", "No active Python environment found. Select an interpreter or set fragments.serverPath.");
            return;
        }
        resolvedBinaryPath = path.join(path.dirname(environmentPath.path), "fragments-lsp");
    }
    if (currentState !== "LocatingFragmentsLsp")
        return;
    if (fs.existsSync(resolvedBinaryPath)) {
        await transition("StartingFragmentsLsp", resolvedBinaryPath);
        return;
    }
    await transition("FragmentsLspBinaryNotFound", `fragments-lsp not found at: ${resolvedBinaryPath}\n\nRun: pip install python-fragments[lsp]`);
}
async function enterFragmentsLspBinaryNotFound() {
    const choice = await vscode.window.showWarningMessage(`Python Fragments: ${statusItem.detail}`, "Watch for Installation", "Dismiss");
    if (choice !== "Watch for Installation")
        return;
    const directory = path.dirname(resolvedBinaryPath);
    if (!fs.existsSync(directory))
        return;
    serverWatcher = fs.watch(directory, () => {
        if (!fs.existsSync(resolvedBinaryPath))
            return;
        serverWatcher?.close();
        serverWatcher = undefined;
        transition("StartingFragmentsLsp", resolvedBinaryPath);
    });
}
async function enterStartingFragmentsLsp() {
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    const serverOptions = {
        command: resolvedBinaryPath,
        options: { cwd: workspaceFolder?.uri.fsPath },
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "python" }],
        outputChannelName: "Python Fragments",
        // Disable the client's built-in restart behavior so our FSM owns the lifecycle.
        errorHandler: {
            error: () => ({ action: node_1.ErrorAction.Continue }),
            closed: () => ({ action: node_1.CloseAction.DoNotRestart }),
        },
    };
    client = new node_1.LanguageClient("python-fragments", "Python Fragments", serverOptions, clientOptions);
    try {
        await client.start();
    }
    catch (error) {
        if (currentState !== "StartingFragmentsLsp")
            return;
        const errorMessage = error instanceof Error ? error.message : String(error);
        client = undefined;
        await transition("FragmentsLspFailed", errorMessage);
        return;
    }
    if (currentState !== "StartingFragmentsLsp")
        return;
    await transition("FragmentsLspRunning");
}
async function enterFragmentsLspRunning() {
    if (!client)
        return;
    clientStateListener = client.onDidChangeState((event) => {
        if (currentState !== "FragmentsLspRunning")
            return;
        if (event.newState === node_1.State.Stopped) {
            transition("FragmentsLspFailed", "The server process exited unexpectedly.");
        }
    });
}
async function enterRestartingFragmentsLsp() {
    serverWatcher?.close();
    serverWatcher = undefined;
    clientStateListener?.dispose();
    clientStateListener = undefined;
    if (client) {
        // stop() throws if the server process has already died; swallow it since we're cleaning up regardless.
        await client.stop().catch(() => undefined);
        client = undefined;
    }
    await transition("CheckingExtensionConflicts");
}
async function enterFragmentsLspFailed() {
    clientStateListener?.dispose();
    clientStateListener = undefined;
    if (client) {
        // stop() throws if the server process has already died; swallow it since we're cleaning up regardless.
        await client.stop().catch(() => undefined);
        client = undefined;
    }
    const choice = await vscode.window.showErrorMessage(`Python Fragments LSP failed: ${statusItem.detail}`, "Restart");
    if (choice === "Restart") {
        await transition("CheckingExtensionConflicts");
    }
}
function activate(context) {
    statusItem = vscode.languages.createLanguageStatusItem("python-fragments.status", { language: "python" });
    statusItem.name = "Python Fragments";
    context.subscriptions.push(statusItem, vscode.commands.registerCommand("fragments.restartLanguageServer", () => {
        if (currentState === "FragmentsLspRunning" || currentState === "StartingFragmentsLsp") {
            transition("RestartingFragmentsLsp");
        }
        else {
            transition("CheckingExtensionConflicts");
        }
    }), vscode.commands.registerCommand("fragments.resolveConflict", resolveConflict), vscode.commands.registerCommand("fragments.showInstallationInstructions", () => {
        vscode.window.showInformationMessage("Run `pip install python-fragments[lsp]` in your active Python environment to install the Fragments language server.");
    }), vscode.workspace.onDidChangeConfiguration((event) => {
        if (event.affectsConfiguration("fragments.serverPath")) {
            if (currentState === "FragmentsLspRunning" || currentState === "StartingFragmentsLsp") {
                transition("RestartingFragmentsLsp");
            }
            else {
                transition("LocatingFragmentsLsp");
            }
            return;
        }
        if (event.affectsConfiguration("python.languageServer") && currentState === "LspConflictDetected") {
            transition("CheckingExtensionConflicts");
        }
    }));
    python_extension_1.PythonExtension.api().then((api) => {
        pythonApi = api;
        context.subscriptions.push(api.environments.onDidChangeActiveEnvironmentPath(() => {
            if (vscode.workspace.getConfiguration("fragments").get("serverPath"))
                return;
            if (currentState === "FragmentsLspRunning" || currentState === "StartingFragmentsLsp") {
                transition("RestartingFragmentsLsp");
                return;
            }
            if (currentState === "FragmentsLspBinaryNotFound" || currentState === "LocatingFragmentsLsp") {
                transition("LocatingFragmentsLsp");
            }
        }));
    }).catch(() => {
        // Python extension unavailable — fragments.serverPath override may still work.
    });
    transition("CheckingExtensionConflicts");
}
function deactivate() {
    serverWatcher?.close();
    return client?.stop();
}
//# sourceMappingURL=extension.js.map