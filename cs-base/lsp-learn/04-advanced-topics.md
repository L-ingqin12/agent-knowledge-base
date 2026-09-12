---
title: LSP 进阶主题
aliases: [LSP 进阶, LSP 性能优化, LSP 测试策略]
tags: [cs/toolchain, cs]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# LSP 进阶主题

> 这些进阶特性在实际项目中的实现可参考：
> - [rust-analyzer](https://github.com/rust-analyzer/rust-analyzer) — Incremental 同步、进度通知、多工作区，LSP 实现黄金标准
> - [gopls](https://github.com/golang/tools/tree/master/gopls) — 生产级测试策略和取消机制
> - [ty](https://github.com/astral-sh/ty) — 极致性能优化 (Rust)
> - 完整生态数据和特性对比见 [05-ecosystem-landscape.md](./05-ecosystem-landscape.md)

## 1. Incremental 文档同步详解

Incremental 同步比 Full 同步复杂得多，但可以显著提升大文件的编辑性能。

### 变更范围的计算

```python
def apply_incremental_change(doc: str, changes: list) -> str:
    """按序应用多个增量变更"""
    for change in changes:
        range_ = change["range"]
        text = change["text"]

        lines = doc.splitlines()
        start_line = range_["start"]["line"]
        start_char = range_["start"]["character"]
        end_line = range_["end"]["line"]
        end_char = range_["end"]["character"]

        # 字符串拼接方式
        before = "\n".join(lines[:start_line])
        current_start = lines[start_line][:start_char] if start_line < len(lines) else ""
        current_end = lines[end_line][end_char:] if end_line < len(lines) else ""
        after = "\n".join(lines[end_line + 1:])

        doc = before + "\n" + current_start + text + current_end + "\n" + after

    return doc
```

### 陷阱

- **rangeLength 废弃**：LSP 3.0 使用 `rangeLength`，3.17 用 `range` 替代
- **多行变更**：`text` 可包含换行符，整个 `range` 替换为 `text`
- **utf-8 vs utf-16**：Position.character 按 UTF-16 code unit 计算

---

## 2. Position 编码问题

### UTF-16 与 UTF-8

```python
def utf8_offset_to_utf16(text: str, offset: int) -> int:
    """将 UTF-8 字节偏移转换为 UTF-16 code unit 偏移"""
    utf16_offset = 0
    for i, char in enumerate(text[:offset]):
        codepoint = ord(char)
        if 0x10000 <= codepoint <= 0x10FFFF:
            utf16_offset += 2  # surrogate pair
        else:
            utf16_offset += 1
    return utf16_offset
```

### Position Encoding Negotiation (LSP 3.17+)

```json
// initialize 时可以协商编码方式
{
  "capabilities": {
    "general": {
      "positionEncodings": ["utf-8", "utf-16"]
    }
  }
}
```

服务器可选择 `utf-8`、`utf-16`、`utf-32`，不指定则默认 `utf-16`。

---

## 3. 进度通知

长时间运行的请求可以报告进度：

```json
// 服务端发送 $/progress 通知
{
  "method": "$/progress",
  "params": {
    "token": "progress-token-abc",
    "value": {
      "kind": "begin",
      "title": "Indexing project...",
      "percentage": 0
    }
  }
}
```

```json
// 更新进度
{
  "method": "$/progress",
  "params": {
    "token": "progress-token-abc",
    "value": {
      "kind": "report",
      "percentage": 50,
      "message": "50/100 files indexed"
    }
  }
}
```

```json
// 完成
{
  "method": "$/progress",
  "params": {
    "token": "progress-token-abc",
    "value": { "kind": "end" }
  }
}
```

---

## 4. Work Done Progress

对于特定请求的进度报告（如 `textDocument/formatting` 处理大文件）：

```python
# 服务端在 initialize 时声明
ServerCapabilities(
    completion_provider=CompletionOptions(
        work_done_progress=True,  # 表示这个 provider 支持进度
    )
)
```

客户端请求时带 `workDoneToken`：

```json
{
  "method": "textDocument/completion",
  "params": {
    "workDoneToken": "token-1",
    ...
  }
}
```

服务端在处理过程中发送 `$/progress`：

```json
{ "method": "$/progress", "params": { "token": "token-1", "value": { "kind": "begin", "title": "Computing completions..." } } }
```

---

## 5. 多工作区支持

服务器可以同时服务多个工作区文件夹：

```json
// workspace/didChangeWorkspaceFolders
{
  "method": "workspace/didChangeWorkspaceFolders",
  "params": {
    "event": {
      "added": [{ "uri": "file:///new-project", "name": "new-project" }],
      "removed": [{ "uri": "file:///old-project", "name": "old-project" }]
    }
  }
}
```

### 工作区配置

```json
// 服务端请求配置
{ "method": "workspace/configuration", "params": { "items": [
    { "section": "myLsp.maxLineLength" },
    { "section": "myLsp.pythonPath" }
]}}

// 客户端返回
[{ "maxLineLength": 120 }, { "pythonPath": "/usr/bin/python3" }]
```

---

## 6. 部分结果 (Partial Results)

大结果集可以分批返回，提高用户体验：

```json
// 服务端声明支持 partial results
{
  "capabilities": {
    "workspaceSymbolProvider": {
      "resolveProvider": true
    }
  }
}

// 客户端请求时带 partialResultToken
{ "method": "workspace/symbol", "params": { "query": "foo", "partialResultToken": "token-1" } }

// 服务端分批发送结果
{ "method": "$/partialResult", "params": { "token": "token-1", "value": [...] } }
```

---

## 7. LSP 3.17 重要新增功能

| 功能 | 说明 |
|------|------|
| Inlay Hint | 内联提示（参数名、类型注解） |
| Inline Value | 内联值（调试时的变量值） |
| Type Hierarchy | 类型层级（子类型/超类型） |
| Diagnostic Pull Model | 客户端按需拉取诊断 |
| Notebook Support | 支持 Jupyter Notebook |
| Linked Editing Ranges | 同步编辑范围（如 HTML 标签配对） |
| Position Encodings | 支持 UTF-8/UTF-32 位置编码 |

---

## 8. 测试 LSP 服务器

### 单元测试

```python
import pytest
from pygls.server import LanguageServer
from pygls.workspace import Document, Workspace

def test_completion_returns_keywords():
    server = LanguageServer("test", "v1")
    doc = Document("file:///test.py", "de\n")

    items = get_completions("de", doc.source)

    labels = [i.label for i in items]
    assert "def" in labels


def test_diagnostic_too_long_line():
    diags = validate_line("x" * 81, line_number=0)
    assert len(diags) == 1
    assert diags[0].severity == DiagnosticSeverity.Warning
```

### 集成测试

```python
import subprocess
import json


def send_request(request: dict) -> dict:
    """通过子进程与 LSP 服务通信"""
    proc = subprocess.Popen(
        ["python", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    content = json.dumps(request)
    header = f"Content-Length: {len(content)}\r\n\r\n"
    message = header + content

    stdout, _ = proc.communicate(input=message.encode())

    # 解析 LSP 响应
    header_end = stdout.index(b"\r\n\r\n") + 4
    body = stdout[header_end:]
    return json.loads(body)


def test_initialize():
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "capabilities": {},
        },
    }
    resp = send_request(req)
    assert resp["id"] == 1
    assert "capabilities" in resp["result"]
```

### LSP 协议级测试

注意 LSP 使用 `Content-Length` header 分隔消息：

```
Content-Length: 123\r\n
Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n
\r\n
{"jsonrpc":"2.0",...}
```

---

## 9. 性能优化建议

1. **延迟加载**：不要在 `initialize` 时加载所有项目数据，在首次请求时做
2. **增量分析**：只重新分析修改的文件，不是整个项目
3. **缓存 AST/索引**：避免重复解析同一文件
4. **取消机制**：支持 `$/cancelRequest`，避免浪费计算
5. **节流 (Debounce)**：`didChange` 事件可以节流处理（等用户停止输入后再分析）
6. **使用 Incremental 同步**：大文件场景下避免传输完整文本

```python
import time
from functools import wraps

def debounce(wait_ms: int):
    """简单的 debounce 装饰器"""
    def decorator(fn):
        last_call = 0

        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal last_call
            now = time.time() * 1000
            if now - last_call >= wait_ms:
                last_call = now
                return fn(*args, **kwargs)
        return wrapper
    return decorator


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
@debounce(300)  # 300ms 后再触发诊断
def on_change(ls, params):
    validate_document(ls, params.text_document.uri)
```

---

## 10. 排查 LSP 问题

### 常见调试方法

```bash
# 查看 LSP 通信日志（VSCode）
# 设置 "trace.server": "verbose" 查看完整的 JSON-RPC 通信

# Neovim 查看 LSP 日志
:LspLog
```

### 抓取 LSP 消息

```bash
# 使用 socat 在客户端和服务器之间做中间人
socat -v TCP-LISTEN:9999,fork,reuseaddr TCP:localhost:8888
```

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 补全不触发 | 未声明 completion provider | 检查 initialize 返回的 capabilities |
| 诊断不显示 | 同步模式为 None | 改为 Full 或 Incremental |
| Position 偏移错误 | UTF-8/UTF-16 混淆 | 检查 positionEncoding |
| 服务器启动失败 | 依赖缺失或路径错误 | 检查 cmd/args 配置 |

## 相关文档

- [[03-implement-server]] — 本系列第三节：从零实现服务器
- [[05-ecosystem-landscape]] — 生产级实现的生态参考
- [[Python高级核心]] — 并发与异步相关的语言基础
- [[LLVM编译器基础设施]] — clangd 等 C/C++ 服务器的编译器背景
