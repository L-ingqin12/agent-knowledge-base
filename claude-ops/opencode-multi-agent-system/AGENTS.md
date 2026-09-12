# OpenCode 多智能体协作系统

## 架构概览

```
                          ┌─────────────────────────────────┐
                          │          👤 用户请求            │
                          └──────────────┬──────────────────┘
                                         │
                          ┌──────────────▼──────────────────┐
                          │     🧠 Orchestrator (主智能体)   │
                          │   ┌─────────────────────────┐   │
                          │   │  1. 意图分析             │   │
                          │   │  2. 任务分解             │   │
                          │   │  3. 子智能体匹配          │   │
                          │   │  4. 并行/串行调度         │   │
                          │   │  5. 结果验证整合          │   │
                          │   └───────────┬─────────────┘   │
                          └───────────────┼─────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
          ┌─────────▼──────┐  ┌──────────▼──────┐  ┌──────────▼──────┐
          │ 🔍 Code        │  │ 🧪 Test         │  │ 📝 Doc          │
          │   Reviewer     │  │   Writer        │  │   Writer        │
          │ (只读审查)      │  │ (测试生成)      │  │ (文档生成)      │
          └────────────────┘  └─────────────────┘  └─────────────────┘
                    │                     │                     │
          ┌─────────▼──────┐  ┌──────────▼──────┐  ┌──────────▼──────┐
          │ 🛡️ Security   │  │ ♻️  Refactor     │  │ 🐛 Debugger     │
          │   Auditor     │  │   Specialist    │  │ (排错修复)      │
          │ (安全审计)     │  │ (代码重构)      │  │                 │
          └────────────────┘  └─────────────────┘  └─────────────────┘
```

## 快速开始

### 1. 安装 OpenCode

```bash
# macOS / Linux
curl -fsSL https://opencode.ai/install | bash

# 验证安装
opencode --version
```

### 2. 配置本项目

```bash
# 克隆本项目
git clone https://github.com/L-ingqin12/opencode-multi-agent-system.git
cd opencode-multi-agent-system

# 将 agent 配置复制到你的项目中
cp -r .opencode /path/to/your-project/
```

### 3. 启动

```bash
cd /path/to/your-project
opencode
# 在 OpenCode 会话中:
# 输入 @orchestrator 切换到主智能体（或设为默认）
# 然后正常描述任务，主智能体会自动调度子智能体
```

## 核心概念

### 三层架构

| 层级 | 角色 | 职责 |
|------|------|------|
| **主智能体 (Orchestrator)** | 总指挥 | 分析意图 → 分解任务 → 调度子智能体 → 验证结果 → 整合输出 |
| **子智能体 (Subagents)** | 专家 | 在自己的专业领域内独立完成任务，返回结构化结果 |
| **工具层 (Tools)** | 能力 | 文件读写、代码搜索、命令执行等原子操作 |

### 子智能体调用机制

主智能体通过 OpenCode 的 `Task` 工具委托子智能体：

```yaml
# 在 agent 定义中使用 task 工具
tools:
  task: true  # 开启子智能体调用能力
```

```python
# 伪代码：主智能体调用子智能体的实际格式
Task(
  subagent_type="code-reviewer",  # 目标子智能体名称
  description="审查 auth 模块",    # 简短描述（用于日志）
  prompt="具体的任务 prompt..."     # 完整任务说明
)
```

### 自规划算法

主智能体收到用户请求后按以下逻辑决策：

```
用户请求
  │
  ▼
意图分析 ─── 提取关键词和任务类型
  │
  ▼
简单任务？─── 是 ──→ 自己完成（不委托）
  │ 否
  ▼
单一专业？─── 是 ──→ 委托对应子智能体
  │ 否（复合任务）
  ▼
分解子任务 ─── 判断依赖关系
  │
  ├── 无依赖 ──→ 并行委托多个子智能体
  └── 有依赖 ──→ 串行委托（等前一个完成再下一个）
```

## 子智能体一览

| 子智能体 | 命令 | 权限 | 用途 |
|---------|------|------|------|
| **Code Reviewer** | `@code-reviewer` | 只读 | 审查代码：正确性/安全性/性能/可维护性/可测试性 |
| **Test Writer** | `@test-writer` | 读写 | 生成单元测试/集成测试/E2E，自动检测测试框架 |
| **Doc Writer** | `@doc-writer` | 读写 | README/API文档/架构文档/变更日志 |
| **Security Auditor** | `@security-auditor` | 只读 | OWASP Top 10 / CWE 漏洞扫描 / 安全加固方案 |
| **Refactor Specialist** | `@refactor-specialist` | 读写 | 消除代码味道/技术债务，不改变外部行为 |
| **Debugger** | `@debugger` | 读写 | Bug根因定位 → 最小修复 → 回归测试建议 |

## 工作流示例

### 示例 1: 代码审查 + 测试

```
用户: "审查 src/auth.js 并补充测试"

主控思考:
  意图: [review, test]
  依赖: 建议先审查再测试（测试可针对风险点优化）
  策略: 串行执行

Step 1: Task(code-reviewer, "审查 src/auth.js")
  → 返回: 3 个严重问题 + 5 个改进建议

Step 2: 主控提取风险点，构造测试委托:
  Task(test-writer, "为 src/auth.js 写测试，重点覆盖:
    1. Token 过期处理 (CRIT-01)
    2. 空密码验证绕过 (CRIT-02)
    3. SQL 注入点 (CRIT-03)")

  → 返回: auth.test.js 包含 15 个测试用例

Step 3: 主控验证整合 → 向用户汇报
```

### 示例 2: 上线前全面检查

```
用户: "准备上线，做全面检查"

主控思考:
  意图: [review, security, docs] — 三个独立任务
  策略: 并行执行

并行委托:
  Task(code-reviewer, "审查 src/ 全部代码质量，重点查错误处理")
  Task(security-auditor, "安全审计 src/，扫描 OWASP Top 10")
  Task(doc-writer, "检查并更新 README，确认 API 文档是最新的")

  → 三个子智能体同时工作
  → 主控收集全部结果 → 生成上线检查清单
```

### 示例 3: Bug 修复 + 重构

```
用户: "用户登录后 5 分钟必定超时，修好后把这个模块重构一下"

主控思考:
  意图: [debug → refactor] — 有依赖关系
  策略: 串行（修复确认后再重构）

Step 1: Task(debugger, "## 任务
    排查登录 5 分钟超时的根因
    ## 范围
    - src/auth.js
    - src/middleware/session.js
    ...")

  → debugger 定位: session.js:42 处 JWT expiresIn 误设为 '5m' 应为 '24h'

Step 2: 主控确认修复无误后:
  Task(refactor-specialist, "## 任务
    重构 src/auth.js 和 src/middleware/session.js
    ## 约束
    - 保留刚才的 JWT 过期时间修复
    - 提取重复的 token 处理逻辑
    ...")
```

## 目录结构

```
your-project/
├── .opencode/
│   └── agent/
│       ├── orchestrator.md        # 主智能体
│       ├── code-reviewer.md       # 代码审查子智能体
│       ├── test-writer.md         # 测试编写子智能体
│       ├── doc-writer.md          # 文档编写子智能体
│       ├── security-auditor.md    # 安全审计子智能体
│       ├── refactor-specialist.md # 代码重构子智能体
│       └── debugger.md            # 调试排错子智能体
├── AGENTS.md                      # 本文件（可软链到项目根目录）
└── ...
```

## 自定义子智能体

创建新的子智能体只需 3 步：

1. 在 `.opencode/agent/` 下创建 `.md` 文件
2. 设置 frontmatter（name, mode, tools）
3. 编写系统指令

```markdown
---
name: my-agent
mode: subagent
description: 我的自定义智能体
tools:
  read: true
  bash: true
---

# My Agent

你是...（具体的系统指令）
```

## 最佳实践

### ✅ DO
- 主智能体对每个子智能体返回做验证
- 并行执行独立的子任务
- 委托 prompt 只给最小必要上下文
- 安全审计在每次上线前运行
- 关键模块的代码变更后运行审查 + 测试

### ❌ DON'T
- 不要对简单操作（读文件、搜索）使用子智能体
- 不要让有写权限的子智能体并行操作同一文件
- 不要在委托 prompt 中泄漏敏感信息
- 不要跳过子智能体返回结果的验证
- 不要让子智能体直接调用子智能体（除非显式开启 task: true）

## 相关资源

- [OpenCode 官方仓库](https://github.com/anomalyco/opencode)
- [rothnic/opencode-agents](https://github.com/rothnic/opencode-agents) — 多智能体框架参考
- [OpenCode Subagents Issue #1293](https://github.com/anomalyco/opencode/issues/1293)
