---
title: LSP (Language Server Protocol) 学习指南
aliases: [LSP 学习指南, lsp-learn, LSP 教程索引]
tags: [cs/toolchain, cs]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# LSP (Language Server Protocol) 学习指南

## 目录

1. **[LSP 概述](./01-lsp-overview.md)** — LSP 是什么、为什么需要它、架构、通信方式、核心概念
2. **[核心功能详解](./02-core-features.md)** — 文档同步、诊断、补全、跳转定义、引用、Code Actions 等
3. **[实现一个 LSP 服务器](./03-implement-server.md)** — 用 Python + pygls 从零搭建，含 VSCode/Neovim 客户端配置
4. **[进阶主题](./04-advanced-topics.md)** — Incremental 同步、进度通知、多工作区、测试策略、性能优化
5. **[LSP 生态全景图](./05-ecosystem-landscape.md)** — Top 30 项目排名、SDK 选型、编辑器客户端对比、发展趋势

## 快速开始

```bash
# 安装依赖（以 Python 为例）
pip install pygls lsprotocol

# 启动你的第一个 LSP 服务器
python server.py
```

## 核心概念速览

```
编辑器 ←── JSON-RPC (stdio/TCP) ──→ 语言服务器
(Client)                              (Server)
  │                                      │
  │ 发送请求/通知                         │ 处理请求
  │ textDocument/completion              │ 返回结果
  │ textDocument/hover                   │ 推送诊断
  │ textDocument/definition              │ ...
```

## 推荐资源

### 官方资源
- [LSP 官方规范 (3.18)](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/)
- [LSP GitHub 仓库](https://github.com/microsoft/language-server-protocol) (12,877 ⭐)
- [官方服务器实现列表](https://microsoft.github.io/language-server-protocol/implementors/servers/)
- [官方 SDK 列表](https://microsoft.github.io/language-server-protocol/implementors/sdks/)

### 学习参考
- [pygls 文档](https://pygls.readthedocs.io/) — Python LSP 框架
- [vscode-languageserver-node](https://github.com/microsoft/vscode-languageserver-node) — TypeScript LSP SDK
- [langium](https://github.com/langium/langium) — 从语法生成 LSP 的语言工程框架
- [tower-lsp](https://github.com/ebkalderon/tower-lsp) — Rust 异步 LSP 框架
- [lsp-sample (VSCode 官方示例)](https://github.com/microsoft/vscode-extension-samples/tree/main/lsp-sample)

### 顶级开源 LSP 参考实现
- [rust-analyzer](https://github.com/rust-analyzer/rust-analyzer) — LSP 实现的黄金标准
- [gopls](https://github.com/golang/tools/tree/master/gopls) — Go 官方 LSP
- [ty](https://github.com/astral-sh/ty) (18,908 ⭐) — Rust 写的极速 Python LSP
- [clangd](https://github.com/llvm/llvm-project/tree/main/clang-tools-extra/clangd) — C/C++ LSP
- [Eclipse JDT LS](https://github.com/eclipse-jdtls/eclipse.jdt.ls) — Java LSP
- [lua-language-server](https://github.com/LuaLS/lua-language-server) — Lua LSP

### Demo 运行
```bash
cd demo
pip install -r requirements.txt
python -m pytest server/test_server.py -v   # 运行测试
python server/server.py                     # 启动服务器 (stdio)
```

## 相关文档

- [[CS-KB-Home]] — cs-base 子库首页
- [[LLVM编译器基础设施]] — clangd 所在的 LLVM 工具链背景
- [[Python高级核心]] — 用 Python + pygls 实现语言服务器的语言基础
- [[01-lsp-overview]] — 本系列第一节：LSP 概述
