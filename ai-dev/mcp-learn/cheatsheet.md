# MCP 速查手册

一份浓缩全部知识要点，适合快速查阅。

## 核心概念

```
Host (AI 应用) → Client (协议处理器) → Server (暴露 Tools/Resources/Prompts)
                                        ↓
                                   JSON-RPC 2.0 over stdio / HTTP
```

| 原语 | 谁控制 | 用途 | 类比 |
|------|--------|------|------|
| **Tool** | AI 模型 | 执行操作 | POST 端点 |
| **Resource** | 应用(Host) | 暴露只读数据 | GET 端点 |
| **Prompt** | 用户 | 交互模板 | 预设宏 |

## 开发速查

```python
# 最小服务器
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("name")

@mcp.tool()
def tool(param: str) -> str:
    """Tool 描述 (AI 据此决定是否调用)"""
    return f"result: {param}"

@mcp.resource("scheme://path")
def resource() -> str:
    return "data"

@mcp.prompt()
def prompt_template(arg: str) -> str:
    return f"请处理: {arg}"

if __name__ == "__main__":
    mcp.run(transport="stdio")  # 或 "streamable-http"
```

## 传输选择

```
本地开发/个人使用  → stdio
远程/团队共享      → Streamable HTTP
生产部署           → Streamable HTTP + Docker/systemd
SSE                → 已废弃, 不推荐
```

## 错误处理

```python
# ✅ 好: 结构化、LLM 友好
raise ValueError("文件不存在: /path/to/f, 请检查路径")

# ❌ 坏: 原始异常
# ConnectionError: (1040, 'Too many connections') ← 暴露内部信息
```

## 安全清单

- [ ] 读写工具分两个工具 (不同风险等级)
- [ ] 路径操作前做范围校验
- [ ] 数据库默认只读, 不暴露 DDL
- [ ] 大响应做截断/分页
- [ ] 环境变量管理密钥, 不硬编码

## 各平台配置速查

| 平台 | 配置 Key | 特殊要求 |
|------|---------|----------|
| Claude Code | `mcpServers` | — |
| OpenCode | `mcp` | 必须 `"type": "local"` + `"enabled": true` |
| Cursor | `mcpServers` | — |
| VS Code Copilot | `servers` | 必须 `"type": "stdio"` |
| Continue.dev | `mcpServers` (数组) | 每个元素需要 `"name"` 字段 |
| Zed | `assistant.mcp_servers` | 仅 stdio |

## 测试

```python
# 技术测试 Checklist
□ list_tools() 返回所有工具
□ 缺少必填参数 → 有意义的错误
□ 非法 enum 值被拒绝
□ 边界: 空输入、超长、特殊字符

# 调试
npx @modelcontextprotocol/inspector python server.py  # 可视化
python proxy.py python server.py                      # stdio 代理
```

## 生产部署

```bash
# Docker (最小安全标准)
docker run --read-only --cap-drop ALL --user 1000:1000 \
  --memory 256m --cpus 0.5 my-mcp-server

# 可观测性 (最小指标)
- mcp.tool.invocations    (调用次数)
- mcp.tool.errors         (错误率)
- mcp.tool.duration.p95   (P95 延迟)
```

## 设计原则 Top 10

1. **工作流导向** — 从用户要完成的任务反推工具, 不要 1:1 映射 API 端点
2. **一个工具一个风险等级** — 读写分离
3. **描述是产品界面** — tool description 决定 AI 何时调用
4. **渐进式暴露** — list → describe → query, 不要一次返回所有信息
5. **Token 预算敏感** — 默认截断, 提供 detail_level 参数
6. **错误信息可操作** — 告诉 AI 下一步该做什么
7. **stdout=协议, stderr=日志** — 永远不要混淆
8. **安全前置** — 路径校验、权限隔离、读写分离, 不是后加功能
9. **可观测性从第一天带** — 没有指标就是在盲飞
10. **演进, 不跳跃** — 细粒度 → 分组 → 统一接口

## MCP vs Skill 决策 (30 秒判断)

```
需要 Claude Code 没有的能力? (二进制、第三方库、数据库)
  → MCP
只是编排 Claude Code 已有能力的顺序?
  → Skill
需要跨 IDE/客户端复用?
  → MCP
超过 50 行 bash/Python?
  → MCP
```

## 目录导航

| 要学什么 | 看哪个 |
|----------|--------|
| 零基础入门 | 01 → 02 → examples/simple_server.py |
| 掌握开发 | 03 → 04 → 05 |
| 深入理解 | 06 → 07 → 10 |
| 架构决策 | 08 (MCP vs Skill) |
| 多平台 | 09 → examples/generate_config.py |
| 生产上线 | 11 → 07 |
| 案例参考 | 12 |
| 发现项目 | 13 (GitHub 高分项目目录) |
| 快速查阅 | 本页 |

## GitHub 高分项目速查

```
学习:    microsoft/mcp-for-beginners           ★16k
列表:    punkpeye/awesome-mcp-servers          ★86k
参考:    modelcontextprotocol/servers          ★87k
框架:    jlowin/fastmcp                        ★25k
案例:    playwright-mcp ★33k | github-mcp ★30k
企业:    bh-rat/awesome-mcp-enterprise         精选
```
