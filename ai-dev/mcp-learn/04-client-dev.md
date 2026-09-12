# 04 — 客户端开发详解

## 客户端的作用

MCP 客户端运行在 Host 内部，负责:
1. 管理 MCP 服务器的连接生命周期
2. 发现服务器的能力 (Tools/Resources/Prompts)
3. 将 AI 模型的调用请求转发给服务器
4. 将服务器返回的结果传给 AI 模型

## 基础客户端

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 定义服务器参数 (通过 stdio 启动子进程)
    server_params = StdioServerParameters(
        command="python",
        args=["hello_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        # 创建客户端会话
        async with ClientSession(read, write) as session:
            # 初始化握手
            await session.initialize()

            # 列出可用工具
            tools = await session.list_tools()
            print(f"可用工具: {[t.name for t in tools.tools]}")

            # 调用工具
            result = await session.call_tool("greet", {"name": "世界"})
            print(f"结果: {result.content[0].text}")

            # 列出资源
            resources = await session.list_resources()
            print(f"可用资源: {[r.uri for r in resources.resources]}")

            # 读取资源
            resource = await session.read_resource("config://version")
            print(f"版本: {resource.contents[0].text}")

            # 列出提示模板
            prompts = await session.list_prompts()
            print(f"可用提示: {[p.name for p in prompts.prompts]}")

asyncio.run(main())
```

## 使用 Streamable HTTP 传输

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://localhost:8000") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"服务器提供 {len(tools.tools)} 个工具")

            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

asyncio.run(main())
```

## 连接多个服务器

```python
import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

async def connect_stdio_server(command: str, args: list):
    """连接 stdio 类型的服务器"""
    params = StdioServerParameters(command=command, args=args)
    read, write = await stdio_client(params).__aenter__()
    session = await ClientSession(read, write).__aenter__()
    await session.initialize()
    return session

async def connect_http_server(url: str):
    """连接 HTTP 类型的服务器"""
    read, write, _ = await streamablehttp_client(url).__aenter__()
    session = await ClientSession(read, write).__aenter__()
    await session.initialize()
    return session

async def main():
    # 同时连接多个服务器
    servers = await asyncio.gather(
        connect_stdio_server("python", ["weather_server.py"]),
        connect_stdio_server("node", ["file_server.js"]),
        connect_http_server("http://localhost:8000"),
    )

    all_tools = []
    for session in servers:
        tools = await session.list_tools()
        all_tools.extend(tools.tools)

    print(f"总计可用工具: {len(all_tools)}")
    for tool in all_tools:
        print(f"  - {tool.name}")

asyncio.run(main())
```

## 整合 AI 模型 (以 Claude API 为例)

```python
import asyncio
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 连接 MCP 服务器
    server_params = StdioServerParameters(
        command="python", args=["weather_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 获取工具列表并转换为 Claude 格式
            tools_result = await session.list_tools()
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_result.tools
            ]

            # 调用 Claude API
            client = Anthropic()
            messages = [{"role": "user", "content": "北京今天天气怎么样?"}]

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=messages,
                tools=claude_tools,
            )

            # 处理工具调用
            for block in response.content:
                if block.type == "tool_use":
                    # 执行 MCP 工具
                    result = await session.call_tool(
                        block.name, block.input
                    )
                    print(f"工具调用结果: {result.content[0].text}")

asyncio.run(main())
```

## 通知处理

```python
async with ClientSession(read, write) as session:
    await session.initialize()

    # 订阅服务器日志
    await session.set_logging_level("debug")

    # 监听资源变更通知
    # 服务器资源变化时客户端会收到通知
    await session.list_resources()
    # 可通过 session.on_notification 注册回调
```

## 错误处理

```python
from mcp import McpError

try:
    result = await session.call_tool("nonexistent", {})
except McpError as e:
    print(f"MCP 错误: code={e.error.code}, message={e.error.message}")
except Exception as e:
    print(f"其他错误: {e}")
```
