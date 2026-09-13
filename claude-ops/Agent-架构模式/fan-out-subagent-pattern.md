---
title: Fan-Out 子智能体分发模式
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-01
updated: 2026-09-13
status: stable
---

# Fan-Out 子智能体分发模式

> [!abstract] Fan-Out 扇出模式 — 主智能体并行分发任务到多个子智能体的设计模式与实现方案

See also: [[Claude-Ops-KB-Home]] · [[state-machine-quality-gate-loop]] · [[opencode-multi-agent-architecture]] · [[main-subagent-realtime-interaction]]

## 定义
主智能体将复杂任务分解为 N 个子任务，一次性并行分发给多个子智能体，汇总结果。

> [!warning] 回传内容不是无损的（2026-09-13 补）
> 上句隐含「分发 → 原样收回」，但子智能体的返回值**可能被截断**，不能默认完整。
> - 社区证据：Claude Code issue [#17208](https://github.com/anthropics/claude-code/issues/17208)（closed / not_planned）正文逐字写「With run_in_background: true, output is truncated to 30K chars」，并转引变更记录「v2.1.2: Fixed API context overflow...truncating to 30K chars」；[#27483](https://github.com/anthropics/claude-code/issues/27483)（closed / duplicate，目标 #27482）标题即「Add max_return_size parameter to Task tool for task-notification truncation」。
> - **口径说明**：30K 这个数字来自 issue 正文对变更记录的转引，**现行官方文档并没有「子智能体返回值上限」条款**（官方只有 `maxTurns` 触发的 partial output，以及 Bash 工具约 30,000 字符的内联上限）。因此只能写作「社区证据 / 变更记录显示」，不能写成「官方 changelog 规定」。
> - 官方相邻语义（子智能体与前后台 fork 模式）见 <https://code.claude.com/docs/en/sub-agents>。
> 处置三条：①子智能体只回**结论 + 证据指针**（文件路径/行号/URL），不回长正文；②长产物落盘后回传路径；③汇总方对每个回传先做**完整性验收**（能否顺着证据指针复现）再采信。

## 适用条件
可以 Fan-Out: 操作不同文件、同一文件不同维度、都是只读
不能 Fan-Out: 同一文件且有写权限冲突、B依赖A的输出

> [!note] 扇出规模判据（2026-09-13 补）
> 光有「能/不能」二分还不够，开工前还要过三道闸门（Claude Code 侧官方口径，见 <https://code.claude.com/docs/en/sub-agents>）：
>
> | 闸门 | 默认值 | 调整方式 |
> |---|---|---|
> | 并发子智能体数 | **20**，超出即 Agent 工具失败并报 `Concurrent subagent limit reached` | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`（需 v2.1.217+；ultracode 会话豁免） |
> | 嵌套深度 | v2.1.172–2.1.216 = 5（不可改）；v2.1.217–2.1.218 = 1；v2.1.219 起 = 3 | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` |
> | 非内置子智能体 `description` 总量 | 合计超 15,000 token 时启动告警 | 精简 description |
>
> **另有一条独立约束**：并发上限只是模型侧闸门，机器资源是另一条——本库 [[subagent-lessons-learned-2026-07-03]] 记过并行开工导致的资源冲突崩溃，故「同时开工数」必须按内存预算单独设限，不能直接取 20。
> **规模判据**：N ≤ 并发上限，且**每个子任务都要有独立可验收的产物**；产物无法逐个验收时，应减少扇出而不是加大并发。
> **失败模式清单**（设计时逐条给降级路径）：超时 / 部分失败（N 个中 1 个挂掉）/ 返回值截断 / 写冲突 / 被并发上限拒绝。

## OpenCode 生态方案
| 方案 | 机制 | 并行上限 | 来源与核验（2026-09-13） |
|------|------|:--------:|------|
| opencode-agent-intercom | spawn() 非阻塞 | 可配置 | 仓库实为 <https://github.com/feanor5555/opencode-agent-intercom>；官方 description 逐字「opencode plugin: bidirectional control channel from the primary agent to running subagents — async spawn, message injection, live status, abort」。**版本 / commit 待锁** |
| Ouroboros Bridge | MCP 钩子 | 10 | 待补上游仓库链接与 commit |
| swarm-control | 文件分解 | 4 | 待补上游依据（本轮未取到可引用的表述） |
| Ephemeral Team | 原生 team() (提案中) | 可配置 | ⚠️ **已终结，不要再等** |

> [!warning] 更正（2026-09-13）：Ephemeral Team 行已过期
> 该提案与它的实现 PR 都已关闭，不能再列为候选方案（原表述为「原生 team() (提案中) | 可配置」）：
> - opencode issue [#19999](https://api.github.com/repos/anomalyco/opencode/issues/19999)：title「[FEATURE]: Ephemeral Sub-Agent Teams (parallel multi-agent orchestration)」，`state=closed`、`state_reason=not_planned`、`closed_by=github-actions[bot]`。
> - 对应实现 PR [#20152](https://github.com/anomalyco/opencode/pull/20152)「feat(tool): add experimental team tool for parallel subagents」：`state=closed`、`merged=false`、`merged_at=null`。
> 结论：**不要把「原生 team()」写进候选路径，也不要为它留等待窗口**（[[state-machine-quality-gate-loop]] 的路径 C 同此结论）。
>
> 「并行上限」列的口径本身也需补齐：应写明是「每 tool call」「每会话」还是「插件级」，并附测法与原始输出；本轮只有 agent-intercom 拿到了仓库级依据，其余三行待补。

## 防冲突
- 有写权限的永不并行同一文件
- 只读可以任意并行
- 汇总阶段交叉验证（同一问题被多个子智能体发现→提升优先级）

> [!note] 汇总规则与冲突处置（2026-09-13 补）
> 上面三条是断言，落到可执行还差一维判据与失败模式：
>
> | 环节 | 缺的判据 | 建议规则 |
> |------|----------|----------|
> | 交叉验证 | 「多个发现 → 提升优先级」没有量化 | 同题 k 次命中：k ≥ 2 记为「已交叉确认」，k = 1 记为「单点，需复核」；k 次结论互相矛盾时不取多数票，改为**升级人工/主智能体裁决** |
> | 去重 | 没有去重键 | 以「文件路径 + 行号」或「URL + 引文」为去重键；同一键的多个回传合并，保留证据最完整的一份 |
> | 冲突裁决 | 「写权限的永不并行」只覆盖了事前 | 事后发现写冲突时：以**先落盘且通过验收**的版本为准，另一份转为该文件的「候选补丁」再合 |
> | 部分失败 | 没写 N 个里挂 1 个怎么办 | N 份结果按「已验收 / 未回传 / 明确失败」三态统计；未回传与失败不参与交叉验证计数，避免把缺失当成「无人发现」 |

## Claude Code 对比
Claude Code 有原生 Agent 工具支持 `run_in_background: true` 实现 Fan-Out，而 OpenCode 依赖插件生态。

> [!warning] 更正（2026-09-13）：前半句需收紧、后半句已过时（原表述为上面整句）
> - **Claude Code 半句**：Agent 工具确实支持前台/后台子智能体（官方见 <https://code.claude.com/docs/en/tools-reference>），但 `run_in_background` 是 **Bash 工具**的参数，子智能体的前后台由 fork 模式决定——写成「Agent 工具支持 `run_in_background: true`」会把两个工具的开关混为一谈。
> - **OpenCode 半句**：官方**已原生内置 subagent 与并行调度**，不再是「依赖插件生态」（官方见 <https://opencode.ai/docs/agents/>）：
>   - 内置三个 subagent：**General、Explore、Scout**；General 的描述逐字为「A general-purpose agent… Has full tool access (except todo)… Use this to run multiple units of work in parallel.」
>   - 另有 `Task` 工具、`permission.task` 权限项、子会话导航（`session_child_first` / `child_cycle` / `parent`）与 agent steps 上限。
> - **改写口径**：两边都已有原生并行子智能体；上表四个第三方方案是**补充控制通道**（消息注入、实时状态、abort 等），不是「OpenCode 缺原生能力」的替代品。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 补疏漏 | 全文（定义/适用条件/防冲突/汇总）未提及子智能体返回值会被截断，默认按「一次性并行分发 → 汇总结果」直接使用回传内容 | 「定义」节新增截断警示与三条处置（只回结论+证据指针、长产物落盘、完整性验收）；依据 issue [#17208](https://github.com/anthropics/claude-code/issues/17208) / [#27483](https://github.com/anthropics/claude-code/issues/27483)，并标明 30K 属**社区证据/变更记录转引**、非现行官方条款 |
| 补疏漏 | 「OpenCode 生态方案」表用「并行上限」列，但全文没有 Claude Code 侧的并行上限 | 「适用条件」节补三道闸门表（并发 20 / 嵌套深度按版本 5→1→3 / description 总量 15,000 token 告警）与 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`、`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`；依据官方 <https://code.claude.com/docs/en/sub-agents> |
| 纠错 | 「Ephemeral Team \| 原生 team() (提案中) \| 可配置」把已终结的提案当作候选方案 | 表内保留原表述并加警示；表下更正块给出 issue #19999（closed / not planned）与 PR #20152（merged=false）证据 |
| 纠错 | 「OpenCode 依赖插件生态」的后半句已过时 | 「Claude Code 对比」节加更正块：OpenCode 已原生内置 General / Explore / Scout 三个 subagent 与 Task 工具、`permission.task`、子会话导航；依据 <https://opencode.ai/docs/agents/>。前半句同时收紧为「前后台由 fork 模式决定，`run_in_background` 是 Bash 工具参数」 |
| 加厚 | 「OpenCode 生态方案」四行只有名称/机制/上限三列，无仓库链接、无版本、无核验日期 | 表增「来源与核验（2026-09-13）」列：agent-intercom 落到 feanor5555/opencode-agent-intercom 与官方 description 逐字；另两行明确标「待补」并写明需锁版本/commit 与「并行上限」测法 |
| 加厚 | 「适用条件」「防冲突」两节只有断言，无一维判据与失败模式 | 「适用条件」补规模判据与失败模式清单（超时/部分失败/返回值截断/写冲突/被并发上限拒绝）；「防冲突」补汇总规则表（交叉验证 k 次阈值、去重键、冲突裁决、部分失败三态统计） |

回链：[[CORRECTIONS]] · [[AGENTS]]
