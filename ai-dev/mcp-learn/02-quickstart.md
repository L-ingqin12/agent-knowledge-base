# 02 — 快速开始

## 环境要求

- Python 3.10+
- pip

## 安装 SDK

```bash
pip install mcp
```

这是 Anthropic 官方 Python SDK，包含服务端和客户端的所有功能。

### 可选工具

```bash
# MCP Inspector — 浏览器中调试 MCP 服务器
npx @modelcontextprotocol/inspector

# MCP CLI — 命令行测试工具
pip install mcp-cli
```

## 第一个 MCP 服务器

创建 `hello_server.py`:

```python
from mcp.server.fastmcp import FastMCP

# 创建服务器实例
mcp = FastMCP("Hello World Server")

@mcp.tool()
def greet(name: str) -> str:
    """向指定的人打招呼"""
    return f"你好, {name}!"

@mcp.tool()
def add(a: int, b: int) -> int:
    """计算两个数的和"""
    return a + b

@mcp.resource("config://version")
def get_version() -> str:
    """返回服务器版本信息"""
    return "1.0.0"

if __name__ == "__main__":
    # 使用 stdio 传输运行 (用于 Claude Desktop)
    mcp.run(transport="stdio")
```

## 测试服务器

### 方式一: MCP Inspector (推荐)

```bash
npx @modelcontextprotocol/inspector python hello_server.py
```

浏览器打开 `http://localhost:5173`，可以看到:
- 服务器信息
- 可用的 Tools 列表
- 可以交互式调用工具

### 方式二: Claude Desktop 集成

编辑 Claude Desktop 配置文件:

```json
{
  "mcpServers": {
    "hello-world": {
      "command": "python",
      "args": ["/path/to/hello_server.py"]
    }
  }
}
```

配置文件位置:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## 运行模式

```python
# stdio 模式 (默认, 用于本地桌面应用)
mcp.run(transport="stdio")

# HTTP 模式 (用于远程访问)
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

## 验证服务器

使用 MCP CLI:

```bash
# 列出可用工具
mcp-cli --server "python hello_server.py" tools list

# 调用工具
mcp-cli --server "python hello_server.py" tools call greet --args '{"name": "世界"}'
```
