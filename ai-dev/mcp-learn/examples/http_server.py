"""HTTP MCP 服务器 — 支持 Streamable HTTP 传输, 适用于远程访问"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("HTTP MCP Server")

@mcp.tool()
async def echo(message: str) -> str:
    """回声工具 — 返回相同的消息"""
    return f"Echo: {message}"

@mcp.tool()
async def enumerate_list(items: list[str]) -> str:
    """将列表编号后返回"""
    return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

@mcp.resource("info://server")
def server_info() -> str:
    return '{"name": "HTTP MCP Server", "version": "1.0.0", "transport": "streamable-http"}'

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    print(f"MCP HTTP Server running on http://{host}:{port}")
    mcp.run(transport="streamable-http", host=host, port=port)
