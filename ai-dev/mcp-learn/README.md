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
# 安装 Python SDK
pip install mcp

# 运行示例服务器
cd examples/
python simple_server.py
```

## 核心要点

1. **协议基础**: JSON-RPC 2.0，客户端-服务器架构
2. **三种原语**: Tools (模型控制的操作)、Resources (应用控制的只读数据)、Prompts (可复用交互模板)
3. **传输方式**: stdio (本地)、Streamable HTTP (远程)、SSE (已废弃)
4. **鉴权**: OAuth 2.0 + Client ID Metadata Documents
