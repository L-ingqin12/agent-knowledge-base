---
title: Pi Agent 框架知识
aliases: []
tags: [ai/ops, ai/agent]
created: 2026-08-10
updated: 2026-09-13
status: stable
---

# Pi Agent 框架知识

> [!abstract] Pi Agent 框架完整知识 — TypeScript monorepo、内置工具集（官方文档列 8 个，本地源码核验称 9 个且其中 1 个无外部支撑，见勘误）、800token预算、parallel tool execution、programmatic SDK

See also: [[Claude-Ops-KB-Home]] · [[pi-agent-constraints-reference]] · [[pi-agent-log-analysis-plan]] · [[opencode-pi-base-development-analysis]] · [[参考-Pi-Agent-技术调研报告]]

## 定义

Pi Agent (Mario Zechner/badlogic) 是 TypeScript 编写的 AI Agent 工具包，monorepo 结构: pi-ai (LLM providers) → pi-agent-core (Agent loop) → pi-coding-agent (runtime) → pi-tui (TUI)。

## 核心约束

- **内置工具（0.84.3 源码核验）**: bash / read / write / edit / edit-diff / grep / find / ls / powershell（Windows 一等支持的直接证据）

> [!note] 勘误 (2026-08-26): 本文早期沿用宣传口径「read/write/edit/bash 四原子工具」；经 @earendil-works/pi-coding-agent@0.84.3 npm 包源码逐文件核验，面向模型的内置工具实为上列 9 种（见 [[参考-Pi-Agent-技术调研报告]] §11.3）。「组合而非新增」的极简哲学不变。

> [!warning] 更正（2026-09-13）：版本锚点已过期，且「9 工具」目前无外部支撑（原表述为上面那条内置工具与勘误里的 `0.84.3` / 9 个工具名）
> **① 版本锚点过期**：npm latest 现为 **`@earendil-works/pi-coding-agent@0.85.1`**（`engines: node>=22.19.0`，依赖 `@earendil-works/chord` / `pi-ai` / `pi-tui` / `pi-agent-core` `^0.85.1`）。0.84.3 已过期。
> 版本锚点今后必须写成「**核验版本 + 核验日期 + 复核命令**」，例如 `npm view @earendil-works/pi-coding-agent version`（2026-09-13 → `0.85.1`）——否则上游每发一次版，这段结论就自动失效而无人察觉。
> **② `edit-diff` 一个工具查无外部支撑**：官方 SDK 文档逐字「Built-in tool names: **read, bash, powershell, edit, write, grep, find, ls**」——共 **8 个**，不含 `edit-diff`；同页另写「Default built-ins: read, bash, edit, write」；在整页（含仓库 `docs/sdk.md` 补充来源）检索 `edit-diff` 为 **0 命中**；npm 包描述也只写「read, bash, edit, write tools」。
> 因此这份**自证式勘误**（「我核验过源码」）目前只有内部证据：要么补上**版本号 + 具体文件路径 + 统计命令/输出**，要么按官方口径改回 **8 个**名称。
> 该差异直接影响 `tools: [...]` 白名单配置——写错一个名字的后果是工具**静默不可用**。
> 依据：<https://pi.dev/docs/latest/sdk> · <https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest>
- **~800 token 系统提示词预算** (刻意保持低开销)
- **无 Agent spawn** — 无子 Agent 概念，用 parallel tools 或 多 AgentSession 模拟
- **无内置权限系统** — 依赖 Docker/Gondolin/OpenShell 容器化
- **无原生 HTTP Server** — 需自行包装 (Express/Fastify)

> [!warning] 更正（2026-09-13）：这一条需要限定——官方已有 RPC 模式与 JSON 事件流（原表述为上一行）
> Pi 确实不自带面向公网的 HTTP server，但**跨进程集成是官方支持路径**，不是「只能自己包 Express」：
> - 官方 SDK 文档导航含 [RPC Mode](/docs/latest/rpc)、[JSON Event Stream Mode](/docs/latest/json)、`runRpcMode`，以及「RPC Mode Alternative」一节。
> - npm manifest 的 `exports` 里确有 `"./rpc-entry"`；`devDependencies` 含 `@earendil-works/pi-server` / `pi-client` / `pi-protocol` `^0.85.1`。
>
> 因此决策时应把三条路并列比较，而不是默认自建 HTTP：
>
> | 路径 | 形态 | 并发 / 隔离 | 崩溃域 |
> |------|------|-------------|--------|
> | 同进程 SDK | `createAgentSession()` 嵌进服务进程 | 无进程隔离；SDK 阻塞会拖住整个服务 | 与服务同一崩溃域 |
> | **RPC 子进程**（官方） | Node 子进程 + stdio JSONL（`./rpc-entry`） | 每子进程独立，可起多个 | 子进程崩溃不影响主服务 |
> | 自建 HTTP | Express/Fastify 包一层 | 取决于实现 | 自建 |
>
> 依据：<https://pi.dev/docs/latest/sdk> · <https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest>

> [!warning] 补（2026-09-13）：上面「~800 token」与「Extension system: 25+ 事件类型」两个数字都没有出处（原表述为「~800 token 系统提示词预算」与「Extension system: 25+ 事件类型，beforeToolCall/afterToolCall hooks」）
> 两者都决定设计边界，必须补**上游出处 + 复核命令**：
> - **「~800 token 系统提示词预算」**决定「日志分析指令能否塞进 system prompt」——需给出该预算的取得方式（读源码的哪段、哪个版本）与实际测量（用什么 tokenizer 数出来的）。
> - **「Extension system: 25+ 事件类型」**决定「hook 能拦哪些点」——需列出事件名清单（或指向官方 Extensions 章节），并注明核验版本。
> 附注：审计原稿把「pi-ai：20+ providers」也并进本条，但那一句实际在 [[pi-agent-constraints-reference]]，不在本页——本页只认上面两个数字。
> 主源口径见下方「来源」块：官方文档站 <https://pi.dev/docs/latest>。

> [!warning] 补（2026-09-13）：本页来源应以官方文档为主源，DeepWiki 降为辅助（原表述为 See also 与「定义」节的引用方式）
> 官方文档站确实存在且可直接引用：<https://pi.dev/docs/latest>（导航覆盖 Overview / Quickstart / Providers / Security / Containerization / Settings / Sessions / Compaction / Extensions / Skills / Packages / Models / SDK / RPC / JSON / Windows / Termux）。
> 现状问题：本页 See also 只有 [[参考-Pi-Agent-技术调研报告]] 一个内部链接，而该报告的底稿把「官方源码 + DeepWiki 分析 + Web 搜索」并列——**DeepWiki 是 AI 生成的第三方页面**，与「官方源码」并列会让人误以为同等可靠，而本库把「把现象当结论」列为头号错误来源。
> 口径：三篇 Pi 文档（本页、[[pi-agent-constraints-reference]]、[[参考-Pi-Agent-技术调研报告]]）应逐条标注**来源类型**（官方文档页 URL / 源码路径 + 版本 / 实测）与**核验日期**，并优先改用官方文档站。

## 关键能力

- **Programmatic SDK**: `createAgentSession({ sessionManager: SessionManager.inMemory() })` 可嵌入 Node.js 服务
- **Parallel tool execution** (默认): `toolExecution: "parallel"` → `Promise.all` 并发执行工具调用 → LLM 自主 Fan-Out
- **Event system**: `session.subscribe()` 订阅流式文本/工具执行/生命周期事件
- **Tree-based JSONL session**: 支持分支/fork/compaction
- **Skills**: 渐进式披露 — `.md` 文件通过 `read` 工具按需加载
- **Extension system**: 25+ 事件类型，beforeToolCall/afterToolCall hooks

## 与 opencode 的关键差异

| 维度 | Pi Agent | opencode |
|------|----------|----------|
| 语言 | TypeScript (Node.js) | TypeScript（TUI 部分为 Go） |
| 工具模型 | 内置 9 工具（bash/read/write/edit/edit-diff/grep/find/ls/powershell） | 丰富工具集 |
| 并行 | toolExecution: "parallel" (LLM 自主) | 依赖插件 (agent-intercom) |
| 嵌入 | SDK in-process | subprocess / HTTP |
| 系统提示词 | ~800 tokens (强制精简) | 无硬限制 |

## 对日志分析架构的影响

- HTTP 层必须用 Node.js (Express/Fastify)，不能用 Tornado
- 多进程用 Node.js cluster 而非手动多端口
- 分析指令通过 Skills (渐进式) 注入，不占 system prompt
- LLM 自主决定并行维度 → 更灵活但可控性低于代码固定的 ThreadPoolExecutor

**Why:** Pi Agent 和 opencode 是两种完全不同的 Agent 框架范式 — TypeScript SDK 嵌入 vs TypeScript CLI subprocess 调用（TUI 为 Go）。选择哪个决定了整个 HTTP 服务的技术栈。
**How to apply:** 设计基于 Pi Agent 的服务时，始终从 "内置工具集 + 800 token + SDK in-process" 的约束出发，不要照搬 opencode 的方案。

## 关联

- [[pi-agent-log-analysis-plan]] — Pi Agent 版日志分析方案
- [[log-analysis-agent-windows-architecture]] — opencode 版方案 (横向对比)
- [[fan-out-subagent-pattern]] — Pi Agent parallel tools 实现 Fan-Out
- [[agent-async-isolation-pattern]] — Node.js 版不适用此 pattern
- [[opencode-multi-agent-architecture]] — opencode 两层模型对比

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|------|--------|------------|
| 纠错 | 「经 @earendil-works/pi-coding-agent@0.84.3 npm 包源码逐文件核验」的版本锚点已过期（现行 0.85.1） | 保留勘误原文并加更正块：npm latest = 0.85.1（engines node>=22.19.0，依赖 chord/pi-ai/pi-tui/pi-agent-core ^0.85.1）；并要求版本锚点写成「核验版本 + 日期 + 复核命令」。依据 <https://registry.npmjs.org/@earendil-works/pi-coding-agent/latest> |
| 纠错 | 勘误宣称「9 工具（含 edit-diff）」无外部支撑 | 更正块给出官方 SDK 文档逐字 8 个工具名（read/bash/powershell/edit/write/grep/find/ls），`edit-diff` 在官方页与仓库 docs/sdk.md 均 0 命中；要求补核验依据或改回 8 个；摘要与「与 opencode 的关键差异」表未强行改写，但已标注差异待确认 |
| 补疏漏 | See also 与引用路径以 DeepWiki（AI 生成页）与旧仓库名为主，未把官方文档站作为主源 | 加「来源」块：给出官方文档站 pi.dev/docs/latest 的章节清单，要求三篇 Pi 文档逐条标注来源类型与核验日期，DeepWiki 降为辅助并标注「AI 生成、非官方」 |
| 补疏漏 | 「无原生 HTTP Server — 需自行包装 (Express/Fastify)」需要限定：官方已有 RPC 模式与 JSON 事件流 | 保留原条目并加更正块：官方 RPC（stdio JSONL、`./rpc-entry`）与 JSON 事件流为受支持路径，npm exports 与 pi-server/pi-client/pi-protocol 亲验；补三条路径对比表（同进程 SDK / RPC 子进程 / 自建 HTTP） |
| 加厚 | 「~800 token 系统提示词预算」「Extension system: 25+ 事件类型」都无出处 | 加补正块，要求各自补上游出处与复核命令，并说明它们分别决定「指令能否塞进 system prompt」与「hook 能拦哪些点」；同时更正审计原稿的归属错位（「pi-ai 20+ providers」在姊妹文档） |

回链：[[CORRECTIONS]] · [[AGENTS]]
