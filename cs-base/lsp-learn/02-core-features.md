# LSP 核心功能详解

## 1. 文档同步 (Document Synchronization)

服务器通过文档同步来获取文件内容。有三种同步模式：

### 同步模式

| 模式 | 值 | 说明 |
|------|---|------|
| None | `TextDocumentSyncKind.None` | 不接受文档同步，只处理已打开文件 |
| Full | `TextDocumentSyncKind.Full` | 每次变更发送完整文本 (最简单，大文件有性能影响) |
| Incremental | `TextDocumentSyncKind.Incremental` | 只发送变更部分 (性能好，实现复杂) |

### 关键通知

```
textDocument/didOpen    — 文件被打开
textDocument/didChange  — 文件内容变化
textDocument/didClose   — 文件被关闭
textDocument/didSave    — 文件被保存
```

### Incremental 同步示例

```json
{
  "method": "textDocument/didChange",
  "params": {
    "textDocument": { "uri": "file:///main.go", "version": 3 },
    "contentChanges": [
      {
        "range": {
          "start": { "line": 10, "character": 0 },
          "end":   { "line": 10, "character": 5 }
        },
        "text": "newText"
      }
    ]
  }
}
```

服务器需要根据 `range` 和 `text` 来更新内部文档模型。

---

## 2. 诊断 (Diagnostics)

诊断是服务器向客户端**主动推送**的消息，用于显示错误、警告等。

```json
{
  "method": "textDocument/publishDiagnostics",
  "params": {
    "uri": "file:///main.go",
    "diagnostics": [
      {
        "range": {
          "start": { "line": 10, "character": 0 },
          "end":   { "line": 10, "character": 8 }
        },
        "severity": 1,
        "message": "undefined variable 'fooBar'",
        "source": "myls"
      }
    ]
  }
}
```

### 严重程度

| 值 | 含义 |
|---|------|
| 1 | Error |
| 2 | Warning |
| 3 | Information |
| 4 | Hint |

### 诊断相关标签 (DiagnosticTag)

- `1` — Unnecessary (不必要的代码，如未使用的 import)
- `2` — Deprecated (已弃用的 API)

---

## 3. 补全 (Completion)

最常用的功能。用户输入时触发。

### 请求

```json
{
  "method": "textDocument/completion",
  "params": {
    "textDocument": { "uri": "file:///main.go" },
    "position": { "line": 5, "character": 3 },
    "context": {
      "triggerKind": 1,          // 1=手动 2=触发字符 3=重新触发
      "triggerCharacter": "."
    }
  }
}
```

### 响应

```json
{
  "result": {
    "isIncomplete": false,
    "items": [
      {
        "label": "fmt.Println",
        "kind": 3,                    // CompletionItemKind: Function
        "detail": "func(...interface{}) (int, error)",
        "documentation": "Println formats using the default formats...",
        "sortText": "00001",
        "filterText": "Println",
        "textEdit": {
          "range": { ... },
          "newText": "fmt.Println(${1:args})"
        },
        "insertTextFormat": 2         // 2=Snippet 格式
      }
    ]
  }
}
```

### CompletionItemKind

| 值 | 含义 | 值 | 含义 |
|---|------|---|------|
| 1 | Text | 9 | Constructor |
| 2 | Method | 10 | Property |
| 3 | Function | 11 | Unit |
| 4 | Constructor | 12 | Value |
| 5 | Field | 13 | Enum |
| 6 | Variable | 14 | Keyword |
| 7 | Class | 15 | Snippet |
| 8 | Interface | 16 | Color |

---

## 4. 悬停提示 (Hover)

鼠标悬停在符号上时显示信息。

```json
// 请求
{ "method": "textDocument/hover", "params": { "textDocument": {...}, "position": {...} } }

// 响应
{
  "result": {
    "contents": {
      "kind": "markdown",
      "value": "```go\nfunc fmt.Println(a ...interface{}) (n int, err error)\n```\n\nPrintln formats using the default formats for its operands and writes to standard output."
    },
    "range": { "start": {...}, "end": {...} }
  }
}
```

---

## 5. 跳转定义 (Go to Definition)

```json
// 请求
{ "method": "textDocument/definition", "params": { "textDocument": {...}, "position": {...} } }

// 响应 — 可以是单个位置或多个位置（如接口的多个实现）
{
  "result": {
    "uri": "file:///path/to/definition.go",
    "range": {
      "start": { "line": 42, "character": 5 },
      "end":   { "line": 42, "character": 9 }
    }
  }
}
```

---

## 6. 查找引用 (Find References)

```json
// 请求
{
  "method": "textDocument/references",
  "params": {
    "textDocument": {...},
    "position": {...},
    "context": { "includeDeclaration": true }
  }
}

// 响应
{
  "result": [
    { "uri": "file:///main.go", "range": { "start": {"line": 5, "character": 2}, "end": {"line": 5, "character": 6} } },
    { "uri": "file:///util.go", "range": { "start": {"line": 20, "character": 0}, "end": {"line": 20, "character": 4} } }
  ]
}
```

---

## 7. 代码操作 (Code Actions)

快速修复、重构等：

```json
// 请求
{ "method": "textDocument/codeAction", "params": {
    "textDocument": {...},
    "range": {...},              // 选中的范围
    "context": {
      "diagnostics": [...],      // 触发 code action 的诊断
      "only": ["quickfix"]       // 只请求特定类型的 actions
    }
}}

// 响应
{
  "result": [
    {
      "title": "Add missing import 'fmt'",
      "kind": "quickfix",
      "diagnostics": [...],
      "edit": {
        "changes": {
          "file:///main.go": [
            { "range": {...}, "newText": "\"fmt\"\n" }
          ]
        }
      }
    }
  ]
}
```

---

## 8. 符号 (Document Symbols / Workspace Symbols)

- `textDocument/documentSymbol` — 当前文件的符号列表（大纲）
- `workspace/symbol` — 整个工作区的符号搜索

```json
// 请求
{ "method": "workspace/symbol", "params": { "query": "HttpServer" } }

// 响应
{
  "result": [
    {
      "name": "HttpServer",
      "kind": 5,                          // Class
      "location": {
        "uri": "file:///server.go",
        "range": { ... }
      },
      "containerName": "package main"
    }
  ]
}
```

---

## 9. 其他常用功能

| 方法 | 说明 |
|------|------|
| `textDocument/formatting` | 格式化整个文档 |
| `textDocument/rangeFormatting` | 格式化选中范围 |
| `textDocument/rename` | 重命名符号 |
| `textDocument/signatureHelp` | 函数签名帮助（参数提示） |
| `textDocument/documentHighlight` | 高亮文档中相同的符号 |
| `textDocument/documentLink` | 检测文档中的链接 |
| `textDocument/foldingRange` | 代码折叠范围 |
| `textDocument/semanticTokens` | 语义高亮（比正则高亮更精确） |
| `textDocument/inlayHint` | 内联提示（参数名、类型等） |
| `textDocument/typeDefinition` | 跳转到类型定义 |
| `textDocument/implementation` | 跳转到接口实现 |

---

## 请求执行顺序

LSP 不保证请求按发送顺序执行。但 `textDocument/didChange` 等文档同步通知**必须按序处理**，因为服务器需要维护正确的文档状态。
