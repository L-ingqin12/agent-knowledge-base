# 12 — 真实案例研究

分析社区和生产环境中经过验证的 MCP 服务器设计。

## 案例一: Sentry MCP Server (大规模生产)

**规模**: 60M 请求/月, 5000+ 组织, 3 人团队维护, 10-15 个工具

### 架构决策

```
                    stdio            Streamable HTTP          SSE
                 (Claude Code)      (远程/Web)           (兼容)
                      ↓                  ↓                   ↓
              ┌───────────────────────────────────────────────┐
              │              Sentry MCP Server                │
              │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
              │  │ Issue    │ │ Alert    │ │ Performance  │  │
              │  │ Tools    │ │ Tools    │ │ Tools        │  │
              │  └──────────┘ └──────────┘ └──────────────┘  │
              │          Sentry API Client (共享层)           │
              └───────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 原因 |
|------|------|
| 同时支持 3 种传输 | 不同客户端支持不同传输, 不选边 |
| 结构化错误 (45k/月错误) | 原始 traceback 绝不能返回给 AI |
| Tool description 存配置文件 | 独立维护, 不在代码里硬编码 |
| AI 过滤大响应 | 嵌入 AI agent 在工具内做智能摘要 |
| 零可观测性起步的教训 | 最初从 Twitter 得知宕机 — 现在全量监控 |

### 工具描述设计

```
✅ 好:
  "Get issues assigned to you. Returns title, status, priority.
   Use get_issue_detail(issue_id) to see full description and comments."

❌ 差:
  "Get issues"  ← 描述太模糊, AI 不知道该何时调用
  "Returns the full JSON representation of all issues..." ← 返回太大
```

### 设计启示

1. **MCP 服务器变成了替代 UI** — 用户不再访问 web 界面, 直接在 AI 中工作
2. **Prompt 工程是基础设施** — tool description 是产品界面, 需要精心维护
3. **观测性从第一天就要有** — 等宕机了再加为时已晚

---

## 案例二: Filesystem MCP Server (官方)

源码: `modelcontextprotocol/servers/src/filesystem`

### 架构

```
Claude Desktop ←→ stdio ←→ Filesystem MCP Server
                               ├── 安全路径限制
                               ├── 文件操作 (读/写/编辑)
                               ├── 目录操作 (列表/创建)
                               └── 文件搜索
```

### 安全设计

```typescript
// 核心安全模式: 所有路径操作前校验
function validatePath(requestedPath: string, allowedDirs: string[]): string {
  const resolved = path.resolve(requestedPath);
  const isAllowed = allowedDirs.some(dir => resolved.startsWith(dir));
  if (!isAllowed) {
    throw new Error(`Access denied: ${requestedPath} is outside allowed directories`);
  }
  return resolved;
}
```

### 设计启示

1. **路径校验是核心** — 每个文件操作前都要验证, 不是一次性的
2. **最小化 API surface** — 官方版 6 个工具, BetterMCPFileServer 从 11 减到 6
3. **权限在配置时决定** — 不在运行时让 AI 选择能访问的目录

---

## 案例三: PostgreSQL MCP Server

源码: `modelcontextprotocol/servers/src/postgres`

### Scheme 发现模式

```
list_tables()           → 所有表名
describe_table("users") → 列名、类型、索引
query("SELECT ...")     → 实际查询
```

支持 AI 按自然顺序发现和使用: 查有哪些表 → 看表结构 → 写查询。

### 关键安全措施

- 默认只读, 写权限在配置中显式开启
- 拒绝 DDL 语句 (CREATE/DROP/ALTER) 除非显式允许
- 查询结果限制行数

---

## 案例四: GitHub MCP Server

最高使用量的 MCP 服务器之一。

### 工作流导向工具设计

```
不是: get_issue + get_comments + get_labels (3 次调用)
而是: get_issue_with_context(issue_number) → 一次返回 issue + 前 10 条评论 + labels
```

### 工具示例

```
create_pr(title, body, base, head)      → 一步创建 PR
search_code(query, repo)                → 跨仓库搜索
review_pr(pr_number)                    → 获取 review 上下文
manage_issue(action, number, ...)       → issue 的 CRUD
```

---

## 案例五: Linear MCP Server (渐进式演进)

Linear 团队的 MCP 服务器经历了三个版本的演进。

### v1: 1:1 映射 API (30+ 工具)

```python
get_issue(issue_id)
get_issue_labels(issue_id)
get_issue_comments(issue_id)
get_issue_history(issue_id)
get_issue_attachments(issue_id)
# ... 30+ 个工具
```

**问题**: AI 不知道需要调用哪些工具才能获取完整信息，经常漏掉 `get_issue_labels`。

### v2: 分组合并 (7 个工具)

```python
get_issue_info(issue_id, category="basic"|"labels"|"comments"|"history"|"attachments")
```

**效果**: AI 调用 `category="basic"` 获取摘要，需要详情时再指定 category。

### v3: 统一查询接口 (1 个工具)

```python
execute_readonly_query(graphql: str)
```

**效果**: 一次 GraphQL 调用替代 4-6 次 API 调用。AI 可以精确构造查询获取所需数据。

### 选型建议

```
如果 API 很复杂 → v1 (细粒度) 配合 v2 (分组) 作为过渡
如果数据模型灵活 → v3 (统一查询) 是最佳终点
不建议从 v1 直接跳到 v3, 中间需要观察 AI 的使用模式
```

---

## 案例六: 常见 MCP 服务器架构模式对比

### 模式 A: 薄封装 (Thin Wrapper)

```
MCP Server → 直接转发 → 下游 API
```

**适用**: 简单的 CRUD 操作、只读查询
**例子**: Weather MCP, Search MCP
**代码量**: 50-200 行

### 模式 B: 工作流编排 (Workflow Orchestrator)

```
MCP Server → 多步骤编排 → 下游 API 1
                        → 下游 API 2
                        → 条件分支
```

**适用**: 业务流程、多系统协调
**例子**: Deploy MCP, Onboarding MCP
**代码量**: 200-1000 行

### 模式 C: AI 增强 (AI-Augmented)

```
MCP Server → 调用 AI 模型 → 处理结果 → 返回
```

**适用**: 需要 NLP/摘要/分类的场景
**例子**: Sentry (AI 过滤大响应), Code Review MCP
**代码量**: 300-800 行

### 模式 D: 代理网关 (Proxy Gateway)

```
AI Client → Gateway → MCP Server A
                   → MCP Server B
                   → 鉴权/限流/路由
```

**适用**: 企业多服务器治理
**例子**: IBM ContextForge, 内部 MCP 平台
**代码量**: 1000+ 行

---

## 社区热门 MCP 服务器参考

### 开发者必备

| 服务器 | 用途 | 关键设计点 |
|--------|------|-----------|
| GitHub | 代码管理、PR、Issue | 工作流导向, 一次调用完成多步操作 |
| Filesystem | 文件操作 | 安全路径限制, 最小化 API surface |
| PostgreSQL | 数据库查询 | 渐进式 schema 发现, 默认只读 |
| Docker | 容器管理 | 危险操作需要确认 |
| Git | 版本控制 | 封装 git 命令, 防止误操作 |
| Jira | 项目管理 | issue 搜索 + 创建 + 更新 |

### 生产运维

| 服务器 | 用途 | 关键设计点 |
|--------|------|-----------|
| Sentry | 错误监控 | 结构化错误, AI 过滤, 3 传输并行 |
| AWS | 云资源管理 | 权限最小化, 只读优先 |
| Kubernetes | 容器编排 | 操作确认, 命名空间隔离 |
| Datadog | 可观测性 | 时间范围限制, 聚合查询 |
| PagerDuty | 告警管理 | 工作流导向: 确认 → 分配 → 解决 |
| Slack | 团队沟通 | 消息发送 + 频道管理 + 搜索 |

### 知识管理

| 服务器 | 用途 | 关键设计点 |
|--------|------|-----------|
| Notion | 知识库 | 页面 CRUD + 搜索 + 数据库 |
| Obsidian | 笔记 | 本地文件操作, 双向链接 |
| Google Drive | 文档管理 | OAuth, 文件搜索 + 读取 |
| Confluence | 企业 Wiki | 空间 + 页面 + 搜索 |

---

## 设计启示录: 从案例中提炼的 7 条原则

1. **工具描述是产品界面** — 不是你写给自己看的注释，是 AI 决定是否调用工具的依据

2. **从工作流反推工具设计** — 不要映射 API 端点, 映射用户需要完成的任务

3. **安全是贯穿设计的主线** — 路径校验、权限限制、读写分离, 不是附加功能

4. **可观测性不是可选项** — 没有指标和日志的 MCP 服务器是盲飞

5. **演进路径: 细粒度 → 分组 → 统一接口** — 不要跳过中间阶段, 每次演进需要实际使用数据支撑

6. **错误信息要可操作** — "数据库连接失败, 请稍后重试" >> "ConnectionError: (1040, 'Too many connections')"

7. **MCP 服务器是产品, 不是工具** — Sentry 的用户不再访问 web 界面, 你的 MCP 服务可能就是用户唯一的交互方式
