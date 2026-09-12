"""MCP 客户端示例 — 演示如何连接和使用 MCP 服务器"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def demo_stdio_client():
    """演示连接 stdio MCP 服务器"""
    server_params = StdioServerParameters(
        command="python",
        args=["simple_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化
            await session.initialize()
            print("已连接到服务器")

            # 列出工具
            tools_result = await session.list_tools()
            print(f"\n=== 可用工具 ({len(tools_result.tools)} 个) ===")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")

            # 调用工具
            print("\n=== 调用 greet 工具 ===")
            result = await session.call_tool("greet", {"name": "世界"})
            print(f"  结果: {result.content[0].text}")

            print("\n=== 调用 add 工具 ===")
            result = await session.call_tool("add", {"a": 3, "b": 5})
            print(f"  结果: {result.content[0].text}")

            # 列出资源
            resources_result = await session.list_resources()
            print(f"\n=== 可用资源 ({len(resources_result.resources)} 个) ===")
            for res in resources_result.resources:
                print(f"  - {res.uri}")

            # 读取资源
            print("\n=== 读取 config://version ===")
            resource = await session.read_resource("config://version")
            print(f"  内容: {resource.contents[0].text}")

            # 列出提示
            prompts_result = await session.list_prompts()
            print(f"\n=== 可用提示 ({len(prompts_result.prompts)} 个) ===")
            for prompt in prompts_result.prompts:
                print(f"  - {prompt.name}: {prompt.description}")

            print("\n完成!")

async def demo_http_client():
    """演示连接 HTTP MCP 服务器"""
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client("http://127.0.0.1:8000") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("已连接到 HTTP MCP 服务器")

            tools = await session.list_tools()
            print(f"可用工具: {[t.name for t in tools.tools]}")

            result = await session.call_tool("echo", {"message": "Hello HTTP!"})
            print(f"Echo 结果: {result.content[0].text}")

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        print("运行 HTTP 客户端模式 (需要先启动 http_server.py)")
        asyncio.run(demo_http_client())
    else:
        print("运行 stdio 客户端模式")
        asyncio.run(demo_stdio_client())
