# Demo LSP — A Minimal Language Server

A working LSP (Language Server Protocol) implementation built with Python and **pygls**, paired with a VSCode client extension.

## What This Demo Demonstrates

| Feature | Protocol Method | What It Does |
|---------|----------------|--------------|
| **Completion** | `textDocument/completion` | Suggests keywords, functions, types as you type |
| **Diagnostics** | `textDocument/publishDiagnostics` | Warns about lines > 100 chars and trailing whitespace |
| **Hover** | `textDocument/hover` | Shows Markdown docs when hovering over keywords |
| **Go to Definition** | `textDocument/definition` | Jumps to function/struct declarations |
| **Document Symbols** | `textDocument/documentSymbol` | Lists all functions and structs (outline) |

## Project Structure

```
demo/
├── server/
│   ├── server.py          # LSP server (the core)
│   └── test_server.py     # Integration tests
├── client/
│   ├── package.json       # VSCode extension manifest
│   ├── extension.js       # VSCode client (launches the server)
│   ├── language-configuration.json
│   └── syntaxes/
│       └── demo.tmLanguage.json   # Syntax highlighting
├── example.demo           # Sample .demo file to test with
└── requirements.txt
```

## Quick Start

### 1. Install Dependencies

```bash
cd demo
pip install -r requirements.txt
```

### 2. Run the Server (standalone test)

```bash
# Start the server via stdio
python server/server.py
```

Then type a JSON-RPC message manually:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":"file:///tmp","capabilities":{}}}' | python server/server.py
```

### 3. Run Tests

```bash
cd demo
python -m pytest server/test_server.py -v
```

### 4. Use in VSCode

1. Open the `demo/` folder in VSCode
2. Press `F5` to launch the Extension Development Host
3. Open `example.demo` or create a new `.demo` file
4. Start typing — completions, hover, and diagnostics work automatically

### 5. Use in Neovim

Add to your Neovim config:

```lua
local lspconfig = require('lspconfig')

local configs = require('lspconfig.configs')
configs.demo_lsp = {
    default_config = {
        cmd = { 'python', '/absolute/path/to/demo/server/server.py' },
        filetypes = { 'demo' },
        root_dir = function(fname)
            return vim.fn.getcwd()
        end,
        settings = {},
    },
}
lspconfig.demo_lsp.setup({})
```

## The .demo Language

A toy language designed to showcase LSP features. Syntax:

```
// Comments
fn function_name(param: type) -> type {
    let var = value;
    return var;
}

struct TypeName {
    field: type,
}

impl TypeName {
    fn method(&self) { }
}
```

Built-in types: `str`, `i32`, `u32`, `bool`, `f64`, `void`
Built-in functions: `print`, `println`, `format`, `read`
