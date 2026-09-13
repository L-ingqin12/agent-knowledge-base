---
title: "Claude Code 记忆机制源码级拆解"
aliases: [CLAUDE.md记忆机制, Memory机制拆解, Claude Code记忆系统]
tags: [ai/agent, ai/learning]
created: 2026-06-02
updated: 2026-09-13
status: stable
source: "微信公众号"
source_urls:
  - "https://mp.weixin.qq.com/s/CLIuogpYSPng2brQph7AHg"
  # canonical（可长期访问的原文出处，2026-09-13 补录；微信为分发渠道）
  - "https://xiaolinnote.com/claudecode/source/cc_memory.html"
author: "小林coding"
date: "2026-06-02"
fetched_at: "2026-06-22"
---

# Claude Code 记忆机制源码级拆解

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[上下文工程落地实践-从理论到Claude-Code实现]] | [[Skill规模化管理-从渐进式披露到检索式发现]] | [[Agent韧性架构分析-微信转载]]

## 摘要

Claude Code 的记忆机制分两层并行工作：（1）**静态层**——CLAUDE.md 六层级声明式指令体系，叠加 @include 引用和条件规则的按需注入；（2）**动态层**——自动记忆系统，在每轮对话结束后由后台 ExtractMemories 代理抽取用户画像/行为偏好/项目动态/外部指针四类信息，落盘为结构化 markdown 文件，下次会话由 Sonnet 从 MEMORY.md 索引中选 top-5 注入上下文，2 天以上的记忆主动加 stale 警告并强制模型验证。

**核心反直觉设计**：不用向量数据库、不用 embedding，全用磁盘上的 markdown 文件 + LLM 做选择器。索引常驻（始终在 system prompt）、内容按需加载。四条可迁移原则：结构化优于自由文本、索引常驻+内容按需、小模型做选择题优于向量检索、时间感知+主动验证。

> [!info] 独立印证（2026-09-13）：该论断由两个独立来源确认——独立源码分析以 Absence 类证据记「No vector search, embeddings, or knowledge graph | Full source review of `src/memdir/` and related services | 0.95 | Confirmed absent from all memory-related code」；小林原文主线即「为什么不用向量数据库」，并给出「结构化文件 + LLM 选择」的对照论述。「廉价模型做选择题」这一可迁移原则亦被独立来源支持（Sonnet 选择器，0.95）。
> - 来源：[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md) · [小林coding — Claude Code 记忆机制图解](https://xiaolinnote.com/claudecode/source/cc_memory.html)

---

## 一、LLM 是无状态的——记忆幻觉的真相

LLM 本身无状态。每次对话，客户端把 system prompt + 全部历史 + 当前问题一起发送。模型看起来「记得」，是客户端偷偷重发了历史——这属于**短期记忆**（上下文窗口）。聊天场景每轮几百 token 能撑住，agent 场景几十轮 tool call 立即爆窗口。

Agent 真正需要的**长期记忆**（跨会话持久化）是四类：

| 类型 | 内容 | 示例 |
|------|------|------|
| 用户画像 | 用户是谁、擅长什么 | 「十年 Go 后端，刚接触 React」 |
| 行为偏好 | 用户喜欢/不喜欢什么 | 「不要用 mock，连真实数据库」 |
| 项目动态 | 项目正在发生什么 | 「移动端 3 月 5 号合并冻结」 |
| 外部指针 | 去哪查什么信息 | 「pipeline bug 在 Linear 的 INGEST 项目追踪」 |

类比：LLM 是失忆的实习生——聪明但每天从零开始。记忆机制 = 工位上的便签：贴在哪、谁来贴、什么时候撕。

---

## 二、四种主流方案及其共同病根

| 方案 | 原理 | 硬伤 |
|------|------|------|
| 滑动窗口 | 保留最近 N 轮，超出的丢弃 | 关键信息随旧消息一起被砍 |
| 对话摘要 | LLM 定期摘要旧对话塞回上下文 | 摘要压糊重要细节（"Kong 不是 nginx"→"技术栈细节"） |
| 向量检索（最热） | embedding → 向量数据库 → top-K 召回 | 相似≠相关；embedding 模型换一个全崩；用户无法看懂存储内容 |
| 分层存储 | core/recall/archival 三层，LLM 主动搬数据 | 搬数据依据仍是 embedding 召回，硬伤一个不少 |

**共同病根**：自由文本无约束、不区分类型、无老化机制、重检索轻写入。

---

## 三、Claude Code 的两层架构

### 静态层：CLAUDE.md 六层级

六种来源的规则，可见范围和修改权限不同，拆成独立层级：

| 层级 | 位置 | 管理者 | 用途 |
|------|------|--------|------|
| Managed | 系统路径 | 仅管理员 | 公司强制策略 |
| User | 家目录 | 用户本人 | 全局偏好，跨项目生效 |
| Project | 项目根目录 CLAUDE.md | Git 团队共享 | 项目级约定 |
| Local | CLAUDE.local.md | 用户本人 | 本地调试约定，不签入 git |
| Auto | 项目自动记忆目录 | Claude 自动写入 | 对话中学习的偏好 |
| Team | Auto/team/ | 团队共享 | 团队积累的 AI 经验（需 feature flag） |

> [!warning] 补（2026-09-13）：「Auto/team/ + 需 feature flag」的写法会让读者以为数据不出本机。独立分析的实测事实是：Team 层不是本地目录约定，而是**带服务端同步的子系统**——private + shared 记忆经 OAuth 鉴权的 delta 同步上传，上传前做 secret 扫描（`teamMemSecretGuard.ts`）；扫描器的覆盖面与误报率未知。关闭后同时失去团队共享记忆。
> - 来源：[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)（TL;DR 与证据 #7）

六层是**叠加关系**（非覆盖），启动时全部拼进 system prompt。

**子机制一：`@include`**——CLAUDE.md 中用 `@~/company/security-rules.md` 引用其他文件，类似 C 的 `#include`。防循环引用、防路径遍历。

**子机制二：条件规则**——`.claude/rules/` 下每条规则用 frontmatter 中的 `paths` glob 字段匹配当前编辑文件，匹配才注入。一个项目可定义几十条规则，每条只在需要时占用 token。

**子机制三：截断双保险**——MEMORY.md 索引同时受 `MAX_ENTRYPOINT_LINES = 200` 和 `MAX_ENTRYPOINT_BYTES = 25000` 限制，防「长行索引炸弹」（极端案例：197KB 不到 200 行）。

> [!info] 独立印证（2026-09-13）：独立分析逐字确认「MEMORY.md truncation at 200 lines / 25KB | Mechanism | Source code (`MAX_ENTRYPOINT_LINES`, `MAX_ENTRYPOINT_BYTES`) | 0.95 | Dual-cap with clear warning message」——**双上限**与**带明确告警**两点与本文一致。**197KB 的极端案例仍无第二来源**，标注为「原文案例，未独立核验」。
> - 来源：[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)

### 动态层：自动记忆系统闭环

#### 类型约束

只允许四种类型，强制 agent 写前做分类决策：

```typescript
export const MEMORY_TYPES = ['user', 'feedback', 'project', 'reference'] as const
```

`feedback` 和 `project` 有强制结构：正文 + **Why:**（为什么）+ **How to apply:**（何时生效）。只记规则不记原因，边界情况无法判断。

`project` 额外要求：相对日期转绝对日期（「周四前冻结」→「2026-03-05 前冻结」）。

**不该存清单**：代码模式/架构/路径（grep/CLAUDE.md 能推出来）、Git 历史（git log 是权威）、调试修复方案（已在 commit 中）、CLAUDE.md 已有内容、临时任务状态。纪律：**只记代码推不出来的东西。**

#### 存储：索引常驻 + 内容按需

每条记忆一个独立 `.md` 文件，YAML frontmatter 存 `name`/`description`/`type`。目录内一个 `MEMORY.md` 索引文件列出所有记忆的 name+description。

`MEMORY.md` → 始终加载进 system prompt（让模型知道有什么可用）  
独立记忆文件 → 真正需要时才加载完整正文

#### 写入：Extract Memories 后台代理

每轮 query loop 结束后通过 stopHook 触发，fork 主对话（复用 prompt cache 而非重新加载 system prompt）。逻辑：扫对话历史 → 与现有记忆比对去重 → 四类型分类 → 写入新文件。

> [!warning] 补与更正（2026-09-13）：原文把抽取 prompt 的**软约束**写成了系统行为，并漏了三条写入侧事实（独立源码分析，已取回）——
> 1. **并发边界**：主 agent 与后台抽取 agent 每轮互斥（`hasMemoryWritesSince`），并非「随时可 fork」；
> 2. **写入侧无内容门禁**：抽取 prompt 只说「don't duplicate」，**代码层没有**去重 / 垃圾过滤 / 合理性检查——原文「与现有记忆比对去重」是 prompt 级要求，不是代码级保证；
> 3. **覆盖式写入，无更正/版本语义**：是 overwrite 模型，不是 append-only corrections——写错只能覆盖，历史不可回溯。
> - 来源：[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)（证据 #2 / #9 / #10）

#### 检索：Sonnet 做选择题，不用向量检索

1. 扫描所有记忆文件前 30 行提取 frontmatter
2. 标题清单发给 Sonnet：「用户当前问题如下，哪些相关？不确定就别选」
3. Sonnet 用 JSON schema 返回 top-5 文件名

> [!info] 精确化（2026-09-13）：「top-5」这个上限**写在选择 prompt 里，不是解析代码里的硬编码常量**——独立分析记「Sonnet selector picks up to 5 relevant memories per query | Mechanism | Source code (`findRelevantMemories.ts`, `max_tokens: 256`) | 0.95 | Limit is in the prompt, not hard-coded in parsing」。引用时不宜说成硬编码常量。
> - 来源：[lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)

两道过滤：`alreadySurfaced`（上轮已出现的排除）、`recentTools`（正在用的工具文档排除，但工具的坑点保留）。

选择 Sonnet 而非 Haiku：记忆判错的代价（污染整条回复）>> 多花的 token 成本。

#### 注入与老化

```xml
<system-reminder>
This memory was saved 5 days ago. Verify it's still accurate before acting on it.
[记忆内容]
</system-reminder>
```

今天/昨天 → 不警告；2 天以上 → stale 警告。附加验证提示：「记忆说文件在路径 X，先检查文件是否存在」「记忆说函数叫 Y，先 grep 一下」——记忆不是真理，是历史快照。

> [!warning] 未能核验（2026-09-13）：「**2 天**」这个老化阈值只在本文与其 canonical 原文（小林coding）这一条链上出现，**无独立来源**，按库内标准标 unverifiable；数字源自原文，引用请注明核验日。

> [!success] 残余复核（2026-09-13 补录）：上一条「无独立来源」的判断**已被推翻**——独立源码分析 [lhl/agentic-memory — ANALYSIS-claude-code-memory.md](https://raw.githubusercontent.com/lhl/agentic-memory/a26d9df2e1f93cfc0a80900ccd98d25b681bef27/ANALYSIS-claude-code-memory.md)（本次经代理直取 HTTP 200）记：`memoryAge(mtimeMs)` 返回 "today / yesterday / N days ago"，`memoryFreshnessText()` 对**超过 1 天**的记忆注入 "This memory is N days old. Memories are point-in-time observations… Verify against current code before asserting as fact."——按整天粒度折算即「今天/昨天不警告、第 2 天起警告」，**与本节的「2 天」一致**，且验证提示语与本节的「先检查文件是否存在 / 先 grep 一下」同义。因此该阈值**有独立来源**，可摘掉 `unverifiable`，改标「两路独立源码分析一致」。
> 唯一仍未独立确认的是**注入的包裹形态**：本节写作 `<system-reminder>`，该独立分析只写「注入到 user context」（"Inject selected memories with staleness caveats into user context"），未见该标签。引用时建议写成「随记忆一并注入提醒文本（本库所记形态为 `<system-reminder>`，未经第二来源确认）」。

---

## 四、可迁移的设计原则

| 原则 | 内容 | 迁移方法 |
|------|------|----------|
| 结构化优于自由文本 | 强制类型 + frontmatter 约束 | 给记忆定 schema，哪怕 4 个字段也比无约束强 |
| 索引常驻 + 内容按需 | 索引始终在 system prompt，内容按需加载 | 适用于任何「总量大但只需少数展开」的场景 |
| 小模型做选择题 | 检索 = 自然语言判断，不是相似度数值 | 候选集 < 几百时，小模型选 > 向量检索 |
| 时间感知 + 主动验证 | 2 天 stale 警告，用前 grep 验证 | 记忆不是 ground truth，是历史快照 |

核心哲学：不堆复杂度，用文件系统 + LLM 组合出比向量检索更好用的系统。

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | frontmatter 只有微信一条 `source_urls`，无可长期访问的原文地址 | 增补 canonical `xiaolinnote.com/claudecode/source/cc_memory.html`（微信标注为分发渠道）；依据小林coding 原文页 |
| 纠错 | 把抽取 prompt 的**软约束**写成系统行为（「与现有记忆比对去重」） | 标注为 prompt 级要求、非代码级保证，并补三条写入侧事实（每轮互斥、无内容门禁、覆盖式写入无版本语义）；依据 lhl/agentic-memory 证据 #2 / #9 / #10 |
| 补疏漏 | Team 层只写「Auto/team/ + 需 feature flag」，易被读成数据不出本机 | 补服务端同步、OAuth 鉴权 delta 上传、上传前 secret 扫描（`teamMemSecretGuard.ts`）与关闭后的影响；依据同上证据 #7 |
| 纠错 | 「Sonnet 返回 top-5」易被读成硬编码常量 | 精确化为「上限写在选择 prompt 内」（`findRelevantMemories.ts`、`max_tokens: 256`）；依据独立源码分析 |
| 加厚 | 「不用向量数据库」与「截断双保险」两个关键论断缺独立出处 | 各补一条独立源码分析印证；197KB 极端案例标注「原文案例，未独立核验」 |
| 补疏漏 | 「2 天 stale 阈值」只有单一来源链 | 标注本库未能核验（unverifiable），引用需注明核验日 |
| 残余复核 | 上一条「2 天阈值无独立来源」的判断 | **已推翻并结案**：lhl/agentic-memory 独立源码分析（本次直取 200）记 `memoryAge` = today/yesterday/N days ago、`memoryFreshnessText()` 对 >1 天记忆注入 "This memory is N days old… Verify against current code"，与「2 天起警告」一致 → 该阈值有独立来源；残留仅 `<system-reminder>` 包裹形态未经第二来源确认 |

- 回链：[[CORRECTIONS]]｜[[AGENTS]]
