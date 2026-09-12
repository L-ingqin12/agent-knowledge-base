---
title: OpenCode 多智能体协作系统 — 架构设计文档
aliases: [多智能体架构设计, OpenCode 智能体模型, 自规划算法设计]
tags: [ai/agent, ai/ops]
created: 2026-09-12
updated: 2026-09-12
status: review
---

# OpenCode 多智能体协作系统 — 架构设计文档

## 设计目标

构建一个可以在 OpenCode 中直接使用的多智能体协作系统，核心目标是：

1. **可用** — 复制 `.opencode/agent/` 到任何项目即可工作
2. **可理解** — 每个智能体的职责边界清晰，调用逻辑透明
3. **可扩展** — 用户只需创建新的 `.md` 文件就能添加自定义智能体

## 架构设计过程

### 阶段 1: 理解 OpenCode 智能体模型

OpenCode 的智能体系统采用**两层架构**：

```
Primary Agent (主智能体)
  └── mode: primary
  └── 出现在 Tab 切换中
  └── 不能被 @mention 或委托
  └── tool: task (开启后可调用子智能体)

Subagent (子智能体)
  └── mode: subagent
  └── 不在 Tab 中出现
  └── 通过 @agent-name 或主智能体调用
  └── 每次调用创建隔离的会话
```

**关键设计约束**：
- `mode: primary` 的智能体**不能被其他智能体调用**（只能在 Tab 中切换使用）
- `mode: subagent` 的智能体**不显示在 Tab 中**（只能被调用）
- `mode: all` 两者皆可（默认值）
- 子智能体的 `task` 工具默认关闭，防止递归嵌套

### 阶段 2: 确定智能体分工

按软件工程生命周期划分专业领域：

```
开发流程: 规划 → 实现 → 审查 → 测试 → 文档 → 上线
                                ↑       ↑       ↑
                        安全审计贯穿全流程
```

覆盖的关键环节：
1. **代码审查** (code-reviewer) — 质量门禁
2. **测试** (test-writer) — 质量保障
3. **文档** (doc-writer) — 知识沉淀
4. **安全审计** (security-auditor) — 风险控制
5. **重构** (refactor-specialist) — 技术债务管理
6. **调试** (debugger) — 问题解决

### 阶段 3: 设计调用机制

**子智能体调用格式** (基于 OpenCode 官方文档):

```
{子智能体名称}, {任务描述}
```

主智能体在其响应中直接写出子智能体名称和任务，OpenCode 运行时识别子智能体名称并自动创建隔离会话。

**为什么不使用显式 Task 工具？**
- OpenCode 的 Task 工具是插件体系的
- 原生机制是通过命名识别: primary agent 输出子智能体名称时系统自动路由
- 这种设计更自然，类似"对话中的委托"

### 阶段 4: 设计自规划算法

主智能体需要一个**内化的决策算法**来决定何时调用哪个子智能体。

核心思路：**关键词意图匹配 + 依赖分析**

```
用户请求 → 提取意图 → 匹配子智能体 → 依赖判断 → 并行/串行执行
```

```
意图识别规则:
  review/审查/检查    → code-reviewer
  test/测试/spec     → test-writer
  doc/文档/readme    → doc-writer
  security/安全/vuln → security-auditor
  refactor/重构      → refactor-specialist
  debug/bug/报错     → debugger
  无匹配             → 自己处理
```

```
依赖判断规则:
  操作不同文件 → 可并行
  操作同一文件 + 只读 → 可并行
  操作同一文件 + 有写 → 串行
  B 需要 A 的输出 → 串行
```

### 阶段 5: 设计 Fan-Out 模式

Fan-Out 是并行执行的扩展：主智能体一次性将任务分解为 N 个子任务并分发。

**当前实现**: Orchestrator 通过多次调用子智能体实现模拟 Fan-Out。

**增强路径**:
1. 安装 `opencode-agent-intercom` 插件 → 非阻塞 `spawn()`
2. 使用 `swarm-control` → 文件级自动分解
3. 等待 Ephemeral Team API (官方提案) → 原生 `team()` 工具

### 阶段 6: 权限模型设计

| 智能体 | read | grep | glob | bash | write | edit | task |
|-------|:----:|:----:|:----:|:----:|:-----:|:----:|:----:|
| orchestrator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| code-reviewer | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| test-writer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| doc-writer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| security-auditor | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| refactor-specialist | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| debugger | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

**权限设计原则**:
- 分析/审查类只读（防止幻觉导致破坏性修改）
- 生成/修复类有写权限（受限范围）
- task 工具仅 orchestrator 开启（防止递归嵌套）

## 关键设计决策

### 决策 1: 为什么 Orchestrator 用 `mode: primary` 而非 `mode: all`

- `primary`: 作为入口智能体，用户明确切换使用
- 如果设为 `all`，其他智能体可能反过来调用它 → 循环调用风险
- `primary` 更清晰地表达了"唯一入口"的定位

### 决策 2: 为什么代码审查和安全审计是只读的

- 审查类智能体的价值在于**发现问题**，而非修复
- 修复应该由 debugger 或 refactor-specialist 执行（有明确的任务范围）
- 读写分离降低风险：幻觉不会导致代码被直接修改

### 决策 3: 为什么不给子智能体 `task: true`

- OpenCode 社区的已知风险：`task: true` 会导致无界递归自调用
- 真实案例: 612 层嵌套、73 分钟、API 额度耗尽
- 所有跨智能体协调统一通过 Orchestrator

### 决策 4: Fan-Out 上限设为 5

- 平衡并行效率与系统负载
- 每个子智能体都有独立的 LLM 会话（消耗 API 额度）
- 5 个并行已经覆盖绝大多数场景（审查+安全+文档+测试+重构）

## 系统局限与改进方向

### 当前局限
1. **无原生并行** — 需要安装 intercom 插件实现真正的非阻塞 Fan-Out
2. **无跨智能体通信** — 子智能体不能直接对话，必须通过 Orchestrator
3. **无状态持久化** — 子智能体会话隔离，无法共享上下文
4. **无自动回退** — 子智能体失败不会自动重试

### 改进路线图
1. **短期**: 集成 opencode-agent-intercom 实现非阻塞 Fan-Out
2. **中期**: 增加失败重试 + 超时处理
3. **长期**: 等待原生 Ephemeral Team API，用 DAG 管理复杂工作流

## 文件结构说明

```
.opencode/agent/
├── orchestrator.md        # 入口: mode=primary, 唯一有 task 权限
├── code-reviewer.md       # 只读: 审查代码
├── test-writer.md         # 读写: 生成测试
├── doc-writer.md          # 读写: 生成文档
├── security-auditor.md    # 只读: 安全审计
├── refactor-specialist.md # 读写: 代码重构
└── debugger.md            # 读写: 调试排错
```

每个 `.md` 文件包含:
- YAML frontmatter: `description`, `mode`, `tools`
- Markdown body: 系统指令（System Prompt）

> 🔗 相关文档：[[opencode-multi-agent-architecture]] · [[fan-out-subagent-pattern]] · [[parallel-execution]] · [[chain-workflow]]
