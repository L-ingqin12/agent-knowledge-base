# 10 — 高级设计模式

当你已经掌握了基本的 Tools/Resources/Prompts 开发后，这些模式将帮助你构建生产级的 MCP 服务器。

## 设计模式总览

| 模式 | 解决什么问题 | 适用阶段 |
|------|-------------|----------|
| 工作流导向设计 | 工具粒度过细、调用次数过多 | 设计阶段 |
| 渐进式工具合并 | 从原型到生产的接口演进 | 重构阶段 |
| 多步有状态工作流 | 复杂业务流程需要分步执行 | 复杂场景 |
| 响应驱动导航 | 让 AI 知道"下一步该调哪个工具" | 通用 |
| 语义工具路由 | 上下文窗口浪费在无关工具描述上 | 多工具场景 |
| 每请求无状态服务器 | 水平扩展、Serverless | 生产部署 |
| 结构化错误 | 错误信息对 LLM 可操作 | 通用 |
| Token 预算管理 | 避免浪费上下文窗口 | 生产优化 |

## 1. 工作流导向设计 (Workflow-Oriented)

这是 **Block (Square)** 工程团队管理 60+ 个 MCP 服务器总结出的核心原则。

**反模式:** 把每个 API 端点暴露为一个工具。

```
❌ get_user(id)          → 返回用户 JSON
❌ create_user(...)       → 创建用户
❌ upload_file(path)      → 上传文件
❌ set_permission(...)    → 设置权限
```

AI 需要调用 4 次才能完成"上传文件并分享给用户"。

**正确做法:** 从用户/Agent 需要完成的工作流出设计工具。

```
✅ upload_and_share(path, recipient_email)
   → 内部: create_user(if needed) → upload → set_permission → notify
   → 返回: 下载链接 + 权限状态
```

```python
# 好的设计: 一个工具完成一个完整工作流
@mcp.tool()
async def deploy_service(
    service_name: str,
    version: str,
    environment: str,
    replicas: int = 2,
) -> str:
    """部署服务到指定环境, 自动处理: 镜像构建、配置更新、滚动发布、健康检查"""
    # 内部编排多个操作
    image = await build_image(service_name, version)
    await update_k8s_config(service_name, image, environment, replicas)
    deploy_id = await rollout_deployment(service_name, environment)
    healthy = await wait_for_health(deploy_id, timeout=300)
    return f"部署完成, ID: {deploy_id}, 状态: {'健康' if healthy else '需检查'}"


# 坏的设计: 细粒度 CRUD 工具
@mcp.tool()
async def get_deployment(deploy_id: str) -> str: ...
@mcp.tool()
async def create_deployment(config: dict) -> str: ...
@mcp.tool()
async def update_replicas(deploy_id: str, count: int) -> str: ...
# AI 需要调用 3 次才能完成一个部署操作
```

## 2. 渐进式工具合并 (Progressive Consolidation)

Linear 团队将他们的 MCP 服务器从 30+ 个细粒度工具演进到 1 个 GraphQL 查询工具的过程:

```
v1: 30+ 细粒度工具 (每个 API 端点一个)
  get_issue, get_issue_labels, get_issue_comments, get_issue_history...

v2: 7 个分组工具 (按类别合并)
  get_issue_info(issue_id, category: "basic"|"labels"|"comments"|"history")

v3: 1 个执行查询工具
  execute_readonly_query(graphql: str)  → 一次调用替代 4-6 次
```

**演进策略**: 用 `category`/`include` 参数逐步合并同类工具，观察 AI 的使用情况，最终推向统一的查询接口。

## 3. 多步有状态工作流

某些业务天然是多步骤的，如入职流程、部署流水线。

```python
from typing import Optional

# 全局状态存储 (生产环境应使用 Redis/数据库)
_workflows: dict[str, dict] = {}

@mcp.tool()
async def start_onboarding(employee_name: str, department: str) -> str:
    """步骤1: 启动入职流程, 创建账号"""
    workflow_id = _make_id()[:8]
    _workflows[workflow_id] = {
        "step": 1,
        "name": employee_name,
        "department": department,
        "status": "accounts_created",
    }
    return (
        f"入职流程 {workflow_id} 已启动。\n"
        f"已完成: 创建账号 {employee_name}@{department}\n"
        f"下一步: 调用 complete_onboarding(workflow_id='{workflow_id}', "
        f"setup_dev_env=True, grant_repo_access=True)"
    )

@mcp.tool()
async def complete_onboarding(
    workflow_id: str,
    setup_dev_env: bool = True,
    grant_repo_access: bool = True,
) -> str:
    """步骤2: 完成入职流程, 配置开发环境和仓库权限"""
    wf = _workflows.get(workflow_id)
    if not wf:
        return f"错误: 未找到入职流程 {workflow_id}。请先调用 start_onboarding"
    # 执行配置
    wf["step"] = 2
    wf["status"] = "completed"
    return f"入职流程 {workflow_id} 已完成。开发环境: {'已配置' if setup_dev_env else '跳过'}, 仓库权限: {'已授予' if grant_repo_access else '跳过'}"
```

## 4. 响应驱动导航 (Response-Driven Navigation)

工具的返回值中明确提示"下一步可以做什么"，引导 AI 选择正确的后续操作。

```python
# ✅ 好: 提供导航线索
@mcp.tool()
async def search_issues(query: str) -> str:
    results = await issue_search(query)
    if not results:
        return "未找到匹配的 issue。建议: 1) 用更宽泛的关键词重试 2) 检查项目名称是否正确"
    
    lines = [f"找到 {len(results)} 个 issue:"]
    for r in results[:5]:
        lines.append(f"  [{r['id']}] {r['title']} ({r['status']})")
    lines.append(f"\n查看更多: 调用 list_issues 并指定更详细的条件")
    lines.append(f"查看详情: 调用 get_issue_detail(issue_id='{results[0]['id']}')")
    return "\n".join(lines)
```

## 5. 语义工具路由 (Semantic Tool Router)

当工具有几十个时，将所有 tool description 塞进上下文会浪费 token。按需暴露相关工具。

```python
# 简单实现: 工具分类 + 按需加载
TOOL_CATEGORIES = {
    "database": ["query_table", "list_schemas", "explain_query"],
    "deployment": ["deploy_service", "rollback", "get_deploy_status"],
    "monitoring": ["get_metrics", "get_alerts", "get_logs"],
}

@mcp.tool()
async def get_available_tools(category: str | None = None) -> str:
    """列出可用的工具类别和具体工具"""
    if category:
        tools = TOOL_CATEGORIES.get(category, [])
        return f"{category} 类别工具: {', '.join(tools)}"
    return "\n".join(f"{k}: {len(v)} 个工具" for k, v in TOOL_CATEGORIES.items())
```

## 6. 每请求无状态服务器 (Stateless Per-Request)

Sent 和 Langfuse 的生产实践: **每次请求创建新的 Server 实例**，在闭包中捕获上下文，请求结束后丢弃。

```python
from contextlib import asynccontextmanager

# 标准方式: lifespan 管理
@asynccontextmanager
async def lifespan(server: FastMCP):
    # 启动时初始化 (连接池等)
    pool = await create_db_pool(min_size=1, max_size=5)
    yield {"db_pool": pool}
    await pool.close()

mcp = FastMCP("stateless-server", lifespan=lifespan)

@mcp.tool()
async def query(ctx, sql: str) -> str:
    pool = ctx.lifespan_context["db_pool"]
    async with pool.acquire() as conn:
        return await conn.fetchval(sql)
```

**关键点**: 状态通过 lifespan 注入，请求间不共享可变状态。这可以轻松水平扩展和部署到 FaaS (Cloud Run, Lambda)。

## 7. 结构化错误处理

原始异常 **绝不能** 直接返回给 AI 模型——会导致信息泄露和不可预测行为。

```python
from enum import Enum

class ErrorKind(str, Enum):
    TOOL_UNAVAILABLE = "tool_unavailable"
    INVALID_INPUT = "invalid_input"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    PERMISSION_DENIED = "permission_denied"

def format_error(kind: ErrorKind, user_msg: str, retryable: bool = False) -> str:
    """返回 LLM 友好的错误信息"""
    return json.dumps({
        "error": {
            "kind": kind.value,
            "retryable": retryable,
            "user_message": user_msg,
        }
    }, ensure_ascii=False)

@mcp.tool()
async def query_database(sql: str, ctx) -> str:
    try:
        return await execute_sql(sql)
    except ConnectionError:
        return format_error(
            ErrorKind.UPSTREAM_ERROR,
            "数据库暂时不可用，请稍后重试。如果问题持续，请检查数据库状态。",
            retryable=True,
        )
    except ValueError as e:
        return format_error(
            ErrorKind.INVALID_INPUT,
            f"SQL 查询无效: {e}。请检查语法后重试。",
        )
```

## 8. Token 预算管理

AI 模型的上下文窗口是有限资源，每次工具返回都会消耗 token。

```python
# ✅ 好: 保护 Token 预算
@mcp.tool()
async def search_logs(
    query: str,
    detail_level: str = "concise",  # concise | normal | detailed
    max_results: int = 10,
) -> str:
    """搜索日志 (用 detail_level 控制返回详细程度以节省 token)"""
    results = await log_search(query, limit=max_results)
    
    if detail_level == "concise":
        # 只返回时间 + 摘要
        return "\n".join(f"{r['time']} [{r['level']}] {r['summary'][:100]}" for r in results)
    elif detail_level == "detailed":
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    # normal: 中等详细程度
    return "\n".join(f"{r['time']} [{r['level']}] {r['message'][:200]}" for r in results)

# ❌ 坏: 不做截断
@mcp.tool()
async def search_logs_bad(query: str) -> str:
    results = await log_search(query, limit=9999)
    return json.dumps(results)  # 可能返回几 MB 数据
```

**Token 预算最佳实践**:
- 默认截断大型响应 (如只返回前 20 条)
- 提供 `detail_level` 参数让 AI 选择响应深度
- 使用 Markdown 而非纯 JSON (LLM 处理 Markdown 更高效)
- 分页: `limit` + `offset` 或 `cursor` 模式
- 避免在 tool description 中注入动态时间戳 (破坏 prompt caching)

## 9. Tool Annotations (工具注解)

从 MCP 2025-03-26 开始支持，帮助客户端理解工具特征:

```python
@mcp.tool(
    annotations={
        "readOnlyHint": True,       # 只读操作
        "destructiveHint": False,   # 非破坏性
        "idempotentHint": True,     # 幂等 (重复调用结果相同)
        "openWorldHint": True,      # 与外部系统交互
    }
)
async def get_weather(city: str) -> str:
    """获取天气 — 只读、幂等、外部数据"""
    ...

@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": True,    # 破坏性操作 (会修改数据)
        "idempotentHint": False,
    }
)
async def delete_user(user_id: str) -> str:
    """删除用户 — 写入、破坏性、不可逆"""
    ...
```

这些注解帮助 Claude Desktop、Cursor 等客户端在 UI 中做安全提示和操作确认。

## 10. 工具权限设计原则

**一条工具一个风险等级**: 不要在一个工具里混用读和写。

```python
# ✅ 好: 读写分离
@mcp.tool()
async def search_documents(query: str) -> str:
    """搜索文档 (只读)"""
    ...

@mcp.tool()
async def update_document(doc_id: str, content: str) -> str:
    """修改文档 (需要确认)"""
    ...

# ❌ 坏: 读写混在一起
@mcp.tool()
async def manage_document(action: str, doc_id: str, content: str = "") -> str:
    """action='read' 或 'write' — 用户无法区分风险"""
    ...
```

## 11. 渐进式信息暴露 (Progressive Discovery)

大型 Schema 不要一次性暴露，按需加载:

```python
@mcp.tool()
async def list_tables() -> str:
    """列出所有数据表"""
    return "\n".join(await get_table_names())

@mcp.tool()
async def describe_table(table_name: str) -> str:
    """获取指定表的结构 (列名、类型、索引)"""
    return json.dumps(await get_table_schema(table_name), ensure_ascii=False, indent=2)

@mcp.tool()
async def query_table(table_name: str, columns: list[str], where: str = "") -> str:
    """查询表数据"""
    return await execute_select(table_name, columns, where)

# AI 会按自然顺序: list → describe → query
```

## 架构决策: 何时用哪种模式

```
你的工具有多少?
├── 5 个以下 → 直接暴露, 不需要特殊模式
├── 5-20 个 → 加 category 参数做分组
├── 20-50 个 → 工作流导向设计 + 语义路由
└── 50+ 个 → 渐进合并 + 统一的查询接口 (GraphQL/SQL)

你的调用频率?
├── 每天百次 → stdio 模式, 状态无所谓
├── 每天万次 → Streamable HTTP, 连接池
└── 每天百万次 → 无状态 + FaaS + 缓存
```
