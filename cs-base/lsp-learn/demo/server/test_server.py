"""
Tests for the Demo LSP server.
Run: python -m pytest server/test_server.py -v
"""

import json
import subprocess
import sys
import time
import pytest


# ---------------------------------------------------------------------------
# Helpers — LSP protocol framing
# ---------------------------------------------------------------------------

def _send(proc, payload: dict) -> dict:
    """Send a JSON-RPC message to the LSP server and return the response."""
    body = json.dumps(payload)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    proc.stdin.write((header + body).encode())
    proc.stdin.flush()

    # Read the response header
    headers = {}
    while True:
        line = proc.stdout.readline().decode()
        if line == "\r\n":
            break
        key, _, val = line.partition(":")
        headers[key.strip()] = val.strip()

    content_length = int(headers.get("Content-Length", 0))
    body = proc.stdout.read(content_length).decode()
    return json.loads(body)


def _notify(proc, method: str, params: dict):
    """Send a notification (no id) to the LSP server."""
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
    header = f"Content-Length: {len(body)}\r\n\r\n"
    proc.stdin.write((header + body).encode())
    proc.stdin.flush()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def lsp_process():
    """Start the demo LSP server as a subprocess."""
    proc = subprocess.Popen(
        [sys.executable, "server/server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="server",
    )

    # Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": "file:///test",
            "capabilities": {},
        },
    }
    resp = _send(proc, init_req)
    assert "capabilities" in resp["result"]
    assert "completionProvider" in resp["result"]["capabilities"]

    # Send initialized notification
    _notify(proc, "initialized", {})

    yield proc

    # Shutdown
    _send(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown", "params": {}})
    _notify(proc, "exit", {})
    proc.terminate()
    proc.wait(timeout=5)


def _open_doc(proc, uri: str, text: str):
    _notify(proc, "textDocument/didOpen", {
        "textDocument": {
            "uri": uri,
            "languageId": "demo",
            "version": 1,
            "text": text,
        }
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_initialize_capabilities(lsp_process):
    """Server should declare its capabilities on initialize."""
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 100,
        "method": "initialize",
        "params": {"processId": None, "rootUri": "file:///test2", "capabilities": {}},
    })
    caps = resp["result"]["capabilities"]
    assert caps["completionProvider"] is not None
    assert caps["hoverProvider"] is True
    assert caps["definitionProvider"] is True
    assert caps["documentSymbolProvider"] is True


def test_completion_empty_prefix(lsp_process):
    """With empty prefix, all completions should be returned."""
    _open_doc(lsp_process, "file:///test.demo", "\n")
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "textDocument/completion",
        "params": {
            "textDocument": {"uri": "file:///test.demo"},
            "position": {"line": 0, "character": 0},
        },
    })
    items = resp["result"]["items"]
    assert len(items) > 0
    labels = {i["label"] for i in items}
    assert "fn" in labels
    assert "let" in labels
    assert "println" in labels


def test_completion_filter_by_prefix(lsp_process):
    """Typing 'pri' should only return completions starting with 'pri'."""
    _open_doc(lsp_process, "file:///test.demo", "pri\n")
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "textDocument/completion",
        "params": {
            "textDocument": {"uri": "file:///test.demo"},
            "position": {"line": 0, "character": 3},
        },
    })
    items = resp["result"]["items"]
    labels = {i["label"] for i in items}
    assert "print" in labels
    assert "println" in labels
    assert "fn" not in labels  # Should be filtered out


def test_hover_on_keyword(lsp_process):
    """Hovering over 'fn' should return markdown documentation."""
    _open_doc(lsp_process, "file:///test.demo", "fn main() {\n}\n")
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": "file:///test.demo"},
            "position": {"line": 0, "character": 1},
        },
    })
    result = resp.get("result")
    assert result is not None
    assert "fn" in result["contents"]["value"]


def test_hover_unknown_word(lsp_process):
    """Hovering over an unknown word should return null."""
    _open_doc(lsp_process, "file:///test.demo", "xyz unknown\n")
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "textDocument/hover",
        "params": {
            "textDocument": {"uri": "file:///test.demo"},
            "position": {"line": 0, "character": 2},
        },
    })
    assert resp.get("result") is None


def test_definition_jumps_to_fn(lsp_process):
    """Go-to-definition on a function call should find the fn declaration."""
    code = "fn greet() {\n}\n\nfn main() {\n    greet();\n}\n"
    _open_doc(lsp_process, "file:///test.demo", code)
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "textDocument/definition",
        "params": {
            "textDocument": {"uri": "file:///test.demo"},
            "position": {"line": 4, "character": 5},  # On "greet" in greet()
        },
    })
    result = resp.get("result")
    assert result is not None
    loc = result if isinstance(result, dict) else result[0]
    # Definition should be on line 0
    assert loc["range"]["start"]["line"] == 0


def test_document_symbols(lsp_process):
    """Document symbols should list functions and structs."""
    code = "fn alpha() {}\nstruct Beta {}\nfn gamma() {}\n"
    _open_doc(lsp_process, "file:///test.demo", code)
    resp = _send(lsp_process, {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "textDocument/documentSymbol",
        "params": {"textDocument": {"uri": "file:///test.demo"}},
    })
    symbols = resp.get("result")
    assert symbols is not None
    names = {s["name"] for s in symbols}
    assert "fn alpha" in names
    assert "struct Beta" in names
    assert "fn gamma" in names


def test_diagnostic_long_line(lsp_process):
    """Lines longer than 100 characters should produce a warning diagnostic."""
    long_line = "x" * 120
    _open_doc(lsp_process, "file:///test.demo", long_line + "\n")

    # Diagnostics are published asynchronously via notification.
    # We need to read the notification from stdout.
    import select

    # Try to read a notification for up to 2 seconds
    start = time.time()
    notification = None
    while time.time() - start < 2:
        ready, _, _ = select.select([lsp_process.stdout], [], [], 0.1)
        if ready:
            # Read header
            headers = {}
            while True:
                line = lsp_process.stdout.readline().decode()
                if line == "\r\n":
                    break
                key, _, val = line.partition(":")
                headers[key.strip()] = val.strip()
            content_length = int(headers.get("Content-Length", 0))
            body = lsp_process.stdout.read(content_length).decode()
            msg = json.loads(body)
            if msg.get("method") == "textDocument/publishDiagnostics":
                notification = msg
                break

    assert notification is not None, "No diagnostics notification received"
    diags = notification["params"]["diagnostics"]
    assert len(diags) >= 1
    assert any("100" in d["message"] for d in diags)
