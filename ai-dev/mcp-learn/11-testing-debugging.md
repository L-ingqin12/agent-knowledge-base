# 11 — 测试、调试与生产部署

MCP 服务器在本质上是**微服务**——需要传统服务的所有运维严谨性。

## 测试策略

### 两层测试模型

```
技术测试 (Technical Testing)          行为测试 (Behavioral Testing)
  ↓                                      ↓
协议正确性、参数校验、错误处理           AI 模型能否有效使用你的工具
  ↓                                      ↓
CI/CD 自动化                            Agent 集成测试
```

### 技术测试

```python
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@pytest.fixture
async def mcp_session():
    params = StdioServerParameters(
        command="python", args=["my_server.py"]
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

class TestToolDiscovery:
    """验证工具发现"""
    async def test_all_tools_listed(self, mcp_session):
        tools = await mcp_session.list_tools()
        names = {t.name for t in tools.tools}
        assert "greet" in names
        assert "add" in names

class TestParameterValidation:
    """验证参数校验"""
    async def test_missing_required_param(self, mcp_session):
        try:
            await mcp_session.call_tool("greet", {})
            assert False, "应该抛出错误"
        except Exception as e:
            assert "name" in str(e).lower()

    async def test_invalid_enum(self, mcp_session):
        try:
            await mcp_session.call_tool("add", {"a": 1, "b": "xxx"})
            assert False, "应该抛出错误"
        except Exception:
            pass

class TestErrorMessages:
    """验证错误信息质量"""
    async def test_divide_by_zero_message(self, mcp_session):
        try:
            await mcp_session.call_tool("divide", {"a": 1, "b": 0})
            assert False
        except Exception as e:
            # 错误信息应该具体, 不是 "Internal error"
            msg = str(e).lower()
            assert any(w in msg for w in ["除数", "zero", "division"])
```

### 行为测试

技术测试通过后，还要验证 AI 模型**确实会调用你的工具**来解决问题:

```python
async def test_ai_chooses_correct_tool():
    """验证 AI 在面对自然语言时选择了正确的工具"""
    prompt = "北京今天天气怎么样?"
    # 给 AI 工具列表, 验证它调用了 get_weather 而不是 search_web
    ...
```

**关键洞察**: 一个技术上正确但描述模糊的工具，AI 在生产中会静默失败（不调用）。

### 测试 Checklist

- [ ] `list_tools()` 返回所有预期工具
- [ ] 缺少必填参数时返回有意义的错误
- [ ] 非法 enum 值被拒绝
- [ ] 返回内容的 shape 一致 (不是只检查 `len > 0`)
- [ ] 默认参数值与显式传参行为一致
- [ ] 边界情况: 空列表、空字符串、超长输入

---

## 调试策略

### 核心问题: stdio 是不透明的

MCP 通过 stdio 通信——没有内置日志、没有 HTTP inspector、客户端看不到服务端错误。

常见症状: `-32001: Request timed out` (服务端静默崩溃了)。

### 方案一: stdio 代理 (协议级调试)

在 client 和 server 之间插入透明代理，记录所有 JSON-RPC 消息:

```
AI Client  ←→  stdio Proxy  ←→  MCP Server
                   ↓
              Log File (所有消息 + 时间戳)
```

```python
#!/usr/bin/env python3
"""简易 MCP stdio 调试代理"""
import sys, json, subprocess, threading

def forward(src, dst, name, log_file):
    for line in src:
        log_file.write(f"[{name}] {line}")
        log_file.flush()
        dst.write(line)
        dst.flush()

def main():
    cmd = sys.argv[1:]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
    log = open("mcp_debug.log", "w")
    
    t1 = threading.Thread(target=forward, args=(sys.stdin, proc.stdin, "CLIENT→SERVER", log))
    t2 = threading.Thread(target=forward, args=(proc.stdout, sys.stdout, "SERVER→CLIENT", log))
    t1.start(); t2.start(); t1.join(); t2.join()

if __name__ == "__main__":
    main()
```

用法:
```bash
# 在 Claude Desktop 配置中使用代理
# {"command": "python", "args": ["proxy.py", "python", "server.py"]}
tail -f mcp_debug.log  # 实时观察 JSON-RPC 消息
```

### 方案二: MCP Inspector (可视化调试)

```bash
# 浏览器中可视化调试
npx @modelcontextprotocol/inspector python server.py

# 连接已有的 HTTP 服务器
npx @modelcontextprotocol/inspector http://localhost:8000
```

Inspector 提供: 工具发现、交互式参数填写、原始 JSON-RPC 日志、资源和 Prompt 浏览器。

### 方案三: VS Code 调试

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug MCP Server",
      "type": "debugpy",
      "request": "launch",
      "module": "mcp",
      "args": ["run", "server.py"],
      "console": "integratedTerminal"
    }
  ]
}
```

**关键断点位置**: 工具注册 (`list_tools`)、工具发现 (`handle_list_tools`)、工具执行 (`handle_call_tool`)、具体处理器。

### 常见问题速查

| 症状 | 常见原因 | 调试方法 |
|------|---------|----------|
| Claude Desktop 中看不到工具 | 服务器启动崩溃、配置路径错误 | 查看 Claude Desktop 日志, 单独运行服务器 |
| 工具调用失败 | 参数校验、返回格式错误 | Inspector 测试, 在 handler 打断点 |
| 服务器不启动 | Python 环境、缺失依赖 | 检查 `python -c "import mcp"` |
| 超时 (-32001) | npm 包损坏、子进程崩溃 | stdio 代理抓包, 检查 stderr |
| AI 不调用你的工具 | 描述模糊、Schema 不匹配 | 行为测试, 用 Inspector 验证实际返回 |

---

## 生产部署

### 部署模式对比

| 模式 | 适用场景 | 复杂度 |
|------|---------|--------|
| stdio + Claude Desktop | 个人使用 | 低 |
| Docker + Streamable HTTP | 团队共享 | 中 |
| systemd 守护进程 | VPS/自建服务器 | 中 |
| FaaS (Cloud Run/Lambda) | 按需调用 | 高 |

### Docker 部署 (生产标准)

```dockerfile
FROM python:3.12-slim

RUN pip install mcp pydantic
COPY server.py /app/server.py
WORKDIR /app

# 非 root 用户
RUN useradd -m mcp && chown -R mcp:mcp /app
USER mcp

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "server.py", "--http"]
```

```bash
# 启动 (生产级安全限制)
docker run \
  --read-only \
  --tmpfs /tmp:size=64M \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --memory 256m --cpus 0.5 \
  --user 1000:1000 \
  -v /data:/data:ro \
  my-mcp-server
```

### systemd 守护进程

```ini
[Unit]
Description=MCP Server
After=network.target

[Service]
Type=simple
User=mcp
Restart=on-failure
RestartSec=5
StartLimitBurst=5
StartLimitIntervalSec=60
MemoryLimit=512M
ExecStart=/opt/mcp/venv/bin/python /opt/mcp/server.py --http

[Install]
WantedBy=multi-user.target
```

### 健康检查

```python
# HTTP 服务器添加 /health 端点
from aiohttp import web

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    # 检查关键依赖
    db_ok = await check_database()
    api_ok = await check_external_api()
    
    status = 200 if db_ok and api_ok else 503
    return web.json_response({
        "status": "healthy" if status == 200 else "degraded",
        "checks": {
            "database": "ok" if db_ok else "error",
            "external_api": "ok" if api_ok else "error",
        },
        "uptime": get_uptime(),
    }, status=status)
```

### 可观测性 (Observability)

**最小指标集** (每个 tool):
- 调用次数 (`mcp.tool.invocations`)
- 错误率 (`mcp.tool.errors`)
- 平均延迟 (`mcp.tool.duration.avg`)
- P95 延迟 (`mcp.tool.duration.p95`)

**最小事件集**:
- `server.startup`, `server.shutdown`
- `tool.invoked`, `tool.completed`
- `server.health`, `server.error`

```python
import time, logging

logger = logging.getLogger("mcp-server")

@mcp.tool()
async def instrumented_tool(param: str) -> str:
    start = time.time()
    try:
        result = await do_work(param)
        duration = time.time() - start
        logger.info("tool.completed", extra={
            "tool": "instrumented_tool",
            "duration_ms": duration * 1000,
            "status": "success",
        })
        return result
    except Exception as e:
        duration = time.time() - start
        logger.error("tool.error", extra={
            "tool": "instrumented_tool",
            "duration_ms": duration * 1000,
            "error_type": type(e).__name__,
        })
        raise
```

**关键规则**: stdout 只用于 JSON-RPC 协议消息，所有日志输出到 stderr。

### 断路器模式 (Circuit Breaker)

防止下游服务故障级联扩散:

```python
import asyncio
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed → open → half_open → closed

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half_open"
            else:
                return format_error(ErrorKind.UPSTREAM_ERROR, "服务暂时不可用, 请稍后重试")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.failure_count -= 1
                if self.failure_count <= 0:
                    self.state = "closed"
                    self.failure_count = 0
            return result
        except Exception:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise

breaker = CircuitBreaker()

@mcp.tool()
async def external_api_call(endpoint: str) -> str:
    return await breaker.call(call_external_api, endpoint)
```

---

## CI/CD 集成

```yaml
# .github/workflows/mcp-test.yml
name: MCP Server Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install mcp pytest pytest-asyncio
      - run: pytest tests/ -v
      
      # 协议验证
      - name: Validate MCP protocol
        run: |
          python server.py &
          sleep 2
          curl -X POST http://localhost:8000/mcp \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## 生产 Checklist

- [ ] stdout 只用于协议消息, 日志走 stderr
- [ ] 错误信息对 LLM 友好 (不含堆栈跟踪)
- [ ] 健康检查端点 (/health 或协议级 ping)
- [ ] Docker: read-only 文件系统 + 非 root 用户 + 资源限制
- [ ] 断路器包裹外部 API 调用
- [ ] 工具调用指标 (计数、延迟、错误率)
- [ ] 连接池管理 (数据库、HTTP 客户端)
- [ ] 请求超时 (所有外部操作 ≤ 30s)
- [ ] 优雅关闭 (SIGTERM/SIGINT 处理)
- [ ] 分页/截断防护大响应
