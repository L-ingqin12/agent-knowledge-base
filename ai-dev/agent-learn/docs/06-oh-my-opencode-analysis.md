---
title: oh-my-opencode Agent 架构深度拆解
aliases: [oh-my-opencode 拆解, OMO 架构分析, 三层 Agent 架构]
tags: [ai, ai/learning, ai/agent]
created: 2026-09-12
updated: 2026-09-13
status: review
---

# oh-my-opencode Agent 架构深度拆解

> 基于 v4.2.0 版本分析 (~2,165 TS 文件, ~314k LOC)

> [!warning] 更正（2026-09-13）：这是 **v4.2.0 历史快照**，原文未标快照日期。上游仓库已更名为 **oh-my-openagent**（`code-yeongyu/oh-my-openagent`，官网 <https://omo.dev>），release 线为 `v5.0.0-beta.62`（`created_at` 2026-09-13，target `dev`，安装命令 `npm i -g omo-ai@beta`），git tag 至少到 `v4.5.12`（该 tag 的 `package.json` 自报 4.5.12），npm 包 `oh-my-opencode` 仍在发 4.x（latest 4.19.4）；npm 的 bin 字段同时提供 `omo` / `lazycodex` / `lazycodex-ai` / `oh-my-opencode` / `oh-my-openagent` 五个别名，上游 AGENTS.md 自述「dual-published as oh-my-openagent during the rename transition」。原文全文只用 `oh-my-opencode` 一名，未提更名、新 CLI 名与官网。
> 计数口径：按 tag v4.2.0 源码归档实测 blob 2,470 个、其中 `.ts/.tsx` 2,117（原文 ~2,165 差约 2%）；**~314k LOC 无法由公开元数据复核，维持 unverifiable**——引用前请自行统计并附口径（如 `tar -tzf v4.2.0.tar.gz | grep -c '\.tsx\?$'`，并注明是否含 `.test.ts`）。
> 上游 dev 分支 AGENTS.md 自报 snapshot `f3642fcd` / Release v5.0.0-beta.18（Generated 2026-08-24），并在顶部警告全库正在做 multi-harness（OpenCode / Codex / Pi / Senpi）重构——本页结论需按该背景理解。
> 来源：<https://api.github.com/repos/code-yeongyu/oh-my-openagent/releases/latest> · <https://api.github.com/repos/code-yeongyu/oh-my-openagent/tags?per_page=100> · <https://cdn.jsdelivr.net/gh/code-yeongyu/oh-my-openagent@v4.5.12/package.json> · <https://registry.npmjs.org/oh-my-opencode/latest> · <https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md>

---

## 1. 整体架构：三层金字塔

```
                        ┌─────────────────┐
                        │   IntentGate     │  ← 关键词检测，意图路由
                        │  (Tier 1: 入口)  │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ↓                  ↓                   ↓
        ┌──────────┐      ┌──────────┐       ┌──────────┐
        │ Sisyphus │      │Prometheus│       │  Atlas   │  ← Tier 2: 主编排器
        │(Opus 4.7)│      │(Opus 4.7)│       │(Sonnet)  │
        └────┬─────┘      └────┬─────┘       └────┬─────┘
             │                 │                   │
             └─────────┬───────┴───────────────────┘
                       ↓
    ┌──────────────────┼──────────────────────────┐
    ↓                  ↓                           ↓
┌────────┐    ┌─────────────┐            ┌──────────────┐
│ Oracle │    │  Explore     │            │ Sisyphus-    │  ← Tier 3: 专项子Agent
│(GPT5.5)│    │ (GPT5.4mini) │            │   Junior     │
│ 架构审查│    │  代码探索     │            │  任务执行者   │
└────────┘    └─────────────┘            └──────────────┘
```

**Tier 1 — IntentGate**：关键词匹配分发（ultrawork/search/analyze/team）
**Tier 2 — 主编排器**：Sisyphus(统筹), Prometheus(规划), Atlas(执行), Hephaestus(自主开发)
**Tier 3 — 专项子Agent**：Oracle(审查), Explore(探索), Librarian(文档), Metis(差距分析), Momus(验证)

> [!warning] 更正（2026-09-13）：上图 Tier 2 只画了 3 个盒子（Sisyphus / Prometheus / Atlas），正文却写 4 个——**Hephaestus 未入图**；名册同时漏了 **Multimodal-Looker**（原文只在第 5 节工具表提 `look_at`）。上游 dev 分支自述 11 agents / 10 个 `createXXXAgent` 工厂（Prometheus 特例化）。

**上游 Agent 名册（2026-09-13 核对，共 11 个）**：

| 装配位置 | Agent | 备注 |
|---------|-------|------|
| `builtin-agents.ts`（实测装配 10 个） | sisyphus / oracle / librarian / explore / multimodal-looker / metis / atlas / momus / hephaestus / sisyphus-junior | `multimodal-looker` 为原文遗漏项（硬拒名单亦含它）；`sisyphus-junior` 原图有画、正文名册未列 |
| `agents/prometheus/`（独立） | prometheus | 上游按 special-cased 工厂处理（`index.ts` → `./system-prompt`） |

模型族硬约束 hook 亦实测存在：`hooks/no-sisyphus-gpt`（`createNoSisyphusGptHook`）与 `hooks/no-hephaestus-non-gpt`（`createNoHephaestusNonGptHook`）——原文讨论「硬编码 Agent → 模型映射」时遗漏了这一层。
来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md> · <https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/packages/omo-opencode/src/agents/builtin-agents.ts> · <https://cdn.jsdelivr.net/gh/code-yeongyu/oh-my-openagent@dev/packages/omo-opencode/src/agents/prometheus/index.ts>

---

## 2. Agent 定义模式：角色 + 能力 = Agent

每个 Agent 是一个强类型的 TypeScript 对象，核心字段：

```
Agent = {
    name: string              // 唯一标识
    role: "primary" | "subagent" | "all"  // 角色层级
    model: ModelSpec          // 默认模型 + 降级链
    tools: Tools[]            // 可用工具集（角色决定）
    systemPrompt: string      // 行为定义
    category?: CategoryName   // 子Agent分类路由
}
```

**关键设计**：
- `primary` agent 尊重 UI 模型选择 → 用户可控
- `subagent` agent 忽略 UI 选择 → 固定低成本模型确保一致性
- `all` agent 两种上下文都可用

---

## 3. Hub-and-Spoke 委托模型

这是 oh-my-opencode 最核心的架构模式：

```
                    ┌──────────────┐
                    │  Primary     │
                    │  Agent (Hub) │
                    └──┬───┬───┬──┘
                       │   │   │
          ┌────────────┘   │   └────────────┐
          ↓                ↓                ↓
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │call_omo_ │    │  task    │    │ backgrnd │
    │ agent    │    │(category)│    │ manager  │
    │(同步直接) │    │(分类路由) │    │(并发控制) │
    └──────────┘    └──────────┘    └──────────┘
```

### 三种委托机制：

| 机制 | 用途 | 目标 |
|------|------|------|
| `call_omo_agent` | 同步直接调用 | Explore, Librarian(只读) |
| `task` (delegate-task) | 分类路由 | Sisyphus-Junior(按分类) |
| BackgroundManager | 后台并发 | 最多 5 并行, 分类感知 |

### 8 个内置任务分类：

| 分类 | 模型（上游 dev 现况） | 用途 |
|------|------|------|
| visual-engineering | anthropic/claude-fable-5-1 (max) | 前端, UI/UX |
| ultrabrain | openai/gpt-6-astra (max) | 复杂逻辑, 架构 |
| deep | openai/gpt-6-astra (high)，带 `requiresModel` 闸门 | 自主研究+执行 |
| artistry | anthropic/claude-fable-5-1 (max) | 创意 |
| quick | kimi-for-coding/kimi-for-coding-highspeed | 拼写修复, 琐碎任务 |
| unspecified-low | xai/grok-4.6 (xhigh) | 中等范围 |
| unspecified-high | openai/gpt-6-astra (high) | 高强度通用 |
| writing | anthropic/claude-fable-5-1 (medium) | 文档, 写作 |

> [!warning] 更正（2026-09-13）：8 个分类**名称与数量未变**，但**模型映射整体换代**。原 v4.2.0 快照映射为：visual-engineering=`gemini-3.1-pro`、ultrabrain=`gpt-5.5 (xhigh)`、deep=`gpt-5.5`、artistry=`gemini-3.1-pro`、quick=`gpt-5.4-mini`、unspecified-low=`claude-sonnet-4-6`、unspecified-high=`claude-opus-4-7`、writing=`gemini-3-flash`。
> 上游实现口径：分类按 provider 拆成三套内置集合（`GOOGLE_CATEGORIES` 2 条 + `OPENAI_CATEGORIES` 5 条 + `KIMI_CATEGORIES` 1 条 = 8 条），由 `builtin-categories.ts` 统一合并；各分类带 `promptAppend` / `resolvePromptAppend` / `callerGuidance`，`deep` 另有 `BUILTIN_CATEGORY_REQUIRES_MODEL` / `GPT_FLAGSHIP_GATE_MODELS` 闸门。
> 来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/packages/omo-opencode/src/tools/delegate-task/builtin-categories.ts> · <https://cdn.jsdelivr.net/gh/code-yeongyu/oh-my-openagent@dev/packages/omo-opencode/src/tools/delegate-task/google-categories.ts> · <https://cdn.jsdelivr.net/gh/code-yeongyu/oh-my-openagent@dev/packages/omo-opencode/src/tools/delegate-task/openai-categories.ts> · <https://cdn.jsdelivr.net/gh/code-yeongyu/oh-my-openagent@dev/packages/omo-opencode/src/tools/delegate-task/kimi-categories.ts>

---

## 4. 两阶段规划-执行工作流

### Phase 1: 战略规划
```
用户意图 → Prometheus(访谈用户) → Metis(差距分析)
                                    ↓
                              Momus(验证计划)
                                    ↓
                          .omo/plans/<timestamp>-<title>.md
```

### Phase 2: 执行
```
/start-work → .omo/boulder.json 创建
                    ↓
Atlas 读取计划 → 按分类拆解任务 → 分配给 Sisyphus-Junior
                    ↓
         并行执行 (最多 5 concurrent)
                    ↓
    积累智慧到 .omo/notepads/<category>.md
```

> [!warning] 更正（2026-09-13）：运行时状态已从 `.sisyphus/` 迁到 **`.omo/`**（原文三处写 `.sisyphus/plans/...`、`.sisyphus/boulder.json`、`.sisyphus/notepads/...`）。上游原文：「Runtime state migrated from .sisyphus/ → .omo/. Legacy .sisyphus/ still exists during transition; packages/omo-opencode/src/shared/legacy-workspace-migration.ts copies it forward on first load.」
> dev 分支归档实测存在 `.omo/plans`、`.omo/rules`、`.omo/drafts`、`.omo/evidence`——**未见 `notepads` 子目录**，该叶子名请以实际工作区为准。Boulder 机制仍在：独立包 `packages/boulder-state`（`src/plan-checklist.ts`、`src/storage/plan-progress.ts`、`src/storage/read-state.ts`，npm workspace `@oh-my-opencode/boulder-state`）。
> 来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md> · <https://codeload.github.com/code-yeongyu/oh-my-openagent/tar.gz/refs/heads/dev>

---

## 5. Tool 系统：三层配置门控

| 类别 | 数量 | 工具 |
|------|------|------|
| Always On | 12（+8 个 `lsp_*` 别名 = 20） | grep, glob, session_list/read/search/info, background_output/cancel, call_omo_agent, task, skill, skill_mcp |
| Conditional | +1 ~ +26 | look_at +1、interactive_bash +1、monitor_* +4、task_* +4、edit(hashline) +1、team_* +12、goal_* +3 |
| 合计 | 12 ~ 38 | 上游自述「12-38 registry tools」 |

> [!warning] 更正（2026-09-13）：原表写「Always On 20 / Conditional +1~12」。上游现行口径为「12-38 registry tools」：Always on 明列 **12 个**，另 8 个 `lsp_*` 别名由内置 lsp MCP 提供——原文的 20 很可能就是 12 + 8（即原文写的 LSP(6) + AST-grep(2)）的另一种算法。真正过时的是 Conditional「+1~12」：它漏掉 `monitor_*`(+4) 与 `goal_*`(+3)，且与最多 +26 的条件项不符。工具目录实测 15 个，剔除 `shared/` 后恰为 14 个（background-task、call-omo-agent、delegate-task、glob、grep、hashline-edit、interactive-bash、look-at、monitor、session-manager、skill、skill-mcp、slashcommand、task）。
> 来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md> · <https://codeload.github.com/code-yeongyu/oh-my-openagent/tar.gz/refs/heads/dev>

### Hashline 编辑系统（关键创新）

```
文件内容每行带 hash 标记:
  LINE#a1b2c3: import os
  LINE#d4e5f6: def main():
  LINE#g7h8i9:     pass

编辑时验证 hash:
  old_string → 计算 hash → 与文件中的 hash 对比
  → 匹配: 应用编辑
  → 不匹配: 拒绝（文件已被修改）
```

---

## 6. 生命周期 Hook 系统（54-62 个）

| 层级 | 数量 | 职责 |
|------|------|------|
| Session | 24 | 会话生命周期 |
| ToolGuard | 18 | 工具执行前后的守卫 |
| Transform | 8 | 消息/prompt 转换 |
| Continuation | 7 | Todo 强制, 自动续行 |
| Skill | 2 | Skill 专用 |
| **合计** | **59 组合槽位**（默认配置激活 54；team 61 / monitor 62） | 上游口径「~54-62 lifecycle hooks (54 base / 61 team / 62 monitor)」 |

> [!warning] 更正（2026-09-13）：原表写 ToolGuard `16+1`、Transform `5+2`（两层各比上游少 1），标题上限 `61` 应为 `62`；Session 24 / Continuation 7 / Skill 2 与上游一致。
> 两处澄清：①第 8 节 TL;DR 的「54 个 Hook」正是**默认配置下的激活值**，不是区间下限；②原分层小计 24+17+7+7+2=57 落在区间内、并不自相矛盾，真正的问题是**分层口径与上游不一致**。
> 对照：2026-01-25 生成的 fork `sodam-ai/oh-my-opencode` AGENTS.md 仍只写 31 lifecycle hooks、20+ tools、10 agents——引用旧版二手文档会得到完全不同的数字。
> 来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md> · <https://raw.githubusercontent.com/sodam-ai/oh-my-opencode/dev/AGENTS.md>

**Todo Enforcer**：Agent 半途退出时强制续行 — "让 Sisyphus 永远推石头"
**Comment Checker**：阻止 AI 废话注释（`// @allow` 可绕过）

---

## 7. 可演进的架构优化方向

### 当前架构的挑战：

| 问题 | 影响 |
|------|------|
| 关键词路由 IntenGate 脆弱 | 无法理解语义意图 |
| 硬编码 Agent → 模型映射 | 无法根据任务自适应选模型 |
| Hub-and-Spoke 但无反馈回路 | 子Agent 错误不会反向优化计划 |
| 分类是静态枚举 | 无法处理混合/边界任务 |
| 并行度固定(5) | 无法根据任务特征动态调整 |

### 演进路线（**本文建议**，非上游路线图）：

```
当前 v4.2（快照）    →    本文建议（作者推演）
─────────────────────────────────────────────
静态关键词路由      →   语义嵌入 + 分类器路由
固定模型映射        →   动态模型路由(成本/能力自适应)
Hub-and-Spoke       →   网状协作(Federated)
静态分类枚举        →   自动分类推理
固定并行度          →   自适应并发策略
单向委托            →   双向反馈 + 计划修正
```

> [!warning] 更正（2026-09-13）：上表六条是**本文作者的推演**，原文标成「当前 v4.2 → v5.0 演进方向」，属把推断写成了上游事实。上游 `ROADMAP.md` 实际目录为 What This Is / Current Priority: Package Layering Refactor / Architecture Direction / Multi-Harness Support (Exploratory) / Why Not OpenCode-Native / Non-Goals / Decision Principle——**没有**语义嵌入分类器路由、联邦网状协作、自动分类推理等条目。
> 上游现况补充：Team Mode（parallel multi-agent coordination）**已实现但默认关闭**；`Why Not OpenCode-Native` 点名 `session.prompt` 提前返回、多个 hook 争抢同一 idle/error 边沿导致重复注入与死循环；PR 必须以 `dev` 为目标（`PRs targeting master are hard-blocked — they MUST target dev`）。
> 来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/ROADMAP.md> · <https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md>

---

## 8. 关键技术净值 (TL;DR)

| 值得借鉴 | 谨慎参考 |
|---------|---------|
| 三层 Agent 分层 | 关键词路由 (应升级为语义路由) |
| Hashline 编辑系统 | 硬编码模型映射 |
| 规划-执行分离 | 静态分类 |
| Todo Enforcer 机制 | Array.prototype 补丁 (hack) |
| 分类模型选择 | 54 个 Hook（默认配置激活值，过多） |
| MCP 三层体系 | 强依赖 Bun 运行时 |

---

## 运行前提、失败模式与降级链（2026-09-13 补）

> 原文只描述静态结构，没有运行前提、失败模式与降级链的边界条件；本节按上游 AGENTS.md 与 hook 源码补齐。

| 维度 | 事实 |
|------|------|
| 运行前提 | 早期 AGENTS.md 写 OpenCode「Requires >= 1.0.150」；v5 线安装 `npm i -g omo-ai@beta`；仓库纪律 `PRs targeting master are hard-blocked — they MUST target dev` |
| 失败模式 ① | `hooks/runtime-fallback/first-prompt-watchdog.ts`：subagent 会话静默超时后触发 fallback / abort；`constants.ts` 中 `DEFAULT_FIRST_PROMPT_WATCHDOG_MS = 90_000`（90 秒） |
| 失败模式 ② | `hooks/unstable-agent-babysitter`（`createUnstableAgentBabysitterHook`）：处理不稳定子 Agent |
| 降级链 | AGENTS.md 记有**两个互不集成**的 fallback 系统：`model-fallback`（主动）/ `runtime-fallback`（反应式）——选型时必须知道两者不会互相兜底 |
| 门控后果 | `team-mode`、`goal` 等开关把工具从 12 拉到 38、hook 从 54 到 61/62；Team Mode 默认关闭 |

来源：<https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/AGENTS.md> · <https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/packages/omo-opencode/src/hooks/runtime-fallback/first-prompt-watchdog.ts> · <https://raw.githubusercontent.com/code-yeongyu/oh-my-openagent/dev/packages/omo-opencode/src/hooks/runtime-fallback/constants.ts> · <https://raw.githubusercontent.com/sodam-ai/oh-my-opencode/dev/AGENTS.md>

## 相关文档

- [[LLM-Agent开发基础]] — 对照单 Agent 基础架构理解三层编排
- [[Agent-Skills技能开发实战]] — OMO 生态中的 Skill 机制
- [[MCP协议开发实战]] — 文中「MCP 三层体系」的协议基础
- [[07-reasonix-architecture-analysis]] — 本系列另一篇架构拆解（缓存优先）

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 版本口径停在 v4.2.0，未提更名、新 CLI 与官网 | 标题下加更正块：标为 v4.2.0 历史快照 + 上游现况（v5.0.0-beta.62 / `omo-ai@beta` / tag ≥ v4.5.12 / npm 4.19.4 / omo.dev / bin 五别名）；依据 GitHub releases·tags·raw AGENTS.md 与 npm registry |
| 纠错 | 计数标注「~2,165 TS 文件 / ~314k LOC」无口径 | 补统计口径（tag v4.2.0 实测 blob 2,470、`.ts/.tsx` 2,117）；LOC 标 unverifiable 并给出可复现命令 |
| 纠错 | 第 3 节分类模型映射为 v4.2 快照 | 按上游 dev 三个 `*-categories.ts` 实测更新 8 条映射，原映射保留在更正块中 |
| 纠错 | 第 4 节运行时路径写 `.sisyphus/` | 改为 `.omo/`，注明 legacy `.sisyphus/` 仍在迁移中及其迁移文件；`notepads` 叶子名标为待确认 |
| 纠错 | 第 5 节「Always On 20 / Conditional +1~12」 | 改为 12（+8 `lsp_*` = 20）/ +1~+26 与上游「12-38 registry tools」口径 |
| 纠错 | 第 6 节 Hook「54-61」与分层 16+1 / 5+2 | 改为 54-62，分层 18 / 8，注明 59 组合槽位与默认激活 54；澄清 TL;DR 的「54」不是区间下限 |
| 纠错 | 第 7 节把作者推演标为「v5.0 演进方向」 | 改标「本文建议（作者推演）」，附上游 ROADMAP 实际目录与 Team Mode 现状 |
| 缺覆盖 | 第 1 节 Agent 名册漏 Multimodal-Looker，图缺 Hephaestus | 补 11 Agent 名册表、图文不一致更正与两个模型族硬约束 hook |
| 缺覆盖 | 全文无运行前提、失败模式与降级链 | 新增「运行前提、失败模式与降级链」节（OpenCode 版本前提、90 秒 first-prompt watchdog、两个互不集成的 fallback 系统、门控后果） |

外部来源已登记至 `sources/learning-notes.md`。

> 回链：[[CORRECTIONS]] · [[AGENTS]]
