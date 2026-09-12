# 01 — MCP 核心概念与架构

## 什么是 MCP

Model Context Protocol (MCP) 是一个**开放标准协议**，用于连接 AI 模型和外部世界。它在 2024 年 11 月由 Anthropic 发布，目前已成为 AI 工具集成的事实标准。

### 类比理解

MCP 之于 AI 工具集成，就像 USB-C 之于设备充电——提供统一的连接标准，取代过去每个 AI 应用/工具各搞一套的碎片化局面。

### 支持情况

- **Anthropic** Claude (原生支持)
- **OpenAI** Agents SDK (2025 年 3 月起原生支持)
- **Google** Gemini (2025 年底集成)
- **IDE/编辑器**: Cursor, Zed, VS Code Copilot, Cline, Continue.dev

## 三层架构

```
┌─────────────────────────────────┐
│           Host (主机)            │  ← AI 应用: Claude Desktop, IDE, 自定义应用
│  ┌───────────────────────────┐  │
│  │     Client (客户端)        │  │  ← 协议处理器, 管理 MCP 服务器连接
│  │  ┌──────┐ ┌──────┐       │  │
│  │  │ MCP  │ │ MCP  │ ...   │  │
│  │  │Server│ │Server│       │  │  ← 服务器: 暴露 Tools/Resources/Prompts
│  │  └──────┘ └──────┘       │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

- **Host**: 运行 AI 模型的应用（Claude Desktop、Cursor、自定义 chatbot）
- **Client**: 在 Host 内部运行，管理与多个 MCP Server 的 1:N 连接
- **Server**: 提供具体能力的服务，暴露 Tools、Resources、Prompts

## 通信协议

基于 **JSON-RPC 2.0**，支持三种消息类型：

| 类型 | 方向 | 说明 |
|------|------|------|
| Request | 双向 | 带 `id` 的请求，期望得到 Response |
| Response | 双向 | 对 Request 的成功/失败响应 |
| Notification | 双向 | 不带 `id` 的消息，无需响应 |

### 能力协商 (Capability Negotiation)

连接建立时，客户端和服务器通过 `initialize` 握手交换各自支持的能力：
- 客户端声明: `roots`, `sampling`
- 服务器声明: `tools`, `resources`, `prompts`, `logging`

## 三大核心原语 (Primitives)

| 原语 | 控制方 | 用途 | 类比 |
|------|--------|------|------|
| **Tools** | 模型控制 | API 调用、计算、数据库操作 | POST 端点 |
| **Resources** | 应用控制 | 暴露只读数据 (文件、数据库记录) | GET 端点 |
| **Prompts** | 用户触发 | 可复用的交互模板 | 预设工作流 |

## 协议版本演进

| 版本 | 日期 | 关键变化 |
|------|------|----------|
| 2025-03-26 | 2025.03 | SSE 废弃，Streamable HTTP 引入 |
| 2025-11-25 | 2025.11 | **当前稳定版**。Tool calling in sampling, Tasks (实验), JSON Schema 2020-12, OAuth CIMD |
| 2026-07-28 | 2026.07 | **下一版本 (RC)**。无状态协议, 移除 initialize 握手, MCP Apps, Tasks 正式化 |

## 核心设计原则

1. **模型无关**: 不绑定任何特定 AI 模型
2. **传输无关**: 支持 stdio / HTTP / SSE 多种传输
3. **安全优先**: 用户始终控制数据访问权限
4. **可发现**: 客户端可以动态发现服务器的能力
5. **可组合**: 一个 Host 可以连接多个 MCP Server
