---
title: Agent Learn — AI Agent 开发学习项目
aliases: [agent-learn 学习项目, Agent 开发学习项目, AI Agent 实战教程]
tags: [ai, ai/learning]
created: 2026-09-12
updated: 2026-09-13
status: stable
---

# Agent Learn — AI Agent 开发学习项目

从零学习 AI Agent 开发，包含知识文档、Python 代码库和可运行示例。

## 项目结构

```
agent-learn/
├── agent_learn/                  # 核心 Python 包 (13 个模块 + adapters 包)
│   ├── __init__.py               # 统一导出接口
│   ├── base.py                   # Agent 基类 + 工具定义 (ToolDef/ToolResult)
│   ├── tools.py                  # 内置工具集 (搜索、计算、文件、代码执行)
│   ├── memory.py                 # 记忆系统 (ShortTermMemory + LongTermMemory)
│   ├── simple_agent.py           # 基础 Tool-Use Agent
│   ├── react_agent.py            # ReAct Agent (推理-行动-观察 循环)
│   ├── memory_agent.py           # 带记忆的 Agent
│   ├── multi_agent.py            # 多 Agent 协作系统 (Sequential + Hierarchical)
│   ├── advanced_agent.py         # OMO 风格三层 Agent (路由→规划→子Agent)
│   ├── cache_first.py            # Reasonix 启发缓存优先循环 + 工具修复管线
│   ├── analysis_agent.py         # 定制化问题分析 Agent (O-H-V-C 协议)
│   ├── provider_agent.py         # Provider 无关 Agent (不 import 任何 SDK)
│   ├── reflexion_agent.py        # 元认知自反思 Agent (Generate→Critique→Refine)
│   └── adapters/                 # 多模型适配层 (base.py / anthropic.py / openai.py)
├── examples/                     # 可运行的示例 (11 个)
│   ├── 01_weather_agent.py       # 天气查询 Agent
│   ├── 02_react_agent.py         # ReAct 循环演示
│   ├── 03_agent_with_memory.py   # 记忆系统演示
│   ├── 04_multi_agent_collab.py  # 多 Agent 协作演示
│   ├── 05_code_assistant.py      # 代码助手综合 Demo
│   ├── 06_omo_style_agent.py     # OMO 风格三层编排演示
│   ├── 07_cache_first_agent.py   # 缓存优先循环 + 修复管线演示
│   ├── 08_custom_analysis_agent.py  # 定制化问题分析 Agent 演示
│   ├── 09_memory_swap.py         # 虚拟内存换入换出演示
│   ├── 10_multi_model_agent.py   # 多模型适配层演示 (含 OpenAI 分支)
│   └── 11_reflexion_agent.py     # 元认知自反思演示
├── docs/                         # 学习文档 (14 章)
│   ├── 01-agent-overview.md
│   ├── 02-core-components.md
│   ├── 03-learning-roadmap.md
│   ├── 04-frameworks-deep-dive.md
│   ├── 05-practice-exercises.md
│   ├── 06-oh-my-opencode-analysis.md
│   ├── 07-reasonix-architecture-analysis.md
│   ├── 08-custom-problem-agent.md
│   ├── 09-production-agent-patterns.md
│   ├── 10-advanced-agent-patterns.md
│   ├── 11-agent-best-practices-cheatsheet.md
│   ├── 12-agentic-rag-and-protocols.md
│   ├── 13-metacognition-and-evaluation.md
│   └── 14-awesome-agent-ecosystem.md
├── requirements.txt
├── pyproject.toml
├── MODULE_README.md
└── .gitignore
```

## 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/L-ingqin12/agent-learn.git
cd agent-learn

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置 API Key
export ANTHROPIC_API_KEY="your-api-key"

# 4. 运行第一个示例
python examples/01_weather_agent.py
```

> [!note] 快速开始的两个补充（2026-09-13）
> - **示例 10 需额外装 `openai`**：`requirements.txt`（anthropic + python-dotenv）与 `pyproject.toml` 都没有 openai，而 `agent_learn/adapters/__init__.py` 第 15 行无条件 `from agent_learn.adapters.openai import OpenAIAdapter`、`adapters/openai.py` 在 `OpenAIAdapter.__init__` 内才 `from openai import OpenAI`——照上面装完依赖再构造 `OpenAIAdapter`（或跑 `examples/10_multi_model_agent.py`）会 `ModuleNotFoundError`。跑之前先 `pip install openai`。
> - **安装自检与失败判据**（原文未写）：`python -c "import anthropic, dotenv"` 自检依赖；`pip show agent-learn` 看版本；失败判据为「未设 `ANTHROPIC_API_KEY` → 缺凭据报错 / key 无效 → 401 / 缺依赖 → `ModuleNotFoundError`」，示例**应打印工具调用轨迹与最终答案**，否则视为未跑通。
> 来源：<https://cdn.jsdelivr.net/gh/L-ingqin12/agent-learn@main/requirements.txt> · <https://raw.githubusercontent.com/L-ingqin12/agent-learn/main/agent_learn/adapters/openai.py>

## 模块拆解

### 基础层 (`base.py`)

| 类 | 职责 |
|---|------|
| `ToolDef` | 工具定义：名称、描述、输入 schema |
| `ToolResult` | 工具执行结果：tool_use_id、内容 |
| `BaseAgent` | Agent 抽象基类：管理客户端、工具注册表、统一 `run()` 接口 |

### 工具层 (`tools.py`)

| 工具 | 功能 |
|------|------|
| `web_search` | 模拟网络搜索 |
| `calculator` | 安全数学表达式计算 |
| `read_file` / `write_file` | 文件读写 |
| `run_python_code` | 在子进程中执行 Python 代码 |
| `json_parser` | JSON 解析与字段提取 |

### 记忆层 (`memory.py`)

| 类 | 策略 |
|---|------|
| `ShortTermMemory` | 消息缓存 → 超限时压缩旧消息为摘要 |
| `LongTermMemory` | JSON 持久化 → LRU 淘汰 → 按 key 检索 |

### Agent 实现层

| 模块 | 类 | 核心循环 | 适用场景 |
|------|---|---------|---------|
| `simple_agent` | `SimpleAgent` | 调用 LLM → 执行工具 → 回传结果，直到无工具调用 | 最基础的工具调用 |
| `react_agent` | `ReActAgent` | Thought → Action → Observation 强制循环 | 需要可解释推理链 |
| `memory_agent` | `MemoryAgent` | 检索记忆 → 增强上下文 → 执行 → 提取新记忆 | 个性化长期服务 |
| `multi_agent` | `MultiAgentSystem` | Manager 分解 → Workers 执行 → Manager 汇总 | 复杂任务分解协作 |
| `advanced_agent` | `AdvancedOrchestrator` | SemanticRouter → Planner → SubAgent 分类执行 | OMO 风格三层编排 |
| `cache_first` | `CacheFirstAgent` | ImmutablePrefix + AppendOnlyLog + VolatileScratch | 缓存稳定的高效 Agent |

> 上表只列 v0.1–v0.3 的六个核心模块；v0.4 起的 `analysis_agent`（`ProblemAnalysisAgent`，O-H-V-C 协议）、v0.5 的 `provider_agent` + `adapters/` 包、v0.7 的 `reflexion_agent`（可插拔 `CriticRegistry`）见「更新记录」。

## 架构设计

```
┌──────────────────────────────────────────────────────────┐
│                     Examples 层                          │
│   01_weather / 02_react / 03_memory / 04_multi_agent     │
│   05_code_assistant / 06_omo_style / 07_cache_first      │
├──────────────────────────────────────────────────────────┤
│                  Agent 实现层                             │
│  SimpleAgent  ReActAgent  MemoryAgent  MultiAgentSystem  │
│  AdvancedOrchestrator  CacheFirstAgent                   │
├──────────────────────────────────────────────────────────┤
│                  基础设施层                               │
│  BaseAgent  ToolDef  ToolResult                          │
│  ImmutablePrefix  AppendOnlyLog  VolatileScratch         │
│  ToolCallRepairPipeline  CostAwareRouter  CacheStats     │
├──────────────────────────────────────────────────────────┤
│    工具层                 记忆层                           │
│  tools.py                memory.py                       │
│  (6 个内置工具)           (短期+长期记忆)                   │
├──────────────────────────────────────────────────────────┤
│                 Anthropic SDK                             │
│      Messages API + Tool Use + Prompt Caching            │
└──────────────────────────────────────────────────────────┘
```

> 图中 Examples 层与实现层只示意到 v0.3（01–07）；完整 11 个示例与 13 个模块见上文「项目结构」与「更新记录」。

## 学习路线

1. **阅读文档**：`docs/` 目录下 01→02→…→14 顺序阅读（共 14 章）
2. **阅读源码**：按 `base.py → tools.py → memory.py → simple_agent.py → react_agent.py → memory_agent.py → multi_agent.py → advanced_agent.py → cache_first.py → analysis_agent.py → provider_agent.py → reflexion_agent.py → adapters/` 顺序
3. **运行示例**：`examples/` 下的示例按编号 01→11 逐个运行（示例 10 需先 `pip install openai`）
4. **实战项目**：参考 `05_code_assistant.py` 或 `08_custom_analysis_agent.py`，构建自己的 Agent 应用

## 核心原则

- **理解比记忆重要** — 理解 Agent 循环、工具调用、记忆管理的原理
- **动手比阅读重要** — 每个练习都要实际写代码跑起来
- **从简单开始** — 不要一上来就用重型框架，先理解裸 SDK
- **安全第一** — 始终考虑 Agent 的安全边界和权限控制

---

## 更新记录

> [!warning] 更正（2026-09-13）：`pyproject.toml` 的 `version = 0.1.0`，而下面的更新记录已写到 v0.7.0（2026-05-30）——`pip install -e .` 或 `pip show agent-learn` 会报 **0.1.0**，读者无法用版本号判断拿到的代码对应哪一版文档。建议把 version 同步到 0.7.0（或改动态版本），并明确「版本号以 `pyproject.toml` 为准」。依赖同理：`pyproject.toml` 只有 anthropic + python-dotenv（含 langchain / all extras），**没有 openai**。
> 来源：本机 `pyproject.toml` 实测 · <https://data.jsdelivr.com/v1/packages/gh/L-ingqin12/agent-learn@main?structure=flat>

### v0.7.0 — 2026-05-30: 教程对齐 + 元认知实现 + 生态全景

**新增文档** (3 章):
- `docs/12-agentic-rag-and-protocols.md` — Agentic RAG + MCP/A2A 协议 + 可信 Agent
  - 综合 Microsoft Lessons 5/6/11 + Hello-Agents Chapters 8/10
  - Self-Reflective RAG / Adaptive RAG / Multi-Source RAG 三种模式
  - 四层防护模型 / MCP vs A2A vs ANP 对比 / "Everything is a Tool" 哲学
- `docs/13-metacognition-and-evaluation.md` — 元认知自反思 + Agent 评估框架
  - 综合 Microsoft Lesson 9 + Hello-Agents Chapter 4/12
  - ReAct / Plan-and-Solve / Reflection 三种经典范式详解
  - 三层次评估框架 / LLM-as-Critic / Multi-Dimension Critic
- `docs/14-awesome-agent-ecosystem.md` — Awesome Agent 生态全景 (2026)
  - GitHub 高星项目汇总: AutoGPT (184k), Dify (144k), LangChain (138k) 等
  - 四梯队分级 / 框架能力矩阵 / 选择决策矩阵 / 6 大趋势
  - agent-learn 在生态中的定位

**新增模块**:
- `agent_learn/reflexion_agent.py` — 元认知自反思 Agent
  - Generate → Self-Critique → Refine 循环
  - LLM-as-Critic / Rule+LLM Hybrid / Multi-Dimension 三种模式
  - CriticRegistry — 可插拔评审维度
  - 预置代码评审 (正确性/完整性/效率) + 写作评审 (清晰/完整/简洁)

**新增示例**:
- `examples/11_reflexion_agent.py` — 3 个子 Demo (LLM评审 / 轨迹分析 / 规则检查)

---

### v0.6.0 — 2026-05-30: 知识库扩充 — 生产实践 + 高级模式 + 最佳实践速查

**新增文档** (3 章):
- `docs/09-production-agent-patterns.md` — 生产级 Agent 工程实践 (Google/Mindflow/Arthur.ai 2026 最佳实践)
  - 9 项生产验证工程实践 / 有界自治 / 五层基础设施栈 / 生产就绪检查清单
- `docs/10-advanced-agent-patterns.md` — 高级 Agent 模式 (综合 2025 研究文献)
  - Reflexion/Reflexion++ 自反思 / Tree-of-Thought / Multi-Agent 四拓扑 / 评估框架
  - "越多 Agent 越好" 神话破灭: MAS 消耗 15× token, 单强 Agent 常优于团队
- `docs/11-agent-best-practices-cheatsheet.md` — Agent 开发最佳实践速查手册
  - 架构选择决策树 / 模型选择 / Prompt 工程 / 工具设计 / 记忆管理 / 安全检查清单
  - 开发 8 步流程 / agent-learn 能力矩阵

**项目累计**: 11 章文档 + 10 个 Agent 实现模块 + 10 个可运行示例

> [!warning] 更正（2026-09-13）：上面「MAS 消耗 15× token」出自 Anthropic《How we built our multi-agent research system》（2025-06-13），原文为「In our data, agents typically use about 4× more tokens than chat interactions, and multi-agent systems use about 15× more tokens than chats.」——**语境是 BrowseComp 类研究任务**，且紧接着经济性条件（任务价值要足够高）。把它压缩成普适结论属去掉前提的引用。另：本节「项目累计 11 章 / 10 个模块 / 10 个示例」是 v0.6.0 时的快照，v0.7.0 后已过期，现行口径见上文「项目结构」。
> 来源：<https://www.anthropic.com/engineering/multi-agent-research-system>

---

### v0.5.0 — 2026-05-30: 虚拟内存换入换出 + 多模型适配层

**新增模块**:
- `agent_learn/memory.py` 扩展 — OS 虚拟内存风格的记忆管理
  - `VirtualMemoryStore` — 换入换出引擎 (Page Table / Page Fault / Clock/LRU/LFU)
  - `SwappableMemoryStore` — Agent 即插即用的记忆接口
  - `ReplacementPolicy` — 三种替换策略 (CLOCK/LRU/LFU)
  - 颠簸检测 / 脏页写回 / 钉住机制
- `agent_learn/adapters/` — 多模型适配层 (新包)
  - `base.py` — `BaseModelAdapter` 抽象接口 + 统一数据结构 (UnifiedMessage/UnifiedToolDef/UnifiedResponse)
  - `anthropic.py` — Anthropic Claude 适配器
  - `openai.py` — OpenAI GPT 适配器
- `agent_learn/provider_agent.py` — Provider 无关 Agent (Agent 层不 import 任何 SDK)

**新增示例**:
- `examples/09_memory_swap.py` — 5 个子 Demo (基本换入换出 / 三种策略对比 / 颠簸检测 / 脏页写回 / Agent 集成)
- `examples/10_multi_model_agent.py` — 4 个子 Demo (统一格式 / 适配器抽象 / 模型切换 / 成本对比)

**核心启示**:
- OS 内存管理思想完美映射到 Agent 记忆: Context Window = RAM, Disk = Swap File, Page = 记忆记录
- Agent 层不应关心模型来源 — 通过适配器层将业务逻辑与 Provider SDK 解耦
- 换入换出让 Agent 记忆突破 Context Window 限制
- 切换模型只需一行 `adapter = XxxAdapter()`, Agent 代码零改动

---

### v0.4.0 — 2026-05-30: 定制化问题分析 Agent 框架

**新增文档**:
- `docs/08-custom-problem-agent.md` — 定制化问题分析 Agent 设计方法论

**新增模块**:
- `agent_learn/analysis_agent.py` — 可插拔领域知识的问题分析 Agent
  - `O-H-V-C` 通用分析协议 (Observe→Hypothesize→Verify→Conclude)
  - `DomainKnowledge` — 领域知识库 (FailureMode / DiagnosticRule / EvidenceStrategy)
  - `ProblemAnalysisAgent` — 推理引擎与领域知识分离
  - `create_python_bug_domain()` — Python Bug 诊断知识库 (5 个故障模式)
  - `create_api_debug_domain()` — API 调试诊断知识库 (4 个故障模式)

**新增示例**:
- `examples/08_custom_analysis_agent.py` — 5 个子 Demo 演示领域知识定义、症状匹配、O-H-V-C 流程、定制新领域、API 调试

**核心启示**: 定制化 Agent 开发的关键是将推理协议(通用)与领域知识(可插拔)分离。换一个问题域只需替换 DomainKnowledge + EvidenceCollectors，O-H-V-C 协议不变。五步法: 定义问题域→梳理故障模式→编码规则→实现收集器→验证迭代。

---

### v0.3.0 — 2026-05-30: Reasonix 架构分析与 Cache-First 实现

**新增文档**:
- `docs/07-reasonix-architecture-analysis.md` — DeepSeek-Reasonix 架构深度拆解

**新增模块**:
- `agent_learn/cache_first.py` — 缓存优先 Agent 循环实现
  - `ImmutablePrefix` — 不可变前缀区，启动时 hash 冻结
  - `AppendOnlyLog` — 只追加日志区，旧 turn 天然做新 turn 的 prefix
  - `VolatileScratch` — 易失暂存区，每轮重置，永不上传
  - `ToolCallRepairPipeline` — 四工序修复管线 (Auto-flatten / Scavenge / Truncation Recovery / Storm Breaker)
  - `CostAwareRouter` — 复杂度驱动的动态模型路由
  - `CacheStats` — 实时缓存命中率追踪

**新增示例**:
- `examples/07_cache_first_agent.py` — 5 个子 Demo 演示三区模型、修复管线、成本路由、缓存统计

**核心启示**: Reasonix 把缓存稳定作为架构约束而非事后优化。三区上下文模型保证第 N+1 轮请求 = 第 N 轮 + 新增内容，缓存命中率从 <20% 提升到 >85%。该模式跨模型适用 (DeepSeek / Anthropic / OpenAI)。

> [!warning] 更正（2026-09-13）：「缓存命中率从 <20% 提升到 >85%」在仓库与本机镜像里**都没有对应的 benchmark 脚本、日志或复现命令**（`cache_first.py` 只有 `CacheStats` 计数器），属**项目自述断言、未复核**——引用时请标注为未验证，或补一段可复现的测量。

---

### v0.2.0 — 2026-05-30: oh-my-opencode 架构分析与演进实现

**新增文档**:
- `docs/06-oh-my-opencode-analysis.md` — OMO v4.2.0 架构深度拆解

**新增模块**:
- `agent_learn/advanced_agent.py` — OMO 风格三层 Agent 演进实现
  - `SemanticRouter` — 语义意图分类 (替代关键词 IntentGate)
  - `DynamicModelRouter` — 动态模型路由 (替代硬编码映射)
  - `StrategicPlanner` — 战略规划器 + 内嵌计划验证
  - `AdaptiveConcurrencyManager` — 自适应并发控制
  - `SubAgent / SubAgentRegistry` — 分类驱动的专项子Agent

**新增示例**:
- `examples/06_omo_style_agent.py` — 4 个子 Demo 演示路由、规划、子Agent 选择、完整编排

**核心启示**: OMO 的三层 Agent 编排 (Router→Orchestrator→SubAgent) 是 Multi-Agent 系统的成熟范式。演进方向: 语义路由、动态模型选择、双向反馈。

---

### v0.1.0 — 2026-05-30: 初始版本

**文档** (5 章):
- `01-agent-overview.md` — AI Agent 概念、架构模式
- `02-core-components.md` — LLM/工具/记忆/规划 详解
- `03-learning-roadmap.md` — 4 阶段学习路线
- `04-frameworks-deep-dive.md` — 6 大框架对比 (Anthropic SDK / LangChain / LangGraph / CrewAI / AutoGen / Semantic Kernel)
- `05-practice-exercises.md` — 递进式代码练习

**核心模块** (6 个):
- `base.py` — Agent 基类和工具定义
- `tools.py` — 6 个内置工具
- `memory.py` — 短期+长期记忆系统
- `simple_agent.py` — 基础 Tool-Use Agent
- `react_agent.py` — ReAct Agent 从零实现
- `multi_agent.py` — 多 Agent 协作系统 (Sequential + Hierarchical)

**示例** (5 个):
- `01_weather_agent.py` — 天气查询
- `02_react_agent.py` — ReAct 循环
- `03_agent_with_memory.py` — 记忆系统
- `04_multi_agent_collab.py` — 多 Agent 协作
- `05_code_assistant.py` — 代码助手

## 相关文档

- [[AI-Dev-KB-Home]] — ai-dev 子库首页，本教程体系的总入口
- [[LLM-Agent开发基础]] — Agent 四组件与 ReAct 循环的基础篇
- [[MCP协议开发实战]] — 工具层的协议化集成实践
- [[Function-Calling工具调用实战]] — 工具调用与 JSON Schema 基础的姊妹篇
- [[04-frameworks-deep-dive]] — 本系列第四部分：框架全景与拆解

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 补疏漏 | 项目结构写「docs (8 章)」且只列 01–07 | 同步为 14 章（01–14）；依据上游 main 文件清单（jsDelivr）与本机 `docs/` 实测 |
| 补疏漏 | 项目结构 examples 只列 01–07 | 补 08–11 四个示例，标注为 11 个 |
| 补疏漏 | `agent_learn/` 未列 `analysis_agent.py`、`provider_agent.py`、`reflexion_agent.py` 与 `adapters/` 包 | 树中补齐（本机实测 13 个 `.py` + `adapters/` 4 文件），并在模块表后加注说明 |
| 补疏漏 | 学习路线止于 `docs 08`，源码顺序缺 3 个模块，示例未标范围 | 改为 01→14 章；源码顺序补 `provider_agent` / `reflexion_agent` / `adapters/`；示例 01→11 |
| 补疏漏 | 快速开始照做后跑示例 10 会 `ModuleNotFoundError` | 加 `pip install openai` 说明与安装自检；依据 `requirements.txt`、`pyproject.toml`、`adapters/__init__.py:15`（无条件导入）、`adapters/openai.py`（`__init__` 内 `from openai import OpenAI`） |
| 补疏漏 | 快速开始无可验收判据（无预期输出 / 失败判据 / 自检命令） | 补 `pip show agent-learn`、`python -c "import anthropic, dotenv"` 自检与四类失败判据、通过标准 |
| 纠错 | `pyproject.toml` 版本 0.1.0 与更新记录 v0.7.0 不一致 | 「更新记录」前加更正块：注明 `pip install -e .` 报 0.1.0、建议同步 0.7.0 或改动态版本 |
| 纠错 | 「MAS 消耗 15× token」被写成普适结论 | 补 Anthropic 原始出处与适用条件（BrowseComp 类研究任务 + 经济性前提） |
| 加厚 | 「缓存命中率 <20% → >85%」无任何复现依据 | 标注为项目自述断言、未复核，并说明可复现要求 |

外部来源已登记至 `sources/learning-notes.md`。

> 回链：[[CORRECTIONS]] · [[AGENTS]]

