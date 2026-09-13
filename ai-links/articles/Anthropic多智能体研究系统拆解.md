---
title: Anthropic多智能体研究系统拆解
aliases: [Multi-Agent Research System, 编排者-工作者模式拆解]
tags: [ai/links, ai/agent]
created: 2026-08-26
updated: 2026-09-13
status: review
source: Anthropic Engineering《How we built our multi-agent research system》(2025-06) 及多源转述交叉验证
source_urls:
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://simonwillison.net/2025/Jun/14/multi-agent-research-system/
  - https://www.zenml.io/llmops-database/building-production-multi-agent-research-systems-with-claude
author: Anthropic（原文）/ 本库拆解
fetched_at: 2026-08-26
---

# Anthropic 多智能体研究系统拆解

> [!abstract] 为什么补这篇
> 文章库此前覆盖 Skill 系统、上下文工程、记忆机制、可解释性，唯独缺**多智能体编排**一组——而这恰是本库当前主线（OpenCode/Pi 基座二开 + LogNet 专家编排）。Anthropic 这篇是生产级 Orchestrator-Worker 模式最完整的一手复盘，其"委派工程/上下文经济学/评测三件套/生产化教训"可直接映射进 [[main-subagent-realtime-interaction]] 的协议设计与 [[opencode-pi-base-development-analysis]] 的基座选型判断。

See also: [[Articles-Index]] · [[AI-Links-KB-Home]] · [[fan-out-subagent-pattern]] · [[state-machine-quality-gate-loop]] · [[lognet-rootcause-multiagent-architecture]]

## 一、架构：Orchestrator-Worker

```
用户研究请求
   │
Lead Agent（编排者，extended thinking）
   ├─ 拆解为可并行的子方向 ──▶ Subagent×3–5（各自独立上下文窗口）
   │        └─ 并行工具调用：搜索/抓取 → 压缩摘要回传
   ├─ 汇总子结论，必要时追加派发（迭代式）
   └─ 引用一致性检查 ▶ 最终带引用报告
Memory/Citation Agent 等专职角色按需挂载
```

- 与 [[Agent驱动Skill迁移设计]] 的单代理 Skill 注入互补：这里是**上下文分区**路线——每个 subagent 独占窗口，主上下文只收摘要
- 关键约束：编排是**同步扇出-汇聚**循环；subagent 数量按查询复杂度弹性伸缩而非固定

## 二、为什么有效：上下文经济学

| 观测 | 数字 | 含义 |
|------|------|------|
| token 放大系数 | 多智能体 ≈ 单对话的 **15×** tokens | 并行买时间与覆盖率，烧钱换质量；预算治理必须前置 |
| 工具调用深度收益 | 子代理工具调用翻倍 → 相对提升 **90.2%** | 收益来自"多试几次"而非更聪明 |
| 并行工具调用 | 启用后相对提升约 14.5% | 同窗口内并发读操作几乎白赚 |

> [!warning] 残余复核（2026-09-13）：上表第 2、3 行**口径与出处均有问题，两行数字都不宜照引**（原表保留以便追溯）。依据为本次经代理直取的官方原文（HTTP 200）与 2025-08-07 Wayback 快照，两版在数字上一致。
> - **90.2% 的归属被写错了**：原文逐字为 "We found that a multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents outperformed single-agent Claude Opus 4 by **90.2%** on our internal research eval."——它是**多智能体 vs 单智能体**的相对提升，基准是 **Anthropic 内部 research eval**，**与「子代理工具调用翻倍」没有关系**；原文确实说工具调用数是解释变量，但那是另一句（见下）。
> - **14.5% 在原文中不存在**：现网原文、2025-08-07 快照、本文两条 `source_urls`（Simon Willison 转述、ZenML 页面）**四处均检索不到 `14.5` 这个数字**。原文关于并行化的可核实表述是**耗时**口径而非性能分——"These changes cut research time by **up to 90%** for complex queries"。
> - **可替换进表的原文量化**：BrowseComp 评测中三个因素合计解释 **95%** 的性能方差，其中 **token 用量单独解释 80%**，**工具调用数**与**模型选择**为另两个因素；token 放大系数 15×（多智能体 vs 聊天）、4×（单 agent vs 聊天）两行与原文一致，可保留。
> 来源：https://www.anthropic.com/engineering/multi-agent-research-system

> [!tip] 对齐本库
> 15× 系数正是 [[main-subagent-realtime-interaction]] 里"看门狗+邮箱"存在的理由——放大器越猛，活性监控与打断越关键。

## 三、委派工程（Delegation Engineering）——全文最有复用价值

1. **教编排者如何委派**：lead prompt 明确"何时拆、拆几路、每路给多少努力"
2. **努力分级规则**（写进系统提示词）：
   - 简单事实查证 → 1 agent，3–10 turns
   - 比较/综述 → 2–4 agents 分维度
   - 新颖争议题 → 起步即可 5+ agents，允许迭代加派
3. **子任务描述三要素**：目标（客观可判）→ 输出格式（摘要规格）→ 工具清单（边界）。模糊委派 = 子代理自由发挥 = 回传噪声

> [!note] 与本库对照
> 三要素即 [[fan-out-subagent-pattern]] 的"分发卡"字段集；努力分级表可平移进 OpenCode agent frontmatter 的 description 字段（模型据描述路由，见 [[参考-OpenCode-技术调研报告]] §1.3）。

## 四、评测三件套

| 方法 | 做法 | 防什么 |
|------|------|--------|
| LLM-as-judge | 固定 rubric 打分（引用支撑/覆盖/平衡），与人工评分校准一致性 | 主观漂移 |
| 人工真实任务 | 内部工程师盲测对比单代理基线 | "基准好看但没人用" |
| 生产遥测 | 真实使用率/完成率回归 | 过拟合到评测集 |

本库 [[state-machine-quality-gate-loop]] 的 QA 门控可直接引用该三层结构做 ESCALATE 判据。

## 五、生产化教训（踩坑清单）

1. **状态即债务**：会话中途崩溃 → 需要 checkpoint/resume 才能救长任务；无状态重跑代价 15×
2. **中断恢复**：用户随时打断，必须支持从任意 step 续跑（对应本库 checkpoint 模板）
3. **token 预算治理**：不设上限的 fan-out = 账单事故；编排层要有预算闸门与降级路径
4. **引用保真**：子代理压缩摘要时丢引用 → 最终报告不可溯源；摘要规格里强制保留 URL/出处
5. **同步 vs 异步**：v1 全同步编排简单但延迟线性叠加；异步+事件通知是演进方向（OpenCode issue #5887 同款缺口）

## 六、对本库的直接映射

| Anthropic 教训 | 本库落点 | 差距动作 |
|----------------|----------|---------|
| 努力分级委派 | OpenCode agent frontmatter / Pi extension binding | 写入基座配置模板（Phase 0 交付物之一） |
| 子任务三要素 | fan-out-subagent-pattern 分发卡 | 已对齐 ✓ |
| checkpoint/resume | main-subagent-realtime-interaction T3 恢复原语 | 协议已设计，实现排期 M3 |
| token 预算闸 | opencode-pi-base-development-analysis §会话池背压 | 待在 Sidecar 落地 |
| 引用保真 | LogNet EventNode.raw_offset 可回溯指针 | PoC 已实现（query_logs refs 字段）✓ |

## 七、待确认项

> ① 90.2%/14.5% 两数的精确实验口径（相对/绝对、基准集）；② Lead Agent 是否使用 extended thinking 的 A/B 数据；③ Memory Agent 的持久化形态（原文仅一笔带过）；④ Citation Agent 独立成角色的版本节点。

> [!success] 残余复核（2026-09-13）：四项**全部结案**——① 口径已定位并含一处订正（见 §二 更正块）；②③④ 的答案是「问法本身需要修正」，而不是「查不到」。
> **① 90.2% 是相对提升**，逐字 "outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval"（基准集 = 内部 research eval，非公开集；对照组 = 单智能体 Claude Opus 4）。**14.5% 判定为无出处**：在官方原文（现网 + 2025-08-07 快照）与本文两条 `source_urls` 中均无该数字，应按 §二 更正块换成原文的 95%/80% 或删除。
> **② 只有定性表述，无 A/B 数字**：原文逐字 "The lead agent uses thinking to plan its approach, assessing which tools fit the task, determining query complexity and subagent count, and defining each subagent's role. Our testing showed that extended thinking improved instruction-following, reasoning, and efficiency."——可确认「用了 extended thinking 且测试显示有改善」，**但文章未公布任何 A/B 数值、样本量或基准**，该问项到此为止，不必再找。
> **③ 原文没有「Memory Agent」这个角色**：Memory 在原文中是**持久化载体**，不是可挂载的 agent。可核实的两处逐字为——"saving its plan to Memory to persist the context, since if the context window exceeds **200,000 tokens** it will be truncated and it is important to retain the plan"；"agents summarize completed work phases and store essential information in **external memory** before proceeding to new tasks… they can retrieve stored context like the research plan from their memory"。即持久化形态 = **会话外的计划/阶段摘要文件**，触发条件是上下文逼近 20 万 token 截断。原文确实提到的独立角色是 `LeadResearcher` 与 `Subagents`，加上末尾的 `CitationAgent`，**没有 Memory Agent**。
> **④ 无「版本节点」可考**：该文不是版本化文档（Anthropic engineering 博客不标版本），2025-08-07 快照与现网版本在角色命名上完全一致（均为 `LeadResearcher` + `Subagents` + `CitationAgent`），不存在可考的「何时独立成角色」节点。且原文把 CitationAgent 写成研究循环结束后的一个处理步骤——"passes all findings to a CitationAgent, which processes the documents and research report to identify specific locations for citations"——**未称其为可按需挂载的独立角色**；本文 §一 架构图里「Memory/Citation Agent 等专职角色按需挂载」属转述时的角色化归纳。
> 来源：https://www.anthropic.com/engineering/multi-agent-research-system （本次直取 HTTP 200）；https://web.archive.org/web/20250807031043/https://www.anthropic.com/engineering/multi-agent-research-system

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 残余复核 | ① 90.2%/14.5% 的精确实验口径（相对/绝对、基准集） | 90.2% = 多智能体（Opus 4 lead + Sonnet 4 subagents）相对单智能体 Opus 4 在**内部 research eval** 上的相对提升（原文逐字）；**14.5% 在原文现网版、2025-08-07 快照及两条 source_urls 中均无出处**，已标为无出处并给出可替换的 95%/80% 口径 |
| 残余复核 | ② Lead Agent 是否使用 extended thinking 的 A/B 数据 | **结案：无 A/B 数据**。原文只有定性句 "Our testing showed that extended thinking improved instruction-following, reasoning, and efficiency."，未公布数值/样本量 |
| 残余复核 | ③ Memory Agent 的持久化形态 | **结案：原文无此角色**。Memory 是持久化载体（plan 持久化、阶段摘要外部记忆），触发条件为上下文逼近 **20 万 token** 截断；原文的具名角色只有 `LeadResearcher` / `Subagents` / `CitationAgent` |
| 残余复核 | ④ Citation Agent 独立成角色的版本节点 | **结案：无版本节点可考**。该文非版本化文档，2025-08-07 快照与现网命名一致；原文把 `CitationAgent` 写作研究循环末段的一个处理步骤，未称其为可挂载角色，§一 的「按需挂载」属转述归纳 |

## Related

- [[main-subagent-realtime-interaction]] · [[fan-out-subagent-pattern]] · [[state-machine-quality-gate-loop]] — 本库协议侧对照
- [[参考-OpenCode-技术调研报告]] · [[参考-Pi-Agent-技术调研报告]] — 基座能力依据
- [[lognet-rootcause-multiagent-architecture]] — 专家编排消费方
- [[上下文工程落地实践-从理论到Claude-Code实现]] — 单代理侧上下文工程姊妹篇
