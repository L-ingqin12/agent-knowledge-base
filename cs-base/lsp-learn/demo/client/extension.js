/**
 * Demo LSP Client — VSCode Extension
 *
 * Launches the demo-lsp server and connects it to VSCode's LSP client API.
 *
 * To use:
 * 1. Open this folder in VSCode
 * 2. Press F5 to launch Extension Development Host
 * 3. Open any .demo file — the server activates automatically
 */
const vscode = require("vscode");
const path = require("path");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

/** @type {LanguageClient} */
let client = null;

/**
 * Called when the extension is activated.
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    const config = vscode.workspace.getConfiguration("demoLsp");
    const modulePath = context.asAbsolutePath(
        path.join("..", "server", "server.py")
    );

    const serverOptions = {
        command: config.get("serverPath", "python"),
        args: [modulePath],
        options: { cwd: path.dirname(modulePath) },
    };

    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "demo" }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher("**/*.demo"),
        },
        outputChannelName: "Demo LSP",
        traceOutputChannelName: "Demo LSP (Trace)",
    };

    client = new LanguageClient(
        "demoLsp",
        "Demo LSP Server",
        serverOptions,
        clientOptions
    );

    vscode.window.showInformationMessage("Demo LSP Client activated 🚀");

    context.subscriptions.push(
        vscode.commands.registerCommand("demoLsp.restart", async () => {
            if (client) {
                await client.stop();
                await client.start();
                vscode.window.showInformationMessage("Demo LSP restarted");
            }
        })
    );

    client.start();
}

function deactivate() {
    if (client) {
        return client.stop();
    }
}

module.exports = { activate, deactivate };
