---
title: 实现一个简单的 LSP 服务器
aliases: [LSP 服务器实现, pygls 实战, LSP Server 开发]
tags: [cs/toolchain, cs]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# 实现一个简单的 LSP 服务器

## 选择实现语言

LSP 是语言无关的协议，可以用任何语言实现。常用选择：

| 语言 | 推荐库 | 说明 |
|------|--------|------|
| TypeScript/JavaScript | [vscode-languageserver-node](https://github.com/Microsoft/vscode-languageserver-node) | Microsoft 官方，VSCode 同款 |
| TypeScript | [langium](https://github.com/langium/langium) | 从语法定义直接生成 LSP 服务器 + 客户端 |
| Python | [pygls](https://github.com/openlawlibrary/pygls) | 最流行的 Python LSP 框架 |
| Java | [lsp4j](https://github.com/eclipse/lsp4j) | Eclipse 官方，Java 生态最成熟 |
| Rust | [tower-lsp](https://github.com/ebkalderon/tower-lsp) | 基于 Tower 的异步 LSP 框架 |
| Rust | [lsp-server](https://github.com/rust-lang/rust-analyzer/tree/master/lib/lsp-server) | rust-analyzer 使用的轻量框架 |
| Go | [go-lsp](https://github.com/TobiasYin/go-lsp/) | 纯 Go LSP 实现 |
| C# | [C#-LSP](https://github.com/OmniSharp/csharp-language-server-protocol) | OmniSharp 出品 |
| C++ | [LspCpp](https://github.com/kuafuwang/LspCpp) | C++ LSP 库 |
| Swift | [LanguageServerProtocol](https://github.com/chimehq/LanguageServerProtocol) | ChimeHQ 出品 |
| Haskell | [haskell-lsp](https://github.com/alanz/haskell-lsp) | Haskell LSP 类型库 |
| Ruby | [LanguageServer::Protocol](https://github.com/mtsmfm/language_server-protocol-ruby) | Ruby LSP 协议库 |

> 更完整的 SDK 列表和选型决策树见 [05-ecosystem-landscape.md](./05-ecosystem-landscape.md#二lsp-sdk--框架按语言分类)

下面以 **Python + pygls** 为例，展示如何一步步搭建。

---

## 第一步：项目结构

```
my-lsp-server/
├── server.py          # LSP 服务端入口
├── completions.py     # 补全逻辑
├── diagnostics.py     # 诊断逻辑
├── utils.py           # 工具函数
└── requirements.txt
```

---

## 第二步：基础服务器骨架

```python
# server.py
import sys
from lsprotocol.types import (
    INITIALIZE, INITIALIZED,
    InitializeParams,
    TEXT_DOCUMENT_COMPLETION,
    CompletionOptions, CompletionParams, CompletionList,
    CompletionItem, CompletionItemKind,
    Position, Range, TextEdit,
    ServerCapabilities, TextDocumentSyncKind,
)
from pygls.server import LanguageServer


# 创建一个 Language Server 实例
server = LanguageServer("my-lsp", "v0.1.0")


@server.feature(INITIALIZE)
def initialize(ls: LanguageServer, params: InitializeParams):
    """初始化：声明服务器能力"""
    return ServerCapabilities(
        text_document_sync=TextDocumentSyncKind.FULL,
        completion_provider=CompletionOptions(
            trigger_characters=[".", " "]
        ),
        hover_provider=True,
        definition_provider=True,
    )


@server.feature(INITIALIZED)
def initialized(ls: LanguageServer, params):
    """收到 initialized 通知，可以开始工作"""
    ls.show_message("My LSP server initialized! 🚀")


@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: LanguageServer, params: CompletionParams):
    """提供自动补全"""
    uri = params.text_document.uri
    line = params.position.line
    char = params.position.character

    # 获取文档
    doc = ls.workspace.get_text_document(uri)
    current_line = doc.lines[line] if line < len(doc.lines) else ""
    text_before_cursor = current_line[:char]

    items = get_completions(text_before_cursor, doc.source)
    return CompletionList(is_incomplete=False, items=items)


def get_completions(text_before: str, full_text: str) -> list[CompletionItem]:
    """简单的补全逻辑"""
    results = []

    # 关键字补全
    keywords = ["def", "class", "import", "return", "if", "for", "while", "try", "except"]
    for kw in keywords:
        if kw.startswith(text_before.split()[-1] if text_before.split() else ""):
            results.append(CompletionItem(
                label=kw,
                kind=CompletionItemKind.Keyword,
                sort_text=f"0_{kw}",
            ))

    return results


if __name__ == "__main__":
    server.start_io()  # 通过 stdio 通信
```

---

## 第三步：添加诊断功能

```python
# diagnostics.py
from lsprotocol.types import (
    Diagnostic, DiagnosticSeverity,
    Position, Range,
    TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_CHANGE,
)
from pygls.server import LanguageServer


def validate_document(ls: LanguageServer, uri: str):
    """检查文档并推送诊断"""
    doc = ls.workspace.get_text_document(uri)
    source = doc.source
    diagnostics = []

    for i, line in enumerate(source.splitlines()):
        # 检查行长度
        if len(line) > 80:
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=i, character=80),
                    end=Position(line=i, character=len(line)),
                ),
                message=f"Line too long ({len(line)} > 80 characters)",
                severity=DiagnosticSeverity.Warning,
                source="my-lsp",
            ))

        # 检查 trailing whitespace
        if line.endswith(" ") or line.endswith("\t"):
            diagnostics.append(Diagnostic(
                range=Range(
                    start=Position(line=i, character=len(line.rstrip())),
                    end=Position(line=i, character=len(line)),
                ),
                message="Trailing whitespace",
                severity=DiagnosticSeverity.Information,
                source="my-lsp",
            ))

    ls.publish_diagnostics(uri, diagnostics)
```

然后在 `server.py` 中注册：

```python
@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params):
    """文件打开或修改时触发诊断"""
    validate_document(ls, params.text_document.uri)
```

---

## 第四步：添加跳转定义

```python
from lsprotocol.types import (
    TEXT_DOCUMENT_DEFINITION,
    DefinitionParams, Location, Position, Range,
)

@server.feature(TEXT_DOCUMENT_DEFINITION)
def goto_definition(ls: LanguageServer, params: DefinitionParams):
    """查找定义位置"""
    # 简化示例：搜索文档中某符号第一次出现的位置
    uri = params.text_document.uri
    doc = ls.workspace.get_text_document(uri)

    # 获取光标处的单词
    position = params.position
    line = doc.lines[position.line]
    word = get_word_at_position(line, position.character)

    if not word:
        return None

    # 在文档中搜索定义模式（如 "def {word}"）
    for i, doc_line in enumerate(doc.lines):
        if line.startswith(f"def {word}(") or line.startswith(f"class {word}"):
            char = len(f"def ") if line.startswith("def") else len("class ")
            return Location(
                uri=uri,
                range=Range(
                    start=Position(line=i, character=char),
                    end=Position(line=i, character=char + len(word)),
                ),
            )
    return None


def get_word_at_position(line: str, char: int) -> str:
    """提取光标处的标识符"""
    import re
    for match in re.finditer(r'\w+', line):
        if match.start() <= char <= match.end():
            return match.group()
    return ""
```

---

## 第五步：安装依赖

```
# requirements.txt
pygls>=1.0.0
lsprotocol>=2023.0.0
```

```bash
pip install -r requirements.txt
```

---

## 第六步：配置编辑器

### VSCode 配置 (扩展的 package.json)

```json
{
  "contributes": {
    "languages": [
      {
        "id": "mylang",
        "extensions": [".my"],
        "aliases": ["MyLang"]
      }
    ]
  },
  "activationEvents": ["onLanguage:mylang"],
  "main": "./extension.js"
}
```

```javascript
// extension.js (VSCode 客户端)
const vscode = require('vscode');
const { LanguageClient } = require('vscode-languageclient/node');

function activate(context) {
    const serverModule = context.asAbsolutePath('server.py');

    const serverOptions = {
        command: 'python',
        args: [serverModule],
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'mylang' }],
    };

    const client = new LanguageClient(
        'myLsp', 'My LSP Server',
        serverOptions, clientOptions
    );

    context.subscriptions.push(client.start());
}
```

### Neovim 配置 (lspconfig)

```lua
-- ~/.config/nvim/init.lua
local lspconfig = require('lspconfig')

lspconfig.my_lsp.setup({
    cmd = { 'python', '/path/to/my-lsp-server/server.py' },
    filetypes = { 'mylang' },
    root_dir = function(fname)
        return vim.fn.getcwd()
    end,
})
```

### 手动测试

```bash
# 启动服务器后，可以通过 stdio 发送 JSON-RPC 消息进行测试
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"capabilities":{}}}' | python server.py
```

---

## 关键实现细节

### 1. 文档管理

服务器维护所有打开文档的内存副本。对于 `Full` 同步模式：

```python
# 服务器内部
_documents: dict[str, str] = {}   # uri -> full text

def did_open(uri: str, text: str):
    _documents[uri] = text

def did_change(uri: str, new_text: str):
    _documents[uri] = new_text
```

对于 `Incremental` 模式，需要根据 `range` 和 `text` 来 patch：

```python
def apply_change(uri: str, range: Range, text: str):
    lines = _documents[uri].splitlines()
    start_line, start_char = range.start.line, range.start.character
    end_line, end_char = range.end.line, range.end.character

    # 拼接：range 之前 + 新文本 + range 之后
    new_lines = (
        lines[:start_line] +
        [lines[start_line][:start_char] + text + lines[end_line][end_char:]] +
        lines[end_line + 1:]
    )
    _documents[uri] = "\n".join(new_lines)
```

### 2. 错误处理

LSP 的错误码定义在 `ErrorCodes` 中：

```python
from lsprotocol.types import ResponseError, ErrorCodes

try:
    result = do_something()
except Exception as e:
    raise ResponseError(
        code=ErrorCodes.InternalError,
        message=str(e),
    ) from e
```

### 3. 取消请求

客户端可以发送 `$/cancelRequest` 通知来取消长时间运行的请求。服务器应在执行昂贵操作前检查 `check_canceled` 或 `token.is_cancellation_requested`。

---

## 从零开始的检查清单

1. [ ] 选择语言和 LSP 库
2. [ ] 实现 `initialize` → 声明能力
3. [ ] 实现 `initialized` → 注册文件监听
4. [ ] 实现 `textDocument/didOpen` `didChange` → 维护文档状态
5. [ ] 实现至少一个语言功能（补全 / 诊断 / 跳转）
6. [ ] 在编辑器中注册为 Language Client
7. [ ] 编写测试用例
8. [ ] 处理错误和边缘情况

## 相关文档

- [[02-core-features]] — 本系列第二节：要实现的协议功能
- [[Python高级核心]] — pygls 服务器实现所需的 Python 基础
- [[05-ecosystem-landscape]] — SDK 选型与生态对比
- [[CS-KB-Home]] — cs-base 子库首页
