# 06 — 传输层详解

## 三种传输方式对比

| 特性 | stdio | Streamable HTTP | SSE (已废弃) |
|------|-------|-----------------|-------------|
| 通信方式 | 子进程管道 | HTTP 请求/响应 | HTTP 长连接 |
| 适用场景 | 本地桌面应用 | 远程服务器、Web 应用 | 已不推荐使用 |
| 连接方向 | 双向 | 双向 | 单向 (服务器→客户端) |
| 网络要求 | 无 | 需要 TCP 连接 | 需要 TCP 连接 |
| 认证 | 进程级信任 | OAuth 2.0 | OAuth 2.0 |
| 负载均衡 | 不支持 | 支持 | 复杂 |
| 协议版本 | 2025-03-26+ | 2025-03-26+ | 2025-03-26 前 |

## stdio 传输

### 工作原理

```
Host 应用
  └── 启动子进程 (python/ node)
       └── stdin/stdout 管道通信
            └── JSON-RPC 消息序列化
```

### 服务端

```python
# 最简单的 stdio 服务器
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stdio-server")

@mcp.tool()
def hello() -> str:
    return "Hello from stdio!"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 客户端

```python
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(
    command="python",
    args=["server.py"],
    env={"API_KEY": "xxx"},  # 可选: 环境变量
)

async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # ... 使用 session
```

### 优缺点

| 优点 | 缺点 |
|------|------|
| 零网络配置 | 仅限本机 |
| 进程隔离安全 | 每个 Host 独立启动 |
| 无需认证 | 不支持远程访问 |
| 简单可靠 | 资源开销较高 |

## Streamable HTTP 传输

### 工作原理

```
Host 应用                         MCP Server
    │                                  │
    ├──── POST /mcp ──────────────>   │ (请求)
    │     {jsonrpc: "2.0", ...}       │
    │                                  │
    │<──── 200 OK ─────────────────│ (响应)
    │     {jsonrpc: "2.0", ...}       │
    │                                  │
    ├──── GET /mcp ───────────────>   │ (SSE 流, 可选)
    │                                  │
    │<──── SSE stream ─────────────│ (服务器推送)
```

### 服务端

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("http-server")

@mcp.tool()
async def remote_query(sql: str) -> str:
    """远程数据库查询"""
    return await execute_sql(sql)

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        # 可选路径前缀
        # path="/mcp",
    )
```

### 客户端

```python
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://localhost:8000") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # ... 使用 session
```

### 生产部署

```bash
# 使用 uvicorn 运行 (推荐用于生产)
uvicorn server:mcp.sse_app --host 0.0.0.0 --port 8000

# 使用 gunicorn + uvicorn workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:mcp.sse_app
```

```nginx
# Nginx 反向代理配置
server {
    listen 443 ssl;
    server_name mcp.example.com;

    location /mcp {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400s;  # SSE 长连接
        proxy_buffering off;        # 禁用缓冲
    }
}
```

## 传输选择指南

```
服务器在哪里运行？
├── 本机, 与 Host 同一台机器
│   └── 使用 stdio (最简单)
│
├── 远程服务器
│   ├── 需要负载均衡 → Streamable HTTP
│   ├── 需要 OAuth 认证 → Streamable HTTP
│   └── 需要跨网络访问 → Streamable HTTP
│
└── 两种都需要
    └── 使用协议工厂模式, 同时支持 stdio 和 HTTP
```

## 同时支持多种传输

```python
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("multi-transport-server")

@mcp.tool()
def hello() -> str:
    return "Hello!"

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
    else:
        mcp.run(transport="stdio")
```
