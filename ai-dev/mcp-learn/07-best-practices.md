# 07 — 最佳实践与安全

## 设计原则

### 1. 工具设计

```python
# 好: 单一职责, 描述清晰
@mcp.tool()
async def get_weather(city: str) -> str:
    """获取指定城市的当前天气信息, 包括温度、湿度、风速"""
    ...

# 坏: 职责不清, 描述模糊
@mcp.tool()
async def do_stuff(data: dict) -> str:
    """处理数据"""
    ...
```

- 每个工具只做一件事
- description 要写清楚功能和使用场景
- 参数名要语义化
- 使用 Pydantic 做输入验证

### 2. 错误处理

```python
# 好: 抛出有意义的异常
@mcp.tool()
async def read_file(path: str) -> str:
    """读取文件内容"""
    if ".." in path or path.startswith("/"):
        raise ValueError("不允许的路径")
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"文件不存在: {path}")

# 坏: 吞掉异常
@mcp.tool()
async def read_file_bad(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except:
        return ""  # 什么信息都没有
```

### 3. 命名规范

```python
# Tools: 动词 + 名词, snake_case
get_weather
search_documents
create_user
delete_file

# Resources: URI 格式, 描述性路径
file://reports/sales_2025.pdf
db://users/profile
config://app/settings

# Prompts: 名词短语, 描述模板用途
code_review
summarize_article
generate_sql
```

## 安全最佳实践

### 1. 输入验证

```python
import re
from pathlib import Path

@mcp.tool()
async def secure_file_read(filename: str) -> str:
    """安全地读取文件"""
    # 1. 白名单验证文件名
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValueError("文件名包含不允许的字符")

    # 2. 限制访问目录
    base_dir = Path("/safe/data/dir")
    file_path = (base_dir / filename).resolve()

    # 3. 防止路径穿越
    if not str(file_path).startswith(str(base_dir)):
        raise ValueError("不允许的路径")

    return file_path.read_text()
```

### 2. SQL 注入防护

```python
@mcp.tool()
async def search_users(name: str) -> str:
    """搜索用户 — 使用参数化查询"""
    # 好: 参数化查询
    query = "SELECT * FROM users WHERE name = ?"
    results = await db.execute(query, [name])
    return results

    # 坏: 字符串拼接 (永远不要这样做!)
    # query = f"SELECT * FROM users WHERE name = '{name}'"
```

### 3. 速率限制

```python
import time
from functools import wraps

def rate_limit(max_calls: int, period: float):
    """简单的速率限制装饰器"""
    calls = []

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [t for t in calls if now - t < period]
            if len(calls) >= max_calls:
                raise RuntimeError(f"速率限制: {max_calls} 次/{period}秒")
            calls.append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@mcp.tool()
@rate_limit(max_calls=10, period=60)
async def expensive_api_call(query: str) -> str:
    """受限制的 API 调用"""
    ...
```

### 4. 权限检查

```python
@mcp.tool()
async def admin_operation(action: str, ctx) -> str:
    """需要管理员权限的操作"""
    # 从上下文获取用户信息
    user = ctx.get("user")
    if not user or "admin" not in user.get("roles", []):
        raise PermissionError("需要管理员权限")
    return perform_admin_action(action)
```

### 5. 日志与审计

```python
import logging

logger = logging.getLogger("mcp-server")

@mcp.tool()
async def sensitive_operation(record_id: str, ctx) -> str:
    """敏感操作需要记录审计日志"""
    logger.info(
        f"用户 {ctx.get('user', 'unknown')} "
        f"在 {datetime.now()} "
        f"执行了 sensitive_operation({record_id})"
    )
    return process_record(record_id)
```

## 性能优化

### 1. 连接池

```python
# 数据库连接池
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
)

@mcp.tool()
async def query_db(sql: str) -> str:
    async with AsyncSession(engine) as session:
        result = await session.execute(sql)
        return str(result.scalars().all())
```

### 2. 缓存

```python
from functools import lru_cache
import time

# 对于频繁访问的资源, 可以加缓存
cache = {}

@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """获取股票价格 (带缓存)"""
    if symbol in cache:
        data, timestamp = cache[symbol]
        if time.time() - timestamp < 60:  # 60 秒缓存
            return data

    price = await fetch_price_from_api(symbol)
    cache[symbol] = (price, time.time())
    return price
```

## 测试

```python
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.fixture
async def mcp_session():
    """创建 MCP 会话用于测试"""
    params = StdioServerParameters(
        command="python", args=["my_server.py"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

@pytest.mark.asyncio
async def test_greet_tool(mcp_session):
    result = await mcp_session.call_tool("greet", {"name": "测试"})
    assert "测试" in result.content[0].text

@pytest.mark.asyncio
async def test_divide_by_zero(mcp_session):
    with pytest.raises(Exception) as exc:
        await mcp_session.call_tool("divide", {"a": 1, "b": 0})
    assert "除数不能为零" in str(exc.value)
```

## 项目结构建议

```
my-mcp-server/
├── pyproject.toml          # 项目配置和依赖
├── README.md               # 说明文档
├── src/
│   └── my_server/
│       ├── __init__.py
│       ├── server.py       # 主服务器入口
│       ├── tools/          # 工具模块
│       │   ├── __init__.py
│       │   ├── search.py
│       │   └── data.py
│       ├── resources/      # 资源模块
│       │   └── files.py
│       └── prompts/        # 提示模块
│           └── templates.py
├── tests/
│   ├── test_tools.py
│   └── test_resources.py
└── claude_desktop_config.json.example
```
