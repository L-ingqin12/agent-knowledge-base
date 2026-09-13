---
title: MEMORY-INDEX
aliases: [Memory 索引, memory 知识索引, MEMORY 记忆索引]
tags: [ai/ops, ai/agent]
created: 2026-08-17
updated: 2026-09-13
status: stable
---

# MEMORY-INDEX — Agent-架构模式记忆索引

> [!abstract] 迁移说明
> 本文档由远程 `memory/MEMORY.md` 索引迁移而来。原索引共 **19 条**，其中 7 条指向实际存在的记忆文件（已迁移入本目录）；**12 条悬空**（指向归档中不存在的文件）——6 条在本子库存在等价文档已重定向，6 条内容散落、无本地等价，原始链接已修复不再悬空。

See also: [[Claude-Ops-KB-Home]] · [[AGENTS]] · [[AI-Links-KB-Home]]

## 定位：本索引 vs Claude Code 官方记忆模型（2026-09-13 补）

> [!warning] 补疏漏：本索引是**项目自有归档**，不是 Claude Code 的 `MEMORY.md`
> 全文（原表述）只索引本库文档，一处未提官方记忆模型，容易被误读为「本库记忆 = Claude Code 记忆」。二者是两套东西，对照如下：
>
> | 官方机制 | 官方行为 | 与本索引的关系 |
> |---|---|---|
> | `CLAUDE.md` 层级（企业 / 用户 / 项目 / 子目录） | 每次会话启动即载入；**项目根 `CLAUDE.md` 在 `/compact` 后由 Claude Code 从磁盘重读并重新注入** | 本索引不承担该职责；本库规范入口是 [[AGENTS]] |
> | auto memory | Claude 自己写入的 `MEMORY.md`，每次启动只载入**前 200 行或 25KB（先到者）**；`/memory` 打开、`/context` 查看实际占用 | **本文件不是它**——同名但不同物，本文是 Agent-架构模式目录的库内索引 |
> | 子代理记忆 | 子代理定义里的 `memory` frontmatter 字段可开启独立持久记忆 | 与本索引无重叠，属未收录的官方载体 |
>
> 来源：<https://code.claude.com/docs/en/memory.md>

## 实际存在的记忆文档（7 条）

| 记忆文档 | 摘要 | 核验方式 | 最后核验日 |
|----------|------|---------|-----------|
| [[agent-async-isolation-pattern]] | ThreadPoolExecutor + asyncio.wait_for 三层超时包装同步 Agent 调用 | 未复核 | — |
| [[deploy-workflow-write-to-repo-first]] | ⚠️ 所有代码变更先在归档仓库编写测试，用户确认后再部署 | 未复核 | — |
| [[fan-out-subagent-pattern]] | 并行分发 N 个子任务、防冲突机制、OpenCode vs Claude Code 对比 | 未复核 | — |
| [[log-analysis-agent-windows-architecture]] | Nginx+Tornado 多进程+ThreadPoolExecutor 异步隔离+Windows TCP 调优 | 未复核 | — |
| [[opencode-multi-agent-architecture]] | Primary/Subagent 两层模型、自规划调度、Fan-Out、权限隔离 | 未复核 | — |
| [[pi-agent-framework-knowledge]] | TypeScript monorepo、内置工具 9 种（0.84.3 源码核验，含 powershell/edit-diff）、800token 预算、programmatic SDK | 本机包源码核验（见摘要括注） | — |
| [[state-machine-quality-gate-loop]] | 7 状态控制流、VERIFY 门/RETRY 回环/ESCALATE、死循环保护 | 未复核 | — |

> [!warning] 补疏漏（2026-09-13）：为什么加「核验方式 / 最后核验日」两列
> 原表（原表述）只有「记忆文档 / 摘要」两列，**没有任何核验标注**，而本库 `sources/*.md` 的登记里 `verified::` 大量集中在 2026-09-12（另有 2026-09-13），**同日集中登记无法区分「看过官方文档」与「只看过本机」**。
> 可验证的对照：官方 changelog 显示 **2026-09-12 已发布 v2.1.270**（2.1.269 为 09-11），而本簇笔记仍停留在 2.1.1xx（无人值守方案记 v2.1.172）——日期相近不等于版本同期。
> 取值口径：「**本机观察** / **官方文档 URL** / **未复核**」三档；日期填最后核验日，`—` 表示无记录。本表 2026-09-13 复核时**未逐篇回核原文**，故除自带核验说明的 Pi 条外一律记「未复核」，不冒充已核验。
> 来源：<https://code.claude.com/docs/en/changelog.md> · [[sources/security-audit|sources/security-audit.md]] · [[sources/README]]

## 2026-08-25 新增架构文档（4 篇）

| 新文档 | 摘要 |
|--------|------|
| [[main-subagent-realtime-interaction]] | 主↔子 agent 实时交互四原语：活性感知(4层金字塔)/邮箱通知/打断抢占/checkpoint 恢复 + T0..T3 升级阶梯 |
| [[opencode-pi-base-development-analysis]] | 基座开发七维度选型：OpenCode 交互基座+Sidecar 外挂 vs Pi 嵌入；明文治理 manifest+secure_read；会话池流水排布；跨平台矩阵与 Phase 0-4 路线图 |
| [[lognet-rootcause-multiagent-architecture]] | 日志网络根因分析多Agent架构：LogNet 图+时间线、从问题节点渐进展开、符号化工具链(addr2line/artget)、多包并发与可行性路线 |
| [[agent-memory-context-knowledge-design]] | 记忆三级模型(L1窗口/L2状态/L3知识库)、上下文五源装配与前缀稳定排序、外部知识库化四形态与写入检索治理（复用本库 AGENTS 协议） |

## 2026-08-26 新增（3 篇）

| 新文档 | 摘要 |
|--------|------|
| [[agent-harness-anatomy]] | Agent Harness 七件套解剖(提示词脚手架/工具循环/上下文记忆/权限沙箱/子代理编排/Hook扩展/观测评测)、Claude Code/OpenCode/Pi/DSH 四家实现对照、从零构建决策树(Anthropic 五模式)与反模式清单 |
| [[agent-evals-observability]] | Agent 评测三层次(单步/轨迹/端到端)、四层方法栈(确定性断言→LLM-as-Judge 校准→人工盲测→在线评估)、trace 结构化采集、质量门控 RETRY/ESCALATE 阈值定标与成本计量 |
| [[Anthropic多智能体研究系统拆解]]（articles/） | 编排者-工作者生产复盘：委派工程三要素/努力分级/15× token 经济学/评测三件套，映射本库协议 |
| [[opencode-深入使用与扩展实战]] | OpenCode 实操手册：permission last-match 规则、agent frontmatter 路由、TypeScript 自定义 tool、hook 五件套审计落盘、serve+SSE 服务化与排障 |
| [[pi-agent深入使用与扩展实战]] | Pi 实操手册：L2 AgentSession 二开层、TypeBox defineTool 全码、steer/followUp/abort 三原语对应交互阶梯、RPC stdio 嵌入、JSONL 会话树→LogNet 数据通道 |

## 悬空条目已重定向（6 条）

| 原索引条目（文件不存在） | 重定向至本库等价文档 |
|--------------------------|----------------------|
| claude-unattended-operation-guide.md | [[claude-unattended-operation-plan]] |
| claude-interruption-resilience.md | [[claude-interruption-resilience-guide]] |
| claude-context-continuity.md | [[claude-context-continuity-guide]] |
| claude-socket-error-elimination.md | [[claude-socket-error-elimination-guide]] |
| hermes-parallel-task-communication.md | [[hermes-parallel-task-report]] |
| claude-cache-permafrost-setup.md | [[PERMAFROST_MODIFICATIONS]]（+ [[claude-cache-strategy]]） |

## 散落条目无本地等价（6 条）

以下条目在原索引中出现，但归档仓库中既无文件、本库也无等价文档，内容散落未存档：

| 原索引条目 | 主题 |
|------------|------|
| occams-razor-principle.md | 如无必要勿增实体——设计全局约束 |
| claude-code-upgrade-incident-2026-06-09.md | v2.1.150→v2.1.169 升级事故与标准流程 |
| claude-code-preflight-checklist.md | ⚠️ 行动前强制检查清单（5 项检查 + 5 条硬规则） |
| claude-code-environment-architecture.md | Termux+PRoot 混合环境、两条 npm 体系、PATH 优先级（最接近本库文档: [[pi-vs-termux-guide]]） |
| claude-code-npm-postinstall-mechanism.md | optionalDependency→原生二进制→linkSync 替换流程 |
| raspberrypi-proxy-ipv6-fix-pending.md | 树莓派代理 IPv6 无路由修复待续 |

> [!bug] 遗留问题
> 以上 6 条记忆源文件不在远程归档中（`_install-tmp/akb-remote/memory/` 仅有 9 个 md：7 条记忆 + 本索引 + README）。如需补全，需回到原始运行环境 `/root/.claude/projects/-root/memory/` 取回。

> [!note] 补全判据（2026-09-13 补）
> 上条 callout 只给了路径与「需回到原始运行环境取回」，**没有可执行判据**（怎么算补全、补到哪一步停）。补三条：
> 1. **路径写法确认**：官方 auto memory 目录为 `~/.claude/projects/<project>/memory/`，`<project>` 由**工作目录路径把非字母数字替换为 `-`** 得到，故 `/root` 工作目录对应 `-root`——`/root/.claude/projects/-root/memory/` 写法正确。
> 2. **逐个验收动作**：对「散落条目」表 6 行逐条处置——能找到源文件 ⇒ 迁入本目录并在索引表标注；只能找到等价文档 ⇒ 在「已重定向」表补一行；两者都无 ⇒ 转 `deprecated` 墓碑行。
> 3. **放弃判据**：远程归档已删除**且**原始运行环境不可达 ⇒ 就地标 `deprecated` 并在索引**保留墓碑行**（不删行，历史可追溯）。**完成信号**：索引表「散落条目」一节清空，或全部转为 `deprecated` + 替代链接。
>
> 来源：<https://code.claude.com/docs/en/memory.md>

## 交叉 Wikilink

- 记忆索引 → MOC：[[Claude-Ops-KB-Home]]
- 部署工作流 → 部署记录：[[claude-deployment-record]]
- 异步隔离/日志分析：[[log-analysis-agent-architecture]] · [[agent-async-isolation-pattern]]
- Fan-Out/质量门控/OpenCode：[[fan-out-subagent-pattern]] · [[state-machine-quality-gate-loop]] · [[opencode-multi-agent-architecture]]
- 实时交互/基座选型：[[main-subagent-realtime-interaction]] · [[opencode-pi-base-development-analysis]] · [[lognet-rootcause-multiagent-architecture]] · [[agent-memory-context-knowledge-design]]
- Harness 解剖/评测观测：[[agent-harness-anatomy]] · [[agent-evals-observability]]
- Pi Agent 体系：[[pi-agent-framework-knowledge]] · [[pi-agent-constraints-reference]]
- Hermes 并行机制：[[hermes-parallel-task-report]]

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 补疏漏 | 全文无一处引用官方记忆模型（CLAUDE.md 层级 / auto memory），易被误认为「本库记忆 = Claude Code 记忆」 | 新增「定位：本索引 vs Claude Code 官方记忆模型」对照表，并注明本文是项目自有归档而非官方 `MEMORY.md`（memory 官方页） |
| 补疏漏 | 索引表无任何核验标注，而同日本库 sources 登记集中在 2026-09-12/13，无法区分「看过官方文档」与「只看过本机」 | 主表增「核验方式」「最后核验日」两列（三档口径），并给可验证对照：官方 changelog 2026-09-12 已到 v2.1.270，本簇笔记仍停在 2.1.1xx |
| 加厚 | 「遗留问题」只给取回路径，无补全判据 | 补三条判据：路径写法确认（`-root` 由来）、6 条逐个验收动作、放弃判据与完成信号（清空或全部转 deprecated 墓碑行） |

回链：本文 See also 已含 [[AGENTS]]；新增 [[CORRECTIONS]]
