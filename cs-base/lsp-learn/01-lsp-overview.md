---
title: LSP (Language Server Protocol) 概述
aliases: [LSP 概述, 语言服务器协议, LSP 架构]
tags: [cs/toolchain, cs]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# LSP (Language Server Protocol) 概述

## 什么是 LSP？

LSP 是 Microsoft 在 2016 年提出的一套开放协议，用于在编辑器/IDE 和语言服务器之间进行通信。它的核心思想是：**用一种标准化的方式，让编辑器能够获得任意编程语言的智能功能**。

## 为什么需要 LSP？

### 传统方式的问题

在 LSP 出现之前，每种编辑器都要为每种语言单独实现智能功能：

```
编辑器(Emacs) ──实现──> Python 补全、跳转、诊断
编辑器(Vim)   ──实现──> Python 补全、跳转、诊断
编辑器(VSCode)──实现──> Python 补全、跳转、诊断
...
```

这意味着 M 种编辑器 × N 种语言 = M×N 种实现。

### LSP 的解决方案

LSP 将"语言智能"抽离为独立的**语言服务器**：

```
编辑器(Vim)    ─┐
编辑器(VSCode) ─┼─ LSP 协议 ──> Python Language Server (pylsp/pyright)
编辑器(Emacs)  ─┘
```

现在只需要 M + N 种实现：M 个编辑器各写一个 LSP 客户端插件，N 种语言各写一个 LSP 服务器。

## LSP 的核心架构

```
┌──────────────┐         JSON-RPC          ┌──────────────────┐
│              │ ◄───────────────────────> │                  │
│   Editor     │   (stdio / TCP / pipe)    │  Language Server │
│  (Client)    │                            │    (Server)      │
│              │                            │                  │
└──────────────┘                            └──────────────────┘
     │                                              │
     │ 用户打开文件                                   │ 解析 AST
     │ 用户输入代码                                   │ 类型检查
     │ 用户悬停符号                                   │ 代码分析
     │ 用户请求补全                                   │ ... 
     ▼                                              ▼
```

## 通信方式

LSP 使用 **JSON-RPC 2.0** 作为消息格式，支持多种传输方式：

| 传输方式 | 说明 |
|---------|------|
| stdio | 标准输入输出，最常用 |
| TCP Socket | 网络通信，支持远程服务器 |
| Named Pipe | 命名管道 (Windows) |
| Socket | Unix domain socket |

### JSON-RPC 消息示例

**请求 (Request):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "textDocument/completion",
  "params": {
    "textDocument": { "uri": "file:///home/user/main.go" },
    "position": { "line": 10, "character": 5 }
  }
}
```

**响应 (Response):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": [
    { "label": "fmt.Println", "kind": 3, "detail": "func(...interface{})" }
  ]
}
```

**通知 (Notification — 无需响应):**
```json
{
  "jsonrpc": "2.0",
  "method": "textDocument/didOpen",
  "params": {
    "textDocument": {
      "uri": "file:///home/user/main.go",
      "languageId": "go",
      "version": 1,
      "text": "package main\n..."
    }
  }
}
```

## 核心概念

### 1. Document URI

LSP 使用 URI 来标识文件（不是文件路径）。URI 的格式为 `file:///绝对路径`：
- Windows: `file:///c%3A/Users/test/main.go`
- Linux/macOS: `file:///home/user/main.go`

### 2. Position

位置用零基的 `(line, character)` 表示。`character` 按 **UTF-16 code units** 计算（历史原因，因为 VSCode 使用 JavaScript）。

### 3. 生命周期

```
        initialize (capability exchange)
              │
              ▼
         initialized
              │
              ▼
    ┌─────────────────────┐
    │  正常工作阶段         │
    │  - didOpen/didChange │
    │  - completion/hover  │
    │  - definition/refs   │
    └─────────┬───────────┘
              │
              ▼
           shutdown
              │
              ▼
            exit
```

## 三大类消息

| 类别 | 方向 | 说明 | 示例 |
|------|------|------|------|
| 文档同步 | Client → Server | 告知服务器文档状态变化 | `textDocument/didOpen` `didChange` `didClose` |
| 语言功能 | Client → Server | 请求语言智能功能 | `textDocument/completion` `hover` `definition` |
| 诊断推送 | Server → Client | 服务器推送错误/警告 | `textDocument/publishDiagnostics` |

## 现实世界中的 LSP

LSP 已经成为现代开发工具的基石。以下是一些代表性实现：

| 语言 | LSP 服务器 | GitHub Stars | 维护者 |
|------|-----------|-------------|--------|
| Rust | [rust-analyzer](https://github.com/rust-analyzer/rust-analyzer) | — | rust-analyzer team |
| Go | [gopls](https://github.com/golang/tools/tree/master/gopls) | — | Go Team |
| Python | [ty](https://github.com/astral-sh/ty) | 18,908 | Astral (ruff 团队) |
| Python | [Pyright](https://github.com/microsoft/pyright) | — | Microsoft |
| C/C++ | [clangd](https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd) | — | LLVM Project |
| Java | [Eclipse JDT LS](https://github.com/eclipse-jdtls/eclipse.jdt.ls) | 2,400 | Eclipse |
| TypeScript | [typescript-language-server](https://github.com/typescript-language-server/typescript-language-server) | 2,500 | Community |
| Lua | [lua-language-server](https://github.com/LuaLS/lua-language-server) | 4,282 | LuaLS |
| Swift | [sourcekit-lsp](https://github.com/swiftlang/sourcekit-lsp) | 3,859 | Apple |
| Zig | [zls](https://github.com/zigtools/zls) | 4,918 | zigtools |

> 注：完整的 150+ 服务器列表请参阅 [05-ecosystem-landscape.md](./05-ecosystem-landscape.md)，包含 SDK 选型、编辑器客户端对比等。

## 相关文档

- [[02-core-features]] — 本系列第二节：核心功能详解
- [[CS-KB-Home]] — cs-base 子库首页
- [[LLVM编译器基础设施]] — clangd 与编译前端工具链背景
- [[Python高级核心]] — 实现语言服务器所需的 Python 基础
