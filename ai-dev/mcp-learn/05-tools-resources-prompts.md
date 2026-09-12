# 05 — 三大核心原语详解

## 对比总览

| 维度 | Tools | Resources | Prompts |
|------|-------|-----------|---------|
| 控制方 | AI 模型 | 应用 (Host) | 用户 |
| 触发方式 | 模型决定调用 | 应用主动读取 | 用户选择 |
| 数据流向 | 双向 (输入→输出) | 单向 (服务器→应用) | 单向 (模板→模型) |
| 是否修改状态 | 可以 | 只读 | 只读 |
| 类比 | POST/PUT 端点 | GET 端点 | 预设宏/工作流 |
| JSON Schema | 需要定义 inputSchema | 不需要 | 可选参数 |

## Tools 深入

### 输入模式定义

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

class SearchParams(BaseModel):
    """搜索参数 — 自动生成为 JSON Schema"""
    query: str = Field(description="搜索关键词")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量 (1-100)")
    offset: int = Field(default=0, ge=0, description="分页偏移")
    order: SortOrder = Field(default=SortOrder.DESC, description="排序方式")
    category: Optional[str] = Field(default=None, description="分类过滤")

@mcp.tool()
async def search_database(params: SearchParams) -> str:
    """在数据库中搜索"""
    results = await db.search(
        query=params.query,
        limit=params.limit,
        offset=params.offset,
        order=params.order.value,
        category=params.category,
    )
    return results.to_json()
```

### 返回复杂内容

```python
from mcp.types import (
    TextContent,
    ImageContent,
    EmbeddedResource,
)

@mcp.tool()
async def multi_content_tool(query: str) -> list:
    """返回多种内容类型"""
    return [
        TextContent(
            type="text",
            text=f"文本分析结果: {query}"
        ),
        ImageContent(
            type="image",
            data="base64_encoded_image...",
            mimeType="image/png",
        ),
        EmbeddedResource(
            type="resource",
            resource={
                "uri": "file://report.pdf",
                "mimeType": "application/pdf",
                "text": "报告内容...",
            }
        ),
    ]
```

## Resources 深入

### URI 设计规范

```
`<scheme>://<path>`

示例:
  file://documents/report.txt        — 文件系统
  db://users/123                     — 数据库记录
  api://weather/beijing             — API 数据
  config://settings/theme            — 配置项
  health://status                    — 健康检查
```

### 资源订阅 (变更通知)

```python
from mcp.types import Resource

@mcp.resource("data://realtime/{stream_id}")
async def realtime_data(stream_id: str) -> str:
    """实时数据流"""
    return get_stream_data(stream_id)

# 数据更新时, 服务器可以通知客户端
# await session.send_resource_updated("data://realtime/sensor1")
```

### 资源列表与分页

```python
@mcp.list_resources()
async def list_resources(cursor: str | None = None) -> list:
    """分页列出资源"""
    page_size = 100
    files = get_files_after(cursor, page_size)
    return [
        Resource(
            uri=f"file://{f.path}",
            name=f.name,
            mimeType="text/plain",
        )
        for f in files
    ]
```

## Prompts 深入

### 多轮对话模板

````python
from mcp.types import PromptMessage, TextContent

@mcp.prompt()
def interview_practice(role: str, difficulty: str = "medium") -> list:
    """面试练习模板"""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"你是一位{role}面试官。"
                     f"请出一道{difficulty}难度的{role}面试题。"
            )
        ),
    ]

@mcp.prompt()
def step_by_step_debug(error: str, code: str) -> list:
    """分步调试模板 — 注意: 代码块的数量要与外层不同以避免嵌套"""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"请按以下步骤分析问题:\n\n"
                     f"1. 阅读错误信息: {error}\n"
                     f"2. 分析相关代码:\n{code}\n"
                     f"3. 识别可能的根本原因\n"
                     f"4. 提供修复建议\n"
                     f"5. 给出修复后的代码"
            )
        ),
    ]
````

## 选型指南

```
需要让 AI 执行操作？
├── 是 → 使用 Tool
│   ├── 计算/查询 → Tool
│   ├── 创建/修改/删除 → Tool
│   └── 调用外部 API → Tool
│
└── 否 → 需要提供上下文数据？
    ├── 是 → 使用 Resource
    │   ├── 静态数据 (配置文件) → Resource
    │   ├── 动态数据 (数据库) → Resource
    │   └── 文件内容 → Resource
    │
    └── 否 → 需要引导交互？
        └── 是 → 使用 Prompt
```
