# 09 — 跨平台兼容: 让 MCP 服务器一次编写到处运行

MCP 协议本身是标准化的，但**不同客户端的配置文件格式和传输支持存在差异**。本章教你如何编写兼容所有主流平台的 MCP 服务器。

## 兼容性速查表

| 客户端 | 配置位置 | 根 Key | stdio | HTTP | Server 标识 |
|--------|----------|--------|-------|------|-------------|
| **Claude Code** | `.mcp.json` / `~/.claude.json` | `mcpServers` | 支持 | 支持 | object key |
| **Claude Desktop** | `~/Library/.../claude_desktop_config.json` | `mcpServers` | 支持 | 不支持 | object key |
| **OpenCode** | `~/.config/opencode/opencode.json` | `mcp` | 支持 | 支持 | object key + `type` |
| **Cursor** | `~/.cursor/mcp.json` | `mcpServers` | 支持 | 支持 | object key |
| **VS Code Copilot** | `.vscode/mcp.json` | `servers` | 支持 | 支持 | object key + `type` |
| **Zed** | `~/.config/zed/settings.json` | `context_servers` | 支持 | 不支持 | object key |
| **Continue.dev** | `~/.continue/config.json` | `mcpServers` (array!) | 支持 | 支持 | `name` field |
| **Cline** | VS Code 面板设置 | `mcpServers` | 支持 | 部分 | object key |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` | 支持 | 部分 | object key |

## 核心原则: 三层兼容策略

```
第一层: 协议兼容 (保证你的 MCP 服务器能用)
    ↓
第二层: 传输兼容 (选择最广泛支持的传输方式)
    ↓
第三层: 配置兼容 (为每个平台提供配置指南)
```

### 第一层: 协议兼容

**必须做到:**
1. 使用标准 JSON-RPC 2.0 (SDK 自动处理)
2. 正确实现 `initialize` 握手 (SDK 自动处理)
3. 返回标准格式的结果

**避免:**
1. 使用非标准 JSON-RPC 方法名
2. 在 tool/resource 响应中使用自定义字段名
3. 依赖特定客户端的扩展功能 (如 Claude 独有特性)

```python
# 好: 标准返回格式
@mcp.tool()
def my_tool(param: str) -> str:
    return "result"

# 避免: 依赖特定客户端特性
@mcp.tool()
def my_tool(param: str) -> str:
    # 不要假设 Claude 的特定行为
    # 不要依赖客户端会显示图片等
    return "result"
```

### 第二层: 传输兼容

**选择优先级:**

```
1. stdio                       ← 所有平台都支持, 零配置
2. Streamable HTTP             ← 远程场景, 大部分新平台支持
3. SSE                         ← 已废弃, 不推荐新项目使用
```

**结论: 默认用 stdio，需要远程时用 Streamable HTTP。**

```python
# 兼容写法: 同时支持 stdio 和 HTTP
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cross-platform-server")

@mcp.tool()
def hello() -> str:
    return "Hello"

if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
```

### 第三层: 配置兼容

为每个平台写清楚配置方式，提供配置模板。

---

## 各平台详细配置

### 1. Claude Code (最完整支持)

```bash
# 命令行添加
claude mcp add my-server -- python /path/to/server.py

# 或编辑 .mcp.json (项目级)
# 或 ~/.claude.json (用户级)
```

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

### 2. OpenCode

配置文件: `~/.config/opencode/opencode.json` 或项目根 `.opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "my-server": {
      "type": "local",
      "command": "python",
      "args": ["/path/to/server.py"],
      "enabled": true
    }
  }
}
```

**关键差异**:
- 根 key 是 `mcp` 不是 `mcpServers`
- 需要 `"type": "local"` 或 `"type": "remote"`
- 需要 `"enabled": true`
- 支持项目级和全局级配置

```json
// HTTP 远程服务器 (OpenCode)
{
  "mcp": {
    "my-http-server": {
      "type": "remote",
      "url": "http://your-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### 3. Cursor

配置文件: `~/.cursor/mcp.json` (全局) 或 `./.cursor/mcp.json` (项目)

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

**HTTP 传输 (Cursor):**
```json
{
  "mcpServers": {
    "my-server": {
      "url": "http://localhost:8000",
      "transport": "sse"
    }
  }
}
```

### 4. VS Code / GitHub Copilot

配置文件: `.vscode/mcp.json` (项目) 或 `~/.vscode/mcp.json` (全局)

注意: 根 key 是 **`servers`** 不是 `mcpServers`

```json
{
  "servers": {
    "my-server": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

```json
{
  "servers": {
    "my-http-server": {
      "type": "sse",
      "url": "http://localhost:8000"
    }
  }
}
```

### 5. Zed

配置文件: `~/.config/zed/settings.json`

使用 `context_servers` 或嵌套的 `assistant.mcp_servers`

```json
{
  "assistant": {
    "mcp_servers": {
      "my-server": {
        "command": "python",
        "args": ["/path/to/server.py"]
      }
    }
  }
}
```

注意: Zed 只支持 stdio，不支持远程 HTTP。

### 6. Continue.dev

配置文件: `~/.continue/config.json`

**关键差异**: `mcpServers` 是**数组**，每个元素有 `name` 字段

```json
{
  "mcpServers": [
    {
      "name": "my-server",
      "transport": {
        "type": "stdio",
        "command": "python",
        "args": ["/path/to/server.py"]
      }
    }
  ]
}
```

也可以使用 YAML 文件放在 `.continue/mcpServers/`:

```yaml
# .continue/mcpServers/my-server.yaml
type: stdio
command: python
args:
  - /path/to/server.py
```

---

## 编写跨平台服务器的最佳实践

### 1. 使用 stdio 作为默认传输

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def greet(name: str) -> str:
    """向指定的人打招呼"""
    return f"你好, {name}!"

if __name__ == "__main__":
    # 默认 stdio — 所有平台兼容
    mcp.run(transport="stdio")
```

### 2. 无外部依赖或声明清楚

```bash
# 提供 requirements.txt
pip install mcp

# 或 setup.cfg / pyproject.toml
[project]
dependencies = ["mcp>=1.0"]
```

### 3. 提供多平台配置模板

创建一个 `configs/` 目录:

```
my-mcp-server/
├── server.py
├── requirements.txt
├── configs/
│   ├── claude-code.json       # Claude Code / Desktop
│   ├── opencode.json          # OpenCode
│   ├── cursor.json            # Cursor
│   ├── vscode-copilot.json    # VS Code Copilot
│   ├── zed.json               # Zed
│   └── continue.json          # Continue.dev
└── README.md
```

各配置文件内容:

**claude-code.json:**
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["${SERVER_PATH}/server.py"]
    }
  }
}
```

**opencode.json:**
```json
{
  "mcp": {
    "my-server": {
      "type": "local",
      "command": "python",
      "args": ["${SERVER_PATH}/server.py"],
      "enabled": true
    }
  }
}
```

**cursor.json:**
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["${SERVER_PATH}/server.py"]
    }
  }
}
```

**vscode-copilot.json:**
```json
{
  "servers": {
    "my-server": {
      "type": "stdio",
      "command": "python",
      "args": ["${SERVER_PATH}/server.py"]
    }
  }
}
```

**continue.json:**
```json
{
  "mcpServers": [
    {
      "name": "my-server",
      "transport": {
        "type": "stdio",
        "command": "python",
        "args": ["${SERVER_PATH}/server.py"]
      }
    }
  ]
}
```

### 4. 用 pipx/npx 分发 (可选)

```bash
# Python 服务器发布到 PyPI 后用 pipx 安装
pipx install my-mcp-server

# 配置时直接用可执行文件名
# {"command": "my-mcp-server", "args": []}
# 不需要绝对路径, 所有平台通用
```

### 5. 提供一键安装脚本

```bash
#!/bin/bash
# install.sh — 一键安装到所有平台

SERVER_PATH="$(pwd)/server.py"

install_to_claude() { ... }
install_to_opencode() { ... }
install_to_cursor() { ... }

echo "选择要安装到的平台:"
echo "1) Claude Code"
echo "2) OpenCode"
echo "3) Cursor"
echo "4) VS Code Copilot"
echo "5) 全部"
read -p "> " choice
```

---

## 已知兼容性陷阱

### 1. Prompt 原语支持有限

大部分客户端只支持 Tools 和 Resources，**Prompts 支持较少的平台**:

| 平台 | Tools | Resources | Prompts |
|------|-------|-----------|---------|
| Claude Desktop | 支持 | 支持 | 支持 |
| Claude Code | 支持 | 支持 | 支持 |
| OpenCode | 支持 | 部分 | 不支持 |
| Cursor | 支持 | 部分 | 不支持 |
| VS Code Copilot | 支持 | 不支持 | 不支持 |

**建议**: 核心功能用 Tool 实现，Resource/Prompt 作为辅助。不要把关键逻辑只放在 Prompt 里。

### 2. 环境变量注入

不同平台注入环境变量的方式不同:

```json
// Claude Desktop / Claude Code
{ "env": { "MY_KEY": "xxx" } }

// OpenCode
{ "env": { "MY_KEY": "xxx" } }

// Continue.dev
{ "transport": { "env": { "MY_KEY": "xxx" } } }

// VS Code Copilot — 不支持 env, 需要用户在 shell 中设置
```

**建议**: 用系统环境变量 + `.env` 文件作为 fallback:

```python
import os
from pathlib import Path

# 尝试多种方式获取 API Key
def get_api_key() -> str:
    # 1. 环境变量 (最通用)
    key = os.environ.get("MY_API_KEY")
    if key:
        return key
    # 2. .env 文件
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("MY_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"\'')
    raise ValueError("未找到 MY_API_KEY")
```

### 3. 项目级 vs 全局级配置

| 平台 | 支持项目级 | 支持全局级 | 优先级 |
|------|-----------|------------|--------|
| Claude Code | `.mcp.json` | `~/.claude.json` | 项目 > 全局 |
| OpenCode | `.opencode/opencode.json` | `~/.config/opencode/opencode.json` | 项目 > 全局 |
| Cursor | `.cursor/mcp.json` | `~/.cursor/mcp.json` | 项目 > 全局 |
| VS Code Copilot | `.vscode/mcp.json` | `~/.vscode/mcp.json` | 项目 > 全局 |

### 4. 二进制路径差异

```python
# 坏: 硬编码路径
ADDR2LINE = "/usr/bin/addr2line"

# 好: 运行时查找
import shutil
ADDR2LINE = shutil.which("addr2line") or _search_ndk()
```

---

## 适配 OpenCode 的特殊要点

OpenCode 作为新兴的开源 AI 编码工具，有几点值得注意:

### 配置结构

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "server-name": {
      "type": "local",       // 必需: "local" 或 "remote"
      "command": "python",   // 本地模式
      "args": ["server.py"],
      "enabled": true,       // 必需
      "env": {}
    }
  }
}
```

### 与 Claude Desktop 的主要差异

| 维度 | Claude Desktop | OpenCode |
|------|---------------|----------|
| 根 key | `mcpServers` | `mcp` |
| 类型字段 | 无 (隐式 stdio) | `"type": "local"/"remote"` |
| enabled | 无 | 必须有 `"enabled": true` |
| 远程支持 | 不支持 | 支持 HTTP + 认证 header |
| JSON Schema | 无 | `$schema` 可选 |

### 已知问题

1. 项目级配置可能不生效 (issue #4054)，临时方案是放全局配置
2. 建议测试时先放 `~/.config/opencode/opencode.json`

---

## 总结

**编写跨平台 MCP 服务器的 checklist:**

- [ ] 使用 stdio 作为默认传输
- [ ] 提供 `--http` 选项支持远程模式
- [ ] 无平台特定的硬编码路径
- [ ] 环境变量从多种来源读取
- [ ] 核心功能用 Tool 实现 (不依赖 Prompt/Resource)
- [ ] 提供多平台配置模板 (`configs/` 目录)
- [ ] README 写清楚每个平台的配置方式
- [ ] 测试覆盖: 至少 Claude Code + OpenCode + Cursor
