# 03 — 服务器开发详解

## FastMCP vs 底层 API

Python SDK 提供两层 API:

| 层级 | API | 适用场景 |
|------|-----|----------|
| 高层 | `FastMCP` (装饰器风格) | 快速开发，90% 的场景 |
| 底层 | `mcp.server.Server` (类继承) | 需要细粒度控制时 |

### FastMCP 方式 (推荐)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
async def my_tool(query: str) -> str:
    """工具描述 — 会自动生成 JSON Schema"""
    return f"处理结果: {query}"
```

### 底层 API 方式

```python
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities

server = Server("my-server")

@server.list_tools()
async def list_tools() -> list:
    return [
        {
            "name": "my_tool",
            "description": "工具描述",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list:
    if name == "my_tool":
        return [{"type": "text", "text": f"结果: {arguments['query']}"}]
    raise ValueError(f"未知工具: {name}")
```

## Tools (工具)

Tools 是模型可以主动调用的操作，类似 API 端点。

```python
from pydantic import BaseModel, Field
from typing import Literal

# 使用 Pydantic 定义复杂输入
class WeatherInput(BaseModel):
    city: str = Field(description="城市名称")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="温度单位"
    )

@mcp.tool()
async def get_weather(params: WeatherInput) -> str:
    """获取指定城市的天气信息"""
    # 实际调用天气 API
    return f"{params.city}: 22°{params.units}"

# 工具可以返回多种内容类型
from mcp.types import TextContent, ImageContent, EmbeddedResource

@mcp.tool()
async def analyze_image(url: str) -> list:
    """分析图片并返回结果"""
    return [
        TextContent(type="text", text="图片分析结果: ..."),
        # ImageContent(type="image", data="base64...", mimeType="image/png"),
    ]
```

## Resources (资源)

Resources 是应用控制的只读数据暴露方式。

```python
# 静态资源
@mcp.resource("config://settings")
def get_settings() -> str:
    """返回应用设置"""
    return '{"theme": "dark", "language": "zh"}'

# 动态资源 (带参数)
@mcp.resource("file://{path}")
async def read_file(path: str) -> str:
    """读取指定文件内容"""
    with open(path, "r") as f:
        return f.read()

# 资源模板 (URI 模板)
@mcp.resource("db://users/{user_id}")
async def get_user(user_id: str) -> str:
    """获取用户信息"""
    return f'{{"id": "{user_id}", "name": "张三"}}'
```

## Prompts (提示模板)

Prompts 是可复用的交互模板，由用户触发。

```python
@mcp.prompt()
def code_review(code: str) -> str:
    """代码审查提示模板"""
    return f"""请审查以下代码，关注:
1. 安全问题
2. 性能问题
3. 可读性

代码:
{code}
"""

@mcp.prompt()
def summarize_article(url: str) -> list:
    """文章摘要提示"""
    return [
        {
            "role": "user",
            "content": f"请用 3 句话总结这篇文章: {url}"
        }
    ]
```

## 完整的服务器示例

```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Demo Server")

# ---- Tools ----
@mcp.tool()
async def web_fetch(url: str) -> str:
    """获取网页内容"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text[:1000]

@mcp.tool()
def calculate(expression: str) -> float:
    """安全的数学表达式计算"""
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expression):
        raise ValueError("表达式包含不允许的字符")
    return eval(expression)

# ---- Resources ----
@mcp.resource("health://status")
def health_check() -> str:
    return "OK"

# ---- Prompts ----
@mcp.prompt()
def explain_error(error_message: str, language: str = "zh") -> str:
    return f"解释这个错误信息(用{language}): {error_message}"

if __name__ == "__main__":
    # 开发时用 HTTP，方便调试
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
```

## 错误处理

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Error Demo")

@mcp.tool()
async def divide(a: float, b: float) -> float:
    """除法运算"""
    if b == 0:
        raise ValueError("除数不能为零")  # 自动转换为 JSON-RPC 错误
    return a / b

# 自定义错误处理
@mcp.tool()
async def safe_api_call(url: str) -> str:
    try:
        # API 调用逻辑
        return "success"
    except TimeoutError:
        raise RuntimeError("API 调用超时")
    except Exception as e:
        raise RuntimeError(f"未知错误: {e}")
```

## 服务器生命周期

```python
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

# 使用 lifespan 管理资源
@asynccontextmanager
async def lifespan(server: FastMCP):
    # 启动时
    print("服务器启动中...")
    db = await connect_database()
    yield {"db": db}
    # 关闭时
    print("服务器关闭中...")
    await db.disconnect()

mcp = FastMCP("Lifespan Demo", lifespan=lifespan)

@mcp.tool()
async def query_data(query: str, ctx) -> str:
    db = ctx.lifespan_context["db"]
    return await db.query(query)
```
