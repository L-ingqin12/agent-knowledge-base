---
title: MCP (Model Context Protocol) 学习指南
aliases: [MCP 学习指南, mcp-learn, MCP 教程索引]
tags: [ai, ai/learning]
created: 2026-09-12
updated: 2026-09-13
status: stable
---

# MCP (Model Context Protocol) 学习指南

MCP 是 Anthropic 推出的开放标准协议，为 AI 模型提供连接外部工具、数据和 API 的统一接口。类比：**MCP 之于 AI 工具集成，就像 USB-C 之于设备充电**——一个通用连接器。

## 目录结构

| 文件 | 内容 |
|------|------|
| [01-overview.md](01-overview.md) | MCP 核心概念、架构、协议基础 |
| [02-quickstart.md](02-quickstart.md) | 环境搭建、第一个 MCP 服务器 |
| [03-server-dev.md](03-server-dev.md) | 服务器开发详解 (Python SDK) |
| [04-client-dev.md](04-client-dev.md) | 客户端开发详解 |
| [05-tools-resources-prompts.md](05-tools-resources-prompts.md) | 三大核心原语: Tools/Resources/Prompts |
| [06-transports.md](06-transports.md) | 传输层: stdio/SSE/Streamable HTTP |
| [07-best-practices.md](07-best-practices.md) | 最佳实践与安全 |
| [08-mcp-vs-skill.md](08-mcp-vs-skill.md) | **架构决策**: MCP vs Skill 选型指南 |
| [09-cross-platform.md](09-cross-platform.md) | **跨平台兼容**: 一次编写, Claude/OpenCode/Cursor/Copilot 全平台运行 |
| [10-advanced-patterns.md](10-advanced-patterns.md) | **高级设计模式**: 工作流导向、语义路由、结构化错误、Token 预算管理 |
| [11-testing-debugging.md](11-testing-debugging.md) | **测试调试部署**: 技术/行为测试、stdio 代理、Docker/systemd 生产部署 |
| [12-real-world-examples.md](12-real-world-examples.md) | **真实案例研究**: Sentry/Linear/GitHub/PostgreSQL MCP 架构分析 |
| [13-ecosystem-projects.md](13-ecosystem-projects.md) | **GitHub 高分项目目录**: Awesome 列表、官方实现、SDK、网关、安全治理 |
| [cheatsheet.md](cheatsheet.md) | **速查手册**: 一页纸浓缩全部知识要点 |
| [references.md](references.md) | 官方文档、教程、社区资源链接 |
| [examples/](examples/) | 可运行的示例代码 + [详细使用部署指南](examples/README.md) |

## 示例服务器

| 文件 | 用途 | 依赖 |
|------|------|------|
| `examples/simple_server.py` | 入门: greet, add, version | `mcp` |
| `examples/multi_tool_server.py` | 进阶: 笔记 CRUD, 天气, 计算器 | `mcp`, `pydantic` |
| `examples/http_server.py` | HTTP 传输示例 | `mcp` |
| `examples/client_demo.py` | 客户端连接示例 | `mcp` |
| `examples/addr2line_server.py` | **实战**: crash 堆栈地址反解、符号查找、反汇编 | `mcp`, binutils |
| `examples/image_understanding_server.py` | **实战**: 图片分析、OCR 文字识别、EXIF、批量处理 | `mcp`, Pillow, pytesseract |
| `examples/excalidraw_server.py` | **实战**: Obsidian Excalidraw 读写解析、AI 自动生成图表、元素增删改绑定 | `mcp` |
| `examples/generate_config.py` | 一键生成 6 大平台 (Claude/OpenCode/Cursor/Copilot/Continue/Zed) 的配置模板 | Python 3.10+ |

## 快速开始

```bash
# 安装 Python SDK —— 注意：pip install mcp 现在装的是 v2.x
# 本库示例仍用 v1 的 FastMCP，请装上界：
pip install "mcp<2"

# 运行示例服务器
cd examples/
python simple_server.py
```

> [!warning] 更正（2026-09-13）：原文只写 `pip install mcp`。实测 PyPI `mcp` 最新版为 **2.2.0**（requires_python >=3.10，author 为「Model Context Protocol a Series of LF Projects, LLC.」），包描述自述「This is v2 of the MCP Python SDK, the current stable release line」，并要求「Since pip install mcp now installs 2.x, keep a `<2` upper bound on your requirement」。下载 `mcp-2.2.0-py3-none-any.whl` 实体核对：`mcp/server/fastmcp.py` 已缩成 **769 字节的桩**，导入即 `raise ModuleNotFoundError`（提示改用 `from mcp.server.mcpserver import MCPServer` 或 pin `mcp<2`）；`mcp/server/__init__.py` 只导出 `MCPServer` / `Server` / `CacheHint` 等。
> **本库 6 个 server 示例**（simple / http / multi_tool / addr2line / image_understanding / excalidraw）仍写 `from mcp.server.fastmcp import FastMCP`，照原文在新机器上执行会直接报错——上面已把安装命令改成 `pip install "mcp<2"` 作为临时解法，**示例文件本身仍待迁移到 v2**。
> v2 迁移要点（官方 whats-new / migration）：`FastMCP` → `MCPServer`；模块整体迁到 `mcp.server.mcpserver`；`MCPServer.get_context()` 移除（`call_tool` / `read_resource` / `get_prompt` 改带 context 参数）；传输配置移入 `run()`；`@mcp.tool()` / `@mcp.resource()` / `@mcp.prompt()` 三个装饰器兼容。
> 来源：<https://pypi.org/pypi/mcp/json> · <https://py.sdk.modelcontextprotocol.io/v2/whats-new/> · <https://py.sdk.modelcontextprotocol.io/v2/migration/>

### 验收判据（2026-09-13 补）

原文快速开始止于「启动服务器」，读者没有成功判据。官方 2026-07-28 教程把完整路径定为「写服务器 → 接入一个 host → 在 host 里看到并调用工具」，补齐如下：

| 步骤 | 做法 | 通过判据 |
|------|------|---------|
| 1. 版本自检 | `pip show mcp` | 示例迁移到 v2 之前应落在 1.x；装成 2.x 时 `simple_server.py` 会在导入处报 `ModuleNotFoundError` |
| 2. 接入 host | `python examples/generate_config.py` 生成 6 平台模板（claude-code / opencode / cursor / vscode-copilot / continue / zed），部署说明见 [examples/README.md](examples/README.md) | host 的 MCP 列表里出现示例服务器，工具数 = 源码里 `@mcp.tool()` 的数量 |
| 3. 调用工具 | 在 host 里调用 `greet` / `add` | 返回预期文本，且 host 无「server disconnected」 |

**host 看不到工具时的排查顺序**（stdio 是最常见的坑）：① host 是否重载了配置（多数 host 只在启动时读取 MCP 配置）；② 启动命令是否用了正确命令名 / 绝对路径；③ **stdio 传输下 stdout 只允许 JSON-RPC**——示例里任何 `print()` 调试都会污染协议流，这是最常见的失败样例，调试输出请走 stderr；④ 查 host 侧的 MCP 日志确认启动错误；⑤ 回到第 1 步确认 SDK 版本。
来源：<https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server>

## 核心要点

1. **协议基础**: JSON-RPC 2.0，客户端-服务器架构
2. **三种原语**: Tools (模型控制的操作)、Resources (应用控制的只读数据)、Prompts (可复用交互模板)
3. **传输方式**: stdio (本地)、Streamable HTTP (远程)、SSE (已废弃) —— 废弃的是 **HTTP+SSE 双端点传输**；SSE 作为流式机制仍在 Streamable HTTP 内部使用，见下节
4. **鉴权**: OAuth 2.0 + Client ID Metadata Documents (CIMD) —— 现行注册机制与切换时间见下节

## 鉴权与传输：2026-07-28 现行口径（2026-09-13 补）

### 传输

| 传输 | 状态 | 说明 |
|------|------|------|
| stdio | 现行 | 本地进程间通信 |
| Streamable HTTP | 现行 | 远程推荐；单端点，响应可用一条「作用域限定在该请求上的 SSE 流」承载请求相关通知 + 最终响应，长连接变更通知由 `subscriptions/listen` 的响应流交付 |
| HTTP+SSE（双端点） | **已废弃** | 2025-03-26 起 deprecated；2026-07-28 由 SEP-2596 依特性生命周期政策正式归档为 Deprecated，迁移目标 Streamable HTTP，移除时间为 SEP-2596 进入 Final 后三个月 |

本库 `examples/http_server.py` 已是 `mcp.run(transport='streamable-http')`，可直接作为迁移后写法参考。
来源：<https://modelcontextprotocol.io/specification/2026-07-28/deprecated> · <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http>

### 鉴权

原文只有一行的「OAuth 2.0 + Client ID Metadata Documents」，补足如下（官方 changelog / deprecated / SDK v2 更新说明实测）：

- **2026-07-28 起 OAuth 2.0 Dynamic Client Registration (RFC 7591) 被正式弃用**，**Client ID Metadata Documents 成为首选注册机制**；弃用表写明移除时间为「First revision released on or after 2027-07-28」。
- SDK v2 客户端：校验授权码返回的 `iss`（RFC 9207；`callback_handler` 返回 `AuthorizationCodeResult`）；注册时携带 `application_type`；凭证不得跨授权服务器复用。
- 企业侧新增 SEP-990 identity-assertion。
- 本库现状：13 篇文档里 OAuth 只零星出现（[[01-overview]] 的「OAuth CIMD」、06/12/13 与 references 各一两处），**没有能照做的片段**——需要落地时直接查官方规范页。

来源：<https://modelcontextprotocol.io/specification/2026-07-28/changelog> · <https://modelcontextprotocol.io/specification/2026-07-28/deprecated> · <https://py.sdk.modelcontextprotocol.io/v2/whats-new/>

## 相关文档

- [[MCP协议开发实战]] — 同主题的完整实战长文，可与本系列对照阅读
- [[LLM-Agent开发基础]] — 工具层之前的 Agent 基础
- [[Function-Calling工具调用实战]] — MCP 要解决的 Function Call 三大缺陷
- [[AI-Dev-KB-Home]] — ai-dev 子库首页
- [[01-overview]] — 本系列第一节：MCP 核心概念与架构

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 快速开始写 `pip install mcp`，未提 SDK v2 已是稳定线 | 改为 `pip install "mcp<2"` 并加更正块：PyPI latest 2.2.0、`mcp/server/fastmcp.py` 已成 769 字节桩、6 个示例仍用 v1 `FastMCP`；依据 PyPI JSON / wheel 实体与 SDK v2 官方页 |
| 补疏漏 | 未给 v2 迁移要点 | 补 `FastMCP` → `MCPServer`、模块迁至 `mcp.server.mcpserver`、`get_context()` 移除、传输配置移入 `run()`、三个装饰器兼容 |
| 纠错 | 核心要点第 3 条「SSE（已废弃）」把两种 SSE 混为一谈 | 拆开讲：废弃的是 HTTP+SSE 双端点传输（SEP-2596 归档与移除时间），SSE 作为流式机制仍在 Streamable HTTP 内部；补传输对照表 |
| 加厚 | 核心要点第 4 条鉴权只有一行 | 补 CIMD 取代 DCR(RFC 7591)、移除时间、RFC 9207 `iss` 校验、`application_type`、SEP-990 identity-assertion |
| 补疏漏 | 快速开始无验收判据 | 补三步验收表（版本自检 / 接入 host / 调用工具）与「host 看不到工具」五步排查顺序（含 stdio 被 `print` 污染） |

已复核无需修改：示例服务器表列 8 个文件、`generate_config.py` 六平台模板、`http_server.py` 用 Streamable HTTP（本机主源复核一致）。

外部来源已登记至 `sources/learning-notes.md`（B6 节）与 `sources/dep-cve.md`（PyPI 包元数据）。

> 回链：[[CORRECTIONS]] · [[AGENTS]]
