---
title: 状态机式质量门控回环
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-07-01
updated: 2026-09-13
status: stable
---

# 状态机式质量门控回环

> [!abstract] 状态机式质量门控反馈回环 — 多智能体系统可靠性控制的核心模式

See also: [[Claude-Ops-KB-Home]] · [[fan-out-subagent-pattern]] · [[opencode-multi-agent-architecture]] · [[main-subagent-realtime-interaction]]

## 仓库
https://github.com/L-ingqin12/opencode-multi-agent-system

## 核心设计

7 个状态: START → ANALYZE → DELEGATE → VERIFY → INTEGRATE → DONE + ESCALATE（超限上报终态）
2 个分支: RETRY (携带反馈回环) + ESCALATE (超限上报)

> [!note] 勘误 (2026-08-25): 原文标注 7 个状态但列表仅列 6 个；按本文档的 ESCALATE 分支补入超限上报终态。上游仓库 (L-ingqin12/opencode-multi-agent-system) 当前不可达，第 7 状态名待原作者确认。
>
> **2026-09-13 结案（上面这段的「不可达 / 待确认」已作废，原文保留供追溯）**：
> 上游仓库现**公开可达**——GitHub API 逐字：`private=false`、`archived=false`、`default_branch=master`、`created_at=2026-07-04T07:02:53Z`、`pushed_at=2026-07-04T12:33:50Z`，description「OpenCode多智能体协作系统: 1主Orchestrator+6专业子智能体」；第 7 状态名由上游文件逐字确认为 **ESCALATE**。
> 上游「状态机总览」逐字：`START → ANALYZE → DELEGATE → VERIFY → INTEGRATE → DONE`，另有 **RETRY**（携带 feedback 的回环）与 **ESCALATE**（retry ≥ 3 的终态）。
> 核验依据：<https://api.github.com/repos/L-ingqin12/opencode-multi-agent-system> · <https://raw.githubusercontent.com/L-ingqin12/opencode-multi-agent-system/master/.opencode/agent/orchestrator.md>
> 另附上游硬约束原文（供复核）：每个子任务 `maxRetries = 3`、全局总轮次 `maxTotalRounds = 10`、同一失败连续 `sameFailureThreshold = 2` → 强制 ESCALATE、RETRY 后输出与上一轮完全相同 → 直接 ESCALATE、进入第 4 次 RETRY → ESCALATE。

## 关键规则
- 每个子任务独立状态机，一个 RETRY 不阻塞其他
- 质量门: syntax/completeness/consistency/no_hallucination/specificity/actionable
- 重试上限 3 次，同一失败连续 2 次 → ESCALATE
- 总轮次上限 10，防止无限循环
- 与 Fan-Out 组合: 并行分发 + 每个任务独立回环

> [!warning] 更正（2026-09-13）：质量门实际是 **7 个**，漏了 `GATE:file_check`（原表述为上面第 2 条，只列 6 项）
> 上游 `orchestrator.md` 的 VERIFY 节分两张清单——**代码生成类**：`syntax` / `completeness` / `consistency` / `no_hallucination`；**分析类**：`specificity` / `actionable` / `file_check`；去重后共 **7 个门**。
> 漏掉的正是最后一项：**`GATE:file_check — 引用的文件路径是否真实存在？`** 缺它会放过「行号对、但没有这个文件」的幻觉——这类错误人工最难发现。
> 依据：<https://raw.githubusercontent.com/L-ingqin12/opencode-multi-agent-system/master/.opencode/agent/orchestrator.md>

### 状态转移表（2026-09-13 补）

原「2 个分支: RETRY + ESCALATE」只有名字，没有守卫条件与产物。上游已给出可直接引用的判定规则：

| 当前态 | 触发 | 守卫 | 下一态 | 产物 | 失败模式 |
|--------|------|------|--------|------|----------|
| VERIFY | 7 个门全部通过 | — | INTEGRATE | 带门结果的验证报告 | 门本身没跑（把「没报错」当通过） |
| VERIFY | 仅 WARNING 级问题 | 无 BLOCKER | INTEGRATE | 验证报告 + WARNING 清单 | WARNING 被静默丢弃 |
| VERIFY | 出现 BLOCKER | retry < 3 且 同失败连续 < 2 | RETRY | feedback（具体到门与行） | feedback 太笼统导致重试空转 |
| VERIFY | 出现 BLOCKER | retry ≥ 3 或同失败连续 ≥ 2 或进入第 4 次 RETRY | ESCALATE | 未解决问题清单 + 已完成部分 | 只上报失败、不报已完成部分 |
| RETRY | 重新产出与上一轮**完全相同** | — | ESCALATE | 两轮输出 diff | 无进展的重试耗光轮次 |
| DELEGATE/VERIFY | 全局轮次达 `maxTotalRounds = 10` | — | ESCALATE | 轮次台账 | 无限循环 |

> [!tip] 验收口径
> 表的每一行都应有一个可复现的负向用例（例如「仅 WARNING → 必须进入 INTEGRATE 而不是 RETRY」「同失败第 2 次 → 必须 ESCALATE」）。只写状态名不算可执行，能被用例判定的状态机才算。

## 实现路径
A) 纯 System Prompt (当前可用，依赖 LLM 自律)
B) Hook 插件 (推荐，opencode hook 强制执行)
C) Workflow Engine (等待原生 Ephemeral Team API)

> [!warning] 更正（2026-09-13）：路径 C 的等待对象已不存在，只剩 A/B 两条路（原表述为上面 C 行）
> - opencode issue [#19999](https://api.github.com/repos/anomalyco/opencode/issues/19999)「[FEATURE]: Ephemeral Sub-Agent Teams (parallel multi-agent orchestration)」：`state=closed`、`state_reason=not_planned`；对应实现 PR [#20152](https://github.com/anomalyco/opencode/pull/20152)：`merged=false`、`state=closed`。**「等待原生 Ephemeral Team API」永远等不到**，C 应改写为「已排除（上游 not planned）」。
> - 因此 **A / B 是仅有的两条路**；B 的落点用 opencode **原生**能力即可，不必另找插件：内置 subagent（General / Explore / Scout）、agent steps 上限、plugin hook 链（见 <https://opencode.ai/docs/agents/>）。
> - 若未来上游重启该提案，需重新取证后再把 C 加回，不能凭记忆恢复。

## 相关记忆
- [[opencode-multi-agent-architecture]]
- [[fan-out-subagent-pattern]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 补疏漏 | 「质量门」只列 6 项，上游 orchestrator.md 实为 7 个门，漏了 `GATE:file_check` | 「关键规则」保留原 6 项并加更正块，补出上游两张清单（代码生成类 4 + 分析类 3，去重 7）与 `file_check` 的作用；依据上游 raw 文件 |
| 纠错 | 「勘误 (2026-08-25)」称上游仓库不可达、第 7 状态名待确认，已过期 | 加「2026-09-13 结案」块：GitHub API 显示仓库 public/未归档，第 7 状态名为 ESCALATE；附上游状态机总览与硬约束原文，依据仓库 API + orchestrator.md |
| 纠错 | 同一勘误自相矛盾：前文已列 ESCALATE，勘误又说「第 7 状态名待原作者确认」 | 结案块明确该句作废并保留原文供追溯；第 7 状态名由上游裁定为 ESCALATE |
| 纠错 | 「C) Workflow Engine (等待原生 Ephemeral Team API)」的等待对象已不存在 | 「实现路径」保留 C 行并加更正块：issue #19999 not planned、PR #20152 merged=false；C 改判「已排除」，A/B 明确为仅有的两条路，B 的落点补 opencode 原生 subagent / steps / plugin hook |
| 加厚 | 「2 个分支: RETRY + ESCALATE」及实现路径只有名字，缺状态转移表与门控判定规则 | 新增「状态转移表」六行（当前态｜触发｜守卫｜下一态｜产物｜失败模式），含 WARNING 直通 INTEGRATE、同失败连续 2 次 ESCALATE、无进展 RETRY ESCALATE、`maxTotalRounds=10`；并附负向用例验收口径 |

回链：[[CORRECTIONS]] · [[AGENTS]]
