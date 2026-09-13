---
title: Agent Harness 解剖学与构建决策树
aliases: [Harness解剖学, Agent Harness知识, 编排外壳构建指南]
tags: [ai/ops, ai/agent]
created: 2026-08-26
updated: 2026-09-13
status: review
source: 综合视图文档——外部依据：Anthropic《Building Effective Agents》、Simon Willison 编码代理原理综述、harness engineering 论述；内部依据：本库 OpenCode/Pi/CC 拆解文档（正文逐条挂锚）
fetched_at: 2026-08-26
---

# Agent Harness 解剖学与构建决策树

> [!abstract] 定位
> 库内 harness 相关知识此前散落在调研报告、课程笔记与文章拆解中，缺一张综合视图。本文给出：**harness 的定义谱系**（vs framework/scaffold）、**七件套解剖**（每件挂库内锚点）、**Claude Code / OpenCode / Pi / DSH 四家实现对照**、**从零构建的决策树**（Anthropic 五模式 + start-simple 原则）与反模式清单。所有外部论断附来源，内部论断挂文档锚点。

See also: [[参考-OpenCode-技术调研报告]] · [[参考-Pi-Agent-技术调研报告]] · [[main-subagent-realtime-interaction]] · [[agent-memory-context-knowledge-design]] · [[Claude-Ops-KB-Home]]

## 一、定义与谱系

| 术语 | 含义 | 代表 |
|------|------|------|
| **Framework** | 提供抽象层让"你写 agent"的代码库 | LangChain/LangGraph、Spring AI |
| **Scaffold** | 围绕模型的最小可运行外壳（提示词+循环+工具） | 早期 openai/evals 式脚本 |
| **Harness** | 生产级 scaffold：把系统提示词、工具循环、上下文管理、权限、子代理、扩展点、观测**七件事产品化**的外壳 | Claude Code、OpenCode、Pi、Cursor |

术语工程化脉络：Simon Willison 把编码代理归纳为"harness 包住模型反复调用工具"的回路（[practitioner guide 转述](https://subagentic.ai/howtos/simon-willison-how-coding-agents-work/ <!-- scan-ignore: 技术博客，非订阅源 -->)）；"harness engineering" 已被当作独立工程学科讨论（[The Rise of Agentic Engineering Part 5](https://dev.to/raminjafary/the-rise-of-agentic-engineering-part-5-harness-engineering-emerges-2d9o)）；社区甚至出现 100+ harness 的策展清单（[best-of-Agent-Harnesses](https://github.com/RyanAlberts/best-of-Agent-Harnesses)）。Anthropic 官方立场：能 workflow 别 agent，**从最简开始按需加复杂度**（[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)）。

> [!info] 与本库的关系
> 本库 AGENTS.md 协议 + DSH 运行时即一个自建 harness 实例；[[Vercel-AI编码Agent-Harness课程]] 是其教学版；[[Loop-Engineering-深度拆解-从产品功能集到方法论包装]] 是对其过度包装倾向的批判视角。

## 二、七件套解剖（每件 = 职责 / 实现 / 库内锚点）

### 1. 系统提示词脚手架
职责：角色定义 + 环境注入 + 渐进披露。
实现：CLAUDE.md/AGENTS.md 分层加载；SKILL.md 按需注入防撑爆窗口。
锚点：[[Claude-Code实用Skills参考]] · [[Skill规模化管理-从渐进式披露到检索式发现]] · Pi ~800 token 预算哲学（[[pi-agent-framework-knowledge]]）

### 2. 工具循环与参数契约
职责：模型↔工具的 ReAct 循环与 schema 校验。
实现：OpenCode 用 zod 契约注册自定义 tool；Pi `defineTool<TParams extends TSchema>` 用 TypeBox；MCP 作为外挂工具总线。
锚点：[[参考-OpenCode-技术调研报告]] §4 · [[参考-Pi-Agent-技术调研报告]] §11.1 · [[MCP协议开发实战]] · [[Function-Calling工具调用实战]]

### 3. 上下文管理与记忆
职责：有限注意力预算下的装配/压缩/持久化。
实现：compaction、三级记忆（L1 窗口/L2 checkpoint/L3 知识库）、前缀稳定排序保 cache 亲和。
锚点：[[agent-memory-context-knowledge-design]] · [[上下文工程-注意力预算与四层解法]] · [[上下文工程落地实践-从理论到Claude-Code实现]]

### 4. 权限与沙箱
职责：工具调用的策略闸门与执行隔离。
实现：OpenCode permission last-match 规则引擎 + 程序化审批 hook（`permission.ask`），权限键实为 doom_loop/external_directory；Pi 无内核权限 → 容器化兜底；Sidecar 场景加命名空间级边界。
锚点：[[参考-OpenCode-技术调研报告]] §8/§11 · [[参考-COM组件框架-Windows集成]] §五安全边界

### 5. 子代理与编排
职责：上下文分区并行 + 委派协议 + 活性监控。
实现：task 委派/subagent_type；fan-out 分发卡三要素；steer/followUp 双队列打断注入；15× token 经济学下的看门狗必要性。
锚点：[[main-subagent-realtime-interaction]] · [[fan-out-subagent-pattern]] · [[Anthropic多智能体研究系统拆解]] · 多代理何时不用见 [Claude 官方 when-and-how](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)

### 6. Hook 与扩展面
职责：不改内核注入横切逻辑（预处理/审批/遥测/短路）。
实现：OpenCode plugin hooks（chat.params/tool.execute.before/permission.ask/event…）；Pi 25+ 扩展事件 + resources_discover；跨框架差异见 DSH 系列。
锚点：[[DSH插件与Hook开发最佳实践]] · [[DSH跨框架Skills与MCP加载]]

### 7. 可观测与评测
职责：trace 化每次模型/工具调用；以评测分驱动质量门控（RETRY/ESCALATE）。
锚点：详见姊妹篇 [[agent-evals-observability]] · [[state-machine-quality-gate-loop]] · [[Claude-Code记忆机制源码拆解]]（会话文件即观测数据源之一）

## 三、四家实现对照

| 七件套 | Claude Code | OpenCode | Pi | DSH（本库） |
|--------|-------------|----------|----|------------|
| 提示词脚手架 | CLAUDE.md+Skills | agent/*.md frontmatter | manifest+~800 预算 | AGENTS.md 协议 |
| 工具循环 | 内置+MCP | zod 自定义 tool+MCP | TypeBox defineTool | DSH 工具集+MCP |
| 上下文/记忆 | compaction+记忆机制 | 会话文件+SDK 读写 | 树状 JSONL+steer 注入 | session jsonl+goal 工具 |
| 权限/沙箱 | settings allowlist | permission 引擎+ask hook | 无内核→容器化 | approval policy+file sandbox |
| 子代理 | Task/Agent 工具 | task 委派+四内置件 | 无 spawn→多 Session 模拟 | subagent/workflow/ralph |
| Hook 扩展 | hooks 事件 | plugin hooks 总线 | 25+ extension events | hooks+skills 加载器 |
| 观测评测 | transcript jsonl | /event SSE 流 | print/RPC 模式 | job_output/goal 工具闭环 |

（每格均可回溯到 §二 对应锚点文档；OpenCode/Pi 列的事实口径以各自调研报告 §11 实机核验为准）

## 四、从零构建决策树（有依据版）

```
0. 先定成功标准与评测集（Anthropic：evals 先于复杂度）
1. 任务可枚举为固定步骤？ ──是──▶ Workflow：prompt chaining / routing
2. 步骤独立可并行？ ──是──▶ parallelization（并行买覆盖率，注意 token 放大）
3. 需要动态拆解未知路径？ ──是──▶ orchestrator-workers（先读 when-not-to 清单）
4. 结果需迭代打磨且有客观判据？ ──是──▶ evaluator-optimizer 循环
5. 以上都不满足才上自由 Agent loop（工具+环境反馈自主多步）
6. 工具面优先走 MCP 外挂而非改内核；权限闸门第 4 件同步上线
7. 复杂度每加一层，回到第 0 步验证评测增量是否为正
```

依据：[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 五模式与 start-simple 原则；并行/编排收益数据见 [[Anthropic多智能体研究系统拆解]] §二。

## 五、反模式清单

| 反模式 | 症状 | 解药 |
|--------|------|------|
| 方法论包装先行 | 先造概念体系再找场景 | [[Loop-Engineering-深度拆解-从产品功能集到方法论包装]] 的批判框架 |
| 过早多代理 | 单代理+好工具就能赢的任务上 fan-out | [when not to use multi-agent](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)；先跑通 workflow |
| 无预算 fan-out | 15× token 账单事故 | 编排层预算闸（[[opencode-pi-base-development-analysis]] 背压节） |
| 提示词万能论 | 把 harness 该做的工程塞进 prompt | 七件套各归其位（本文 §二） |
| 评测后置 | 上线后才定义"成功" | 决策树第 0 步 + [[agent-evals-observability]] |

## 六、待确认项

> ① Cursor/Aider 等 harness 在七件套上的差异未逐项核验（仅入清单未入对照表）；② "harness engineering" 术语的最早提出者考证（当前仅追溯到 2025 年社区论述）；③ DSH ralph 模式的公开对标物。

> [!success] 残余复核（2026-09-13）：②③ **已定论**（含 ③ 的公开对标物），仅 ① 仍开放。
> - **③ 内部定义（已定论）**：`ralph` 是 DSH 内置的**模型工具** `@deepseek-ai/dsh-tool-ralph`——对**一个不可变目标**跑固定前台循环，每 Round 起一个**全新**子 agent 在共享工作区作业，跨 Round 只传一份有界结构化报告；父级对话与先前子会话**绝不**作为种子（工作区即长期记忆）。模型提交 `{ objective, maxRounds? }`，调用阻塞至整个运行结算；终态 `complete` / `blocked` / `budget-limited`，报告状态为 `continue` / `complete` / `blocked`；默认且上限 `maxRounds = 256`、`maxHandoffChars = maxResultChars = 16384`。官方提示词明确要求「仅当用户明确要求 Ralph 式全新 agent 迭代时使用」，普通长期工作走 goal 工具、有界委派走 subagent/workflow。
> - **③ 公开对标物（已定论）**：即 **Geoffrey Huntley 的「Ralph Wiggum」技术**，作者原文《Ralph Wiggum as a "software engineer"》首发 **2025-07-14**（页面 dateModified 2026-02-19）。原文自述「Ralph is a technique. In its purest form, Ralph is a Bash loop」——最小形态就是 `while :; do cat PROMPT.md | claude-code ...`，即**对同一目标反复起全新 agent**。与 DSH 版的映射：Huntley 的纯 Bash 循环 ↔ DSH 把它产品化为固定前台循环（每 Round 全新子 agent + 有界报告交接 + `maxRounds` 上限 + 结构化终态）。**差异点**：Huntley 版不设 Round 上限、不做报告校验、状态全靠工作区与文件；DSH 版加了轮次上限、报告 schema 校验与 `complete/blocked/budget-limited` 终态——即「把社区技巧工程化」。该包 README 自身「进一步探索」章节仍**零外部引用**（只有 DSH 内部文档链接），故这层对标是外部考证得出的，不是上游自述。
>   依据（取回 2026-09-13）：<https://ghuntley.com/ralph/>
> - **② 术语最早提出者（已定论）**：**Mitchell Hashimoto**（HashiCorp 联合创始人，Terraform / Ghostty 作者）在 **2026-02-05** 的博文《My AI Adoption Journey》第 5 步「Engineer the Harness」中自述提出该词，逐字为：*"I don't know if there is a broad industry-accepted term for this yet, but I've grown to calling this 'harness engineering.' It is the idea that anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again."*——注意他**自己声明这是个人命名**（"I don't know if there is a broad industry-accepted term for this yet"），故「最早提出者」应表述为「**该词由 Hashimoto 于 2026-02-05 命名**」，而非「某人发明了该概念」；他也给出两条落地形态：改 AGENTS.md（隐式提示）+ 写程序化工具。
>   依据（取回 2026-09-13）：<https://mitchellh.com/writing/my-ai-adoption-journey>（原站为 JS 渲染，正文经 <https://web.archive.org/web/2026id_/https://mitchellh.com/writing/my-ai-adoption-journey> 取回）
>   ⚠️ 本节 §一 原写「当前仅追溯到 2025 年社区论述」——该表述应更正为「2026-02-05 由 Hashimoto 命名」；另有二手来源称更早的「harness」概念根在 2025-11 的 Anthropic 博文，本次**未取回原文，不采信**。
> - **① 仍开放**：Cursor/Aider 的七件套差异需逐项抓两家的权限/扩展/子代理官方文档。注意本库对这两家**无实机核验**（§三 表的四家是 CC/OpenCode/Pi/DSH，均有源码或文档实证），不可把四家的口径外推到它们身上。判据：逐项产出「七件套 × {Cursor, Aider}」对照表并各挂官方文档锚点，或补实机核验。
> - 依据（③ 内部定义）：`%USERPROFILE%\.dsh\profiles\node_modules\@deepseek-ai\dsh-tool-ralph\README.zh.md`（含「使用本包 / 配置 / 进一步探索」三节）

## Related

[[参考-OpenCode-技术调研报告]] · [[参考-Pi-Agent-技术调研报告]] · [[agent-evals-observability]] · [[Anthropic多智能体研究系统拆解]] · [[agent-memory-context-knowledge-design]] · [[main-subagent-realtime-interaction]] · [[lognet-rootcause-multiagent-architecture]] · [[Claude-Ops-KB-Home]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 加厚 | §六 ③「DSH ralph 模式的公开对标物」只有问题、无定义 | 加复核块补出**内部定义**（本机 `@deepseek-ai/dsh-tool-ralph` README）：不可变目标 + 每 Round 全新子 agent + 单份有界报告跨 Round、父会话不作种子、`maxRounds=256`/`maxHandoffChars=16384`、终态 complete/blocked/budget-limited |
| 定论 | §六 ③「DSH ralph 模式的公开对标物」 | 加复核块：对标物为 **Geoffrey Huntley 的「Ralph Wiggum」技术**（《Ralph Wiggum as a "software engineer"》2025-07-14，「Ralph is a Bash loop」）；给出与 DSH 版的映射及三处工程化差异（轮次上限/报告校验/结构化终态）。依据取回 2026-09-13：ghuntley.com/ralph/ |
| 定论 | §六 ②「harness engineering」术语最早提出者 | 加复核块：**Mitchell Hashimoto 于 2026-02-05**《My AI Adoption Journey》Step 5「Engineer the Harness」命名，逐字引其自述（他自称个人命名、非行业既定术语）；并更正 §一「仅追溯到 2025 年社区论述」。依据取回 2026-09-13：mitchellh.com/writing/my-ai-adoption-journey（经 web.archive.org 取回正文） |
| 留开放 | §六 ① Cursor/Aider 在七件套上的差异 | 需逐项抓两家官方文档产出对照表；本库对这两家无实机核验（§三 四家为 CC/OpenCode/Pi/DSH），不可外推 |

回链：[[CORRECTIONS]] · [[AGENTS]]
