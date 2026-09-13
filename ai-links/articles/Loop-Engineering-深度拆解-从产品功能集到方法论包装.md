---
title: "Loop Engineering 深度拆解 — 从产品功能集到方法论包装"
aliases: [Loop Engineering, Addy Osmani, Loop方法论]
tags: [ai/agent, ai/learning]
created: 2026-06-25
updated: 2026-09-13
status: stable
source: "微信公众号"
source_urls:
  - "https://mp.weixin.qq.com/s/QXW2WbxjSDyOClg-PX2Sng"
author: "靳岩岩"
date: "2026-06-25"
fetched_at: "2026-06-25"
---

# Loop Engineering 深度拆解

See also: [[AI-Links-KB-Home]] | [[Articles-Index]] | [[Claude-Code记忆机制源码拆解]] | [[上下文工程-注意力预算与四层解法]] | [[Agent韧性架构分析-微信转载]]

## 摘要

2026 年 6 月，"Loop Engineering" 一词由 Google Chrome 工程主管 Addy Osmani 推上方法论位置。〔**2026-09-13 更正**：头衔过期——Addy 本人页脚自述为"长期在 Google 负责 Chrome 开发者体验，近年转向 AI（Gemini、编码 Agent、agentic engineering），最近任 Google Cloud AI Director"，详见「Loop 的四种定义对比」下的更正块。〕此前 Peter Steinberger（OpenAI）和 Boris Cherny（Anthropic Claude Code 负责人）已分别在社交媒体上使用 "loop" 一词。但深入对比发现：三个发明者对 "loop" 的定义互不一致，且 Loop Engineering 本质是 **Claude Code 2.1.139 功能集的外包装**——核心本体是 `/loop` 和 `/goal` 两个 slash command（共 10 字符），外围四件（git worktree、SKILL.md、MCP、sub-agents）全是支撑设施。〔**2026-09-13 更正**：两个命令**不是同一版本上线**——`/loop` 于 2.1.71（2026-03-07 UTC）引入，`/goal` 于 2.1.139（2026-05-11 UTC / 北京时间 05-12）引入，故"本质是 2.1.139 功能集的外包装"这一核心论断需修正：本体有一半来自 2 个多月前的 2.1.71。官方 release 正文逐字见下文「Claude Code 的 /loop 本体」一节。〕

Addy 的贡献不在于发明新技术，而在于为 AI 工程造了一套三层词汇表：**Context Engineering → Harness Engineering → Loop Engineering**，三者均对应早就存在的旧技术（prompt+RAG / sandbox+system prompt / cron+ReAct），但作为招聘 JD 和立项理由的词汇非常有效。〔**2026-09-13 更正**：该"三层架构表"与"招聘 JD"说法在 Addy 原文中检索不到（原文相关表述只有一句 "Loop engineering sits one floor above the harness."）；且 **harness engineering 一词不是 Addy 提出**——他在《Agent Harness Engineering》中写明 "Viv Trivedy coined the term _harness engineering_"。详见「Addy 的三层 AI 工程架构」一节更正块。〕

**核心洞见**：loop 不是工具，是放大器——它放大工程师已有的判断力和勤奋，也放大懒惰和认知投降。Karpathy 的 autoresearch（630 行 Python）是该理念的最小可用证明。〔**2026-09-13 更正**：代码量实为约 1,000 行 Python（train.py 630 行 + prepare.py 389 行）外加 program.md 114 行 Markdown，原"630 行"只等于 train.py 单文件。〕

---

## Loop 的四种定义对比

| 提出者 | 定义 | 本质 | 类比对象 |
|--------|------|------|----------|
| **Peter Steinberger** (OpenAI) | "design loops that prompt your agents" | 抽象修辞，表达抽象层级上移 | 一种"工程师姿态" |
| **Boris Cherny** (Anthropic) | 几百个 Claude 实例并行运行，读 GitHub issues/扫 Twitter/翻 Slack | 生产环境多实例编排 | cron + Claude + API |
| **Addy Osmani** (Google Chrome)〔头衔过期，见下方更正块〕 | "recursive goal where you define a purpose and the AI iterates until complete" | 单 agent 内部的目标驱动循环 | ReAct / AutoGPT |
| **Anthropic 官方** | "/loop: let the model self-pace"〔**2026-09-13 更正**：带引号的这个英文句子在官方 CHANGELOG 中检索不到，不应作为「官方措辞」引语——见下方更正块〕 | 产品功能——定时触发或自定节奏触发 slash command | 一个 slash command |

> [!warning] 更正（2026-09-13）：
> ① **「/loop: let the model self-pace」不是官方原话**。本次在 Anthropic 官方 CHANGELOG 中检索不到该句；可核实的官方措辞是 2.1.248 变更说明逐字为 "Changed `/loop`: self-paced dynamic mode and the no-prompt autonomous default are now always available, including on Bedrock/Vertex/Foundry"；官方文档用的是 "self-paced `/loop`"，并把该模式的小节题为「Let Claude choose the interval」。用带引号的「官方措辞」承载未经核对的句子，与本库头号错误来源「把现象当结论」同类，故改为转述或换成可核实原话。来源：https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md ，https://newreleases.io/project/github/anthropics/claude-code/release/v2.1.248 ，https://code.claude.com/docs/en/scheduled-tasks.md
> ② **Addy Osmani 头衔过期**：其站点页脚自述逐字为 "Addy Osmani is an engineering and evangelism leader who spent over 14 years at Google leading developer experience across Chrome and, in recent years, AI (Gemini, coding agents, and agentic engineering), most recently as a Director at Google Cloud AI."——「Chrome 工程主管」是旧头衔，最近职务是 Google Cloud AI 的 Director。该页脚在其 2026-04-19 / 2026-06-07 两篇原文中均已存在，早于本文 updated（2026-08-25），不属事后之明。建议表述：Addy Osmani（Google；长期负责 Chrome 开发者体验，近年转向 AI/agentic engineering，最近任 Google Cloud AI Director）。来源：https://addyosmani.com/blog/loop-engineering/ ，https://addyosmani.com/blog/agent-harness-engineering/
> ③ **可补一条可核实定义**：Addy 在后续《Practical Loop Engineering》(2026-08-14) 中逐字给出 "A loop is an autonomous, self-correcting feedback cycle where an agent repeatedly acts, tests its results and adjusts its approach until a specific goal is met"，并说明 goal 与 loop 两个原语的分工。来源：https://addyosmani.com/blog/practical-loop-engineering/

---

## Claude Code 的 /loop 本体

- **上线版本**: Claude Code 2.1.139 (2026-05-12)〔**2026-09-13 更正**：两个命令不是同一版本上线，原表述只对 `/goal` 成立。GitHub Release 数据：`/loop` 于 **v2.1.71**（published_at 2026-03-07T00:12:46Z）引入，正文逐字为 "Added `/loop` command to run a prompt or slash command on a recurring interval (e.g. `/loop 5m check the deploy`)"；`/goal` 于 **v2.1.139**（published_at 2026-05-11T18:43:42Z，即北京时间 2026-05-12）引入，正文为 "Added `/goal` command: set a completion condition and Claude keeps working across turns until it's met. Works in interactive, `-p`, and Remote Control." 第三方文章亦记录「Claude Code 2.1.71 introduit /loop」（frr.dev，2026-03-09）。〕
- **用法一**: `/loop 5m /foo` — 每 5 分钟触发一次 `/foo`
- **用法二**: `/loop`（不带 interval）— 模型自定节奏
- **官方措辞**: "let the model self-pace"〔**2026-09-13 更正**：该句在官方 CHANGELOG 中检索不到，不能作为引语。可核实的官方说法是 **"self-paced dynamic mode"**（2.1.248 变更说明）与 **"self-paced `/loop`"**，官方文档把该模式的小节题为「Let Claude choose the interval」。〕
- **别名**: `/proactive` 是 `/loop` 的别名（官方 CHANGELOG 2.1.105 变更说明）。
- **官方文档页**: `code.claude.com/docs/en/scheduled-tasks`（"Run prompts on a schedule"）与 `code.claude.com/docs/en/goal`（"Keep Claude working toward a goal"）——比引用 CHANGELOG 更稳的引用位。

来源：https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.71 ，https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.139 ，https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md ，https://newreleases.io/project/github/anthropics/claude-code/release/v2.1.243 ，https://claude-code-log.com/changelog/v2.1.105 ，https://code.claude.com/docs/en/scheduled-tasks.md

### 运行边界（2026-09-13 补录）

| 边界 | 内容 | 依据 |
|------|------|------|
| 依附会话 | 循环任务是**会话级**的："Tasks are session-scoped: they live in the current conversation and stop when you start a new one."；"Closing the terminal or letting the session exit stops them firing." | 官方文档 scheduled-tasks |
| 状态不恢复 | self-paced loop 在 resume 时不恢复；循环任务 7 天后自动过期；等待下一轮时按 Esc 会清除 pending wakeup | 官方文档 scheduled-tasks |
| 远程/容器场景受限 | CHANGELOG 2.1.172 逐字："Stopped promoting `/loop` in remote sessions, where pending loops don't keep the container alive" | 官方 CHANGELOG |
| 与 cron 的分工 | 官方另外给出「Routines / Desktop scheduled tasks / GitHub Actions」作为**脱离会话**的排程方案；第三方实测结论是它属于「会话内、临时任务的调度器，**不能替代 cron**」 | 官方文档 scheduled-tasks；frr.dev（2026-03-09） |

### 可观测性（2026-09-13 补录）

CHANGELOG 2.1.243 逐字："Added a Loops breakdown to `/usage`: per-loop run count, total tokens, tokens per run, and last run, so runaway or chatty `/loop` tasks are easy to spot"。
**验收判据**：在 `/usage` 里能看到该 loop 的运行次数与每轮 token——据此判断它是否 runaway（跑飞）或在空烧钱；这正是下文「三个工程坑」缺的监控手段。

---

## Addy 的五件套拆解

| 组件 | 是不是 loop？ | 来源 | 时间 | 实际作用 |
|------|--------------|------|------|----------|
| `/loop` + `/goal` | **是** — loop 本体 | Claude Code 2.1.139 | 2026-05-12 | 定时触发 or 递归目标直到完成 |
| git worktree | 不是 — 隔离机制 | Git 2.5 | 2015 | 并行 agent 的文件系统隔离 |
| SKILL.md | 不是 — 知识包 | Anthropic | 2025-10 | 项目规则按需注入 agent 上下文 |
| MCP | 不是 — 外部接口 | Anthropic | 2024-11 | agent 连接外部系统（Jira/Slack/DB） |
| Sub-agents | 不是 — 分工 | Anthropic | 2025 年中 | 独立 verifier agent 做验收 |
| STATE.md | 不是 — 记忆 | 附赠 | — | 跨 session 状态持久化 |

> [!note] STATE.md 不在 Addy「五件套」之列，是附赠的第 6 件——仅作跨 session 状态持久化补充，与 loop 本体无关。

> [!warning] 更正（2026-09-13）：上表的构成与「第六件」的说法**正好说反了**（原表保留以便追溯）。Addy 原文《Loop Engineering》(2026-06-07) 的清单逐字为：1. Automations（"that go off on a schedule and do discovery and triage by themselves"）、2. Worktrees、3. Skills、4. Plugins and connectors、5. Sub-agents；紧接着写 "Then the sixth thing, the memory. A markdown file, or a Linear board, anything that lives outside the single conversation and holds what's done and what is next."——**第六件就是 memory，且是被明确承认的第六件**，不是「附赠」。
> 另外两点归属修正：
> ① `/loop` 与 `/goal` 在该文对照表里属于**第 1 件 Automations 的 Claude Code 侧实现**（该行 Claude Code 列写的是 "Scheduled tasks and cron, `/loop`, `/goal`, hooks, GitHub Actions"），并不是一个独立的「loop 本体」条目；
> ② State 行的 Claude Code 列写的是 "Markdown (`AGENTS.md`, progress files) or Linear via MCP"——**Addy 从未写过 STATE.md 这个文件名**，应改写为「Markdown 进度文件（如 AGENTS.md、progress files）或 Linear 看板」。
> 按原文重排后的正确清单：

| 序 | Addy 原文的五件套 | 性质 | Claude Code 侧对应 |
|----|------------------|------|-------------------|
| 1 | Automations | 让 agent 按排程自己跑发现与分诊 | Scheduled tasks and cron、`/loop`、`/goal`、hooks、GitHub Actions |
| 2 | Worktrees | 隔离并行工作区 | git worktree |
| 3 | Skills | 按需注入的知识包 | SKILL.md |
| 4 | Plugins and connectors | 接外部系统 | MCP 及连接器 |
| 5 | Sub-agents | 分工与独立验收 | Sub-agents |
| 6 | memory（第六件，原文明确列出） | 会话之外的持久状态 | Markdown 进度文件（AGENTS.md、progress files）或 Linear（经 MCP） |

> 来源：https://addyosmani.com/blog/loop-engineering/

**结论**：五件套里只有第一件是 loop 本体，其余四件全是支持设施。〔**2026-09-13 更正**：按原文归属，`/loop`+`/goal` 属第 1 件 **Automations** 的 Claude Code 侧实现，而非独立条目；第六件 memory 属被承认的清单成员。〕五件套最小可用版 = git + python + 验证函数（Karpathy autoresearch，约 1,000 行 Python）。

---

## Addy 的三层 AI 工程架构

| 层 | 管什么 | 旧名字 | 招聘 JD |
|----|--------|--------|---------|
| **Context Engineering** | 上下文窗口里放什么 | prompt + RAG | Context Engineer |
| **Harness Engineering** | 单个 agent 跑在什么环境里 | system prompt + sandbox | Harness Engineer |
| **Loop Engineering** | 谁来触发 agent，什么时候停 | cron + ReAct/AutoGPT | Loop Engineer |

**关键观察**：每层对应的"旧技术"早已存在。Addy 的贡献是给 AI 工程造了一套可写在岗位 JD 上的词汇表——三个抽屉，三种 JD，三种立项理由。

> [!warning] 更正（2026-09-13）：上表与「关键观察」**缺少一手出处，归属有误**（原表述保留以便追溯）：
> ① Addy 的《Loop Engineering》全文**没有这张三层架构表**，也没有把 Context / Harness / Loop 并列成一套词汇表——该文中相关表述只有一句逐字为 "Loop engineering sits one floor above the harness."；「招聘 JD / Context Engineer / Harness Engineer / Loop Engineer」的说法在该文中检索不到（本次通读该页全文）。
> ② **harness engineering 一词不是 Addy 提出的**：他在前作《Agent Harness Engineering》(2026-04-19) 中逐字写明 "Viv Trivedy coined the term _harness engineering_"，并链接对方的《Anatomy of an Agent Harness》。因此「三层词汇表是 Addy 的贡献」缺少一手依据。
> ③ 处置：本节表与表题保留，但其性质应标注为**「转载方/本文的归纳，非 Addy 原文」**；`Harness Engineering` 一行的提出者应补 Viv Trivedy。
> 来源：https://addyosmani.com/blog/loop-engineering/ ，https://addyosmani.com/blog/agent-harness-engineering/

---

## Karpathy autoresearch — 最小可用证明

- 开源时间：2026-03-07〔可在 GitHub API 对上：`created_at` = 2026-03-06T22:00:43Z，折算北京时间 2026-03-07 06:00；保留原日期，仅补时区说明〕
- 代码量：约 630 行 Python（3 个文件：prepare.py / train.py / program.md）〔**2026-09-13 更正**：本次直接抓取三个文件逐行计数——**train.py = 630 行、prepare.py = 389 行（两个 .py 合计 1,019 行）**，program.md = 114 行且是 Markdown 而非 Python。原「约 630 行（3 个文件）」实际只等于 train.py 单文件，**低估约四成**；正确写法：「约 1,000 行 Python（train.py 630 + prepare.py 389）+ program.md 114 行 Markdown」。〕
- 核心循环：读 program.md → 形成假设 → 改 train.py → 跑 5 分钟 → 看 validation → 改进就 commit/没改进就 revert
- 效果：一小时约 12 个实验，一晚约 100 个；16 块 GPU 集群一晚 910 个实验/$309〔**2026-09-13 更正**：前两个数字可与仓库自述直接对上（README / program.md："approx 12 experiments/hour and approx 100 experiments while you sleep"），属合理保留；**后半句「16 块 GPU 集群」与该仓库口径不一致**——README 逐字写有 "A single NVIDIA GPU (tested on H100)"、"One GPU, one file, one metric."、"This code currently requires that you have a single NVIDIA GPU."，仓库 description 亦为「AI agents running research on single-GPU nanochat training automatically」；「910 个实验/$309」在文档中没有任何出处，疑似出自 Karpathy 推文，而 x.com 在本环境不可抓取、无法核实。处置：保留 12/小时与 100/晚，后半句须标注「数据出自 Karpathy 推文（附链接），口径为『多张单卡各跑一个 agent』而非分布式训练」，否则删除。〕

> [!success] 残余复核（2026-09-13 补录）：「910 个实验」的**出处已定位，且与上一条更正的猜测方向相反——既不出自仓库，也不出自 Karpathy 推文**，而是第三方 SkyPilot 团队的实测报告（Alex Kim / Romil Bhardwaj，2026-03-18，本次经代理直取 HTTP 200）。原文逐字：「We pointed Claude Code at autoresearch and gave it access to **16 GPUs** on a Kubernetes cluster. Over 8 hours it submitted **~910 experiments**, found that scaling model width mattered more than any single hyperparameter…」；硬件为 13×H100 + 3×H200；吞吐 ~90 实验/小时（单卡 ~10/小时，9×）；val_bpb 1.003 → 0.974（2.87%）。
> 因此**它与 README 的「单卡」口径并不冲突**：autoresearch 每个实验仍跑在单卡上，SkyPilot 只是把 16 个单卡实验并行起来（原文首段即「Karpathy's autoresearch runs one experiment at a time… We gave it access to our GPU infra and let it run experiments in parallel」）。上一条更正里「疑似推文」与「口径为『多张单卡各跑一个 agent』而非分布式训练」两句，前一句应删、后一句方向对但依据错（依据是 SkyPilot，不是推文）。
> **真正需要订正的是金额**：SkyPilot 原文 Cost 段逐字为「Claude Code's API cost for the session would be about **$9**. … 13 H100s for 8 hours is ~**$200** and 3 H200s for 8 hours adds ~**$60** (at ~$2.3/h), totaling **under $300** in total costs.」——**一手口径是「不到 $300」，不是 $309**；$309 是二手文章把「$300 GPU + $9 API」相加后的数。建议原句改写为：「一小时约 12 个实验、一晚约 100 个（仓库自述）；另有第三方实测把 16 张单卡并行后达 ~910 个实验 / 8 小时、总成本约 $300（SkyPilot，2026-03-18）」。
> 来源：https://blog.skypilot.co/scaling-autoresearch/

- 当前 stars：87,000+〔**2026-09-13 更正**：GitHub API 本次返回 `stargazers_count = 95,690`（forks 13,426），原「87,000+」已过期约 9%；且「当前」二字对快照类数字不安全，应写成带日期的快照，如「≈ 95.7k stars（2026-09-13 快照）」。〕
- 对应五件套的方式：
  - `/loop` → `while True` + 五分钟计时
  - worktree → `git commit / git revert`
  - SKILL.md → `program.md`
  - verifier → validation 指标数值
  - STATE.md → git history〔**2026-09-13 更正**：STATE.md 这个文件名在 Addy 原文中不存在（原文写的是 "Markdown (`AGENTS.md`, progress files) or Linear via MCP"），此处应读作「外部持久化状态（Markdown 进度文件 / 看板）→ git history」。〕

> [!info] 本节数字来源（2026-09-13 补录）
> https://api.github.com/repos/karpathy/autoresearch （stars / forks / created_at）
> https://raw.githubusercontent.com/karpathy/autoresearch/master/train.py 、https://raw.githubusercontent.com/karpathy/autoresearch/master/prepare.py 、https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md （逐行计数，2026-09-13 抓取）
> https://raw.githubusercontent.com/karpathy/autoresearch/master/README.md （单卡口径："A single NVIDIA GPU (tested on H100)"、"One GPU, one file, one metric."）

---

## 三个工程坑

> [!info] 2026-09-13 补录：每个坑补「如何检测 + 如何反制」——原文只给现象与金句，落地时无法执行。

1. **Verifier 信任问题**: 你信不过 verifier 就得自己看；自己看那 loop 跑了个寂寞。AutoGPT 2023 年典型翻车：search → save → verify → 重复 300 次零产出烧掉 $80。
   - **机制与反制（maker/checker 分离）**：Addy 原文——"This is also basically what Claude Code's `/goal` does under the hood, a fresh model decides if the loop is done instead of the one that did the work, the maker and checker split applied to the stop condition itself"；官方 `/goal` 文档亦写明 "After each turn, a small fast model checks whether the condition holds."。即：**让没干活的模型判「是否完成」**，而不是让干活的模型自评。
   - **检测**：验收条件是否可判定（能被一条命令/一个指标回答）？判定者是否独立于执行者？
   - **成本观测**：用 `/usage` 的 Loops 面板看该 loop 的运行次数与每轮 token（见上文「可观测性」）。
   - **人的责任边界**：Addy 原话 "Verification is still on you. A loop running unattended is also a loop making mistakes unattended."、"even then 'done' is a claim and not a proof."
   - 来源：https://addyosmani.com/blog/loop-engineering/ ，https://code.claude.com/docs/en/goal.md

2. **理解债**: loop 越快交付你没写过的代码，"代码实际上是什么"和"你以为是什么"之间的鸿沟就越大。
   - **检测**：合上编辑器，能否独立复述这次 loop 改了什么、为什么这么改、失败会怎么表现？答不上来就是债在累积。
   - **反制**：把「人真正读过并认可的代码比例」当成硬约束——loop 的产出仍要走 code review 与测试，而不是「跑通了就算交付」；必要时缩短单轮 loop 的改动面。

3. **认知投降**: loop 运行时人容易放弃自己的判断。"搭 loop 带着判断去做是解药，为了逃避思考去做是助推剂——同一个动作，相反的结果。"
   - **成本边界（Addy 原文警告）**：他在《Loop Engineering》开头即写 "you absolutely _have_ to be careful about token costs (usage patterns can vary wildly if you are token rich or poor)"，并指出子 Agent "do burn more tokens since each one does its own model and tool work"——**loop 的成本随「有多少子 Agent 各自跑模型」放大，不是免费的自动化**。
   - **检测**：每轮 loop 的 token 曲线是否在涨而产出没有同步增长（用 `/usage` 的 Loops 面板）。
   - 来源：https://addyosmani.com/blog/loop-engineering/ ，https://addyosmani.com/blog/practical-loop-engineering/

---

## 参考资料

- Addy Osmani 原文: https://addyo.substack.com/p/loop-engineering <!-- scan-ignore: substack 博客，非订阅源 -->〔**2026-09-13 更正**：该短链与可核实的一手地址不一致，主引用改用 https://addyosmani.com/blog/loop-engineering/ （HTTP 200，2026-06-07）〕
- Addy Osmani 后续: https://addyosmani.com/blog/practical-loop-engineering/ （HTTP 200，2026-08-14；给出 "A loop is an autonomous, self-correcting feedback cycle…" 的定义与 goal / loop 两个原语的分工）〔2026-09-13 新增〕
- 前作 Harness Engineering: https://addyosmani.com/blog/agent-harness-engineering/ （其中逐字写明 "Viv Trivedy coined the term _harness engineering_"）〔2026-09-13 补注〕
- Peter Steinberger 推文: https://x.com/steipete/status/2063697162748260627
- Karpathy autoresearch: https://github.com/karpathy/autoresearch
- Claude Code 2.1.139: https://www.anthropic.com/product/claude-code 〔**2026-09-13 标注**：该产品页不能证明 `/loop` 与 `/goal` 的上线版本；版本事实请改用 GitHub Release API 与官方 CHANGELOG——https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.71 （`/loop`，2026-03-07 UTC）、https://api.github.com/repos/anthropics/claude-code/releases/tags/v2.1.139 （`/goal`，2026-05-11 UTC）、https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md 〕
- Claude Code 官方文档（排程与目标）: https://code.claude.com/docs/en/scheduled-tasks.md （"Run prompts on a schedule"，含会话级边界与 "Let Claude choose the interval"）、https://code.claude.com/docs/en/goal.md （"Keep Claude working toward a goal"）〔2026-09-13 新增〕
- 第三方实测（/loop 与 cron 的分工）: https://www.frr.dev/fr/posts/loop-cron-claude-code/ （2026-03-09，记录「Claude Code 2.1.71 introduit /loop」与会话内调度器的定位）〔2026-09-13 新增〕
- O'Reilly Radar 联名版: https://www.oreilly.com/radar/loop-engineering/ 〔**2026-09-13 标注**：本次请求返回 403 Access Denied（Akamai 边缘拒绝，疑似反爬，**不能据此判定失效**），本环境无法核实其内容，故「联名版」这一说法**目前无法证实**；保留链接待人工用浏览器复核。〕

> [!success] 残余复核（2026-09-13 补录）：**已定论——页面存在，但「联名版」的说法不成立。**
> 直连与带正常浏览器 UA 的请求在本机仍为 **403**（Akamai 边缘拒绝，与上文标注一致，不是链接失效）；改用 **Wayback Machine 存档**取回该页（本次直取 HTTP 200，快照含完整正文）。页面元信息逐字为：标题「Loop Engineering – O'Reilly」，署名 **By Addy Osmani, June 22, 2026 • 14 minute read**，栏目 Radar > Topics > AI & ML。
> 判定「联名版」有误的依据是页面首段逐字：「**The following article originally appeared on Addy Osmani's blog and is being reposted here with the author's permission.**」——即**经作者许可的转载版**（O'Reilly 只是分发渠道），不是联名/合著。**建议改写为**：「O'Reilly Radar 转载版（署名 Addy Osmani，2026-06-22，经作者许可转载；原链 Akamai 反爬 403，可用 Wayback 存档访问）」。
> 附带收益：该页可核实的第三方原话有两条，本文摘要段的引述与之逐字一致——Peter Steinberger「You shouldn't be prompting coding agents anymore. You should be designing loops that prompt your agents.」；Boris Cherny「I don't prompt Claude anymore. I have loops running that prompt Claude and figuring out what to do. My job is to write loops.」
> 来源：https://web.archive.org/web/2026/https://www.oreilly.com/radar/loop-engineering/
- TechTalks "loopmaxxing": https://bdtechtalks.com/2026/06/22/ai-loop-engineering/
- 橙皮书（中文）: https://github.com/alchaincyf/loop-engineering-orange-book
- 鹤啸九天技术分析: https://wqw547243068.github.io/loop

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|-----------|
| 纠错 | 把 `/loop` 与 `/goal` 一并挂在「Claude Code 2.1.139 上线」上，并据此推出「Loop Engineering 是 2.1.139 功能集外包装」 | 保留原表述 + 更正：Release API 正文显示 `/loop` 于 **v2.1.71**（2026-03-07 UTC）引入、`/goal` 于 **v2.1.139**（2026-05-11 UTC / 北京 05-12）引入；摘要的核心论断同步修正（本体半壁来自 2 个多月前） |
| 纠错 | 「官方措辞: "let the model self-pace"」被当作 Anthropic 官方引语 | 保留原句 + 更正：官方 CHANGELOG 检索不到该句；可核实说法是 "self-paced dynamic mode"（2.1.248）/ "self-paced `/loop`"，官方文档小节题为「Let Claude choose the interval」；并给出两个官方文档页作更稳引用位 |
| 纠错 | 五件套构成写错、且称 STATE.md 为「附赠的第 6 件」 | 保留原表 + 更正并按 Addy 原文重排：1 Automations / 2 Worktrees / 3 Skills / 4 Plugins and connectors / 5 Sub-agents，**第六件 = memory**（原文明确列出）；`/loop`+`/goal` 归入第 1 件 Automations 的 CC 侧实现；STATE.md 非 Addy 所写文件名，改述为「Markdown 进度文件（AGENTS.md、progress files）或 Linear 看板」 |
| 纠错 | 「Addy 造了三层词汇表 + 三种招聘 JD」缺乏一手出处，且 harness engineering 归属错误 | 保留原表 + 更正块：Addy 原文无三层架构表与 JD 说法（只有 "Loop engineering sits one floor above the harness."）；**harness engineering 由 Viv Trivedy 提出**（Addy 前作逐字承认）；标注该表性质为「转载方/本文的归纳，非 Addy 原文」 |
| 纠错 | 「Google Chrome 工程主管 Addy Osmani」头衔过期 | 保留原表述 + 更正：其站点页脚自述最近职务为 Google Cloud AI 的 Director，近年方向是 AI/agentic engineering；该页脚早于本文 updated，不属事后之明 |
| 纠错 | autoresearch「约 630 行 Python（3 个文件）」、「当前 stars：87,000+」 | 逐行计数：train.py 630 + prepare.py 389 ≈ 1,019 行 Python，program.md 114 行 Markdown；stars 实测 95,690（2026-09-13 快照，原值已过期约 9%）；开源时间补时区说明（created_at 2026-03-06T22:00:43Z） |
| 纠错 | 「16 块 GPU 集群一晚 910 个实验/$309」与仓库自述口径冲突 | 保留「一小时约 12 个 / 一晚约 100 个」（可与 README 逐字对上）；后半句标注：仓库自述为**单卡**（"A single NVIDIA GPU (tested on H100)"），910/$309 无出处、疑似推文且不可抓取核验，须标注口径或删除 |
| 补疏漏 | 「Claude Code 的 /loop 本体」只有两条用法与一个版本，无运行边界与可观测性 | 新增「运行边界」表（会话级、resume 不恢复、7 天过期、Esc 清 pending wakeup、2.1.172 远程会话限制、与 cron 的分工）与「可观测性」段（2.1.243 的 `/usage` Loops 面板：每 loop 运行次数 / 总 token / 每轮 token / 最近运行），并给出 runaway 验收判据 |
| 补疏漏 | 「三个工程坑」只给现象与金句，无检测与反制 | 每个坑补「如何检测 + 如何反制」：坑一挂 maker/checker 分离（`/goal` 由另一模型判定）与 `/usage` 面板；坑二给可自问的理解债检测与「读过的代码比例」约束；坑三引 Addy 的 token 成本警告与子 Agent 成本放大机制 |
| 加厚 | 参考资料主引用为 substack 短链，O'Reilly「联名版」无法核实 | 主引用改为 addyosmani.com 两篇一手原文，O'Reilly 条目保留并标注 403/未核验；新增官方 CHANGELOG、两条 Release API、两个官方文档页、第三方实测链接 |
| 残余复核 | 「910 个实验 / $309」出处未知（原判为「疑似 Karpathy 推文、不可核验」） | **已结**：出处为第三方 SkyPilot 实测报告（blog.skypilot.co/scaling-autoresearch，2026-03-18，本次直取 200）——16 GPUs（13×H100 + 3×H200）、~8 小时、~910 experiments、吞吐 9×、val_bpb 1.003→0.974；与 README 单卡口径**不冲突**（每实验仍单卡，只是并行 16 路）。金额订正：一手为「under $300」（GPU ~$260 + API ~$9），非 $309 |
| 残余复核 | O'Reilly「联名版」说法无法证实（原链 403） | **已结**：Wayback 存档取回原页（HTTP 200），署名 Addy Osmani / 2026-06-22；页面首段逐字「originally appeared on Addy Osmani's blog and is being reposted here with the author's permission」→ **经许可的转载版，非联名**；顺带核实 Steinberger / Cherny 两句引语逐字一致 |

回链：[[CORRECTIONS]] | [[AGENTS]]
