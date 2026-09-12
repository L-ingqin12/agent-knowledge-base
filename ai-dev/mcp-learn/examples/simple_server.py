"""最简单的 MCP 服务器示例 — 快速入门"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Simple Demo Server")

@mcp.tool()
def greet(name: str) -> str:
    """向指定的人打招呼"""
    return f"你好, {name}!"

@mcp.tool()
def add(a: int, b: int) -> int:
    """计算两个整数的和"""
    return a + b

@mcp.resource("config://version")
def get_version() -> str:
    """服务器版本信息"""
    return "1.0.0"

@mcp.prompt()
def code_review(code: str) -> str:
    """代码审查模板"""
    return f"请审查以下代码的安全性、性能和可读性:\n\n{code}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
