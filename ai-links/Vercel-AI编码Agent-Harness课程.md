---
title: Vercel 课程 — Build Your Own AI Coding Agent Harness
aliases: [Vercel Agent Harness课程, TeensyCode, 手写Agent框架课程]
tags: [ai/agent, ai/learning, ai/links]
created: 2026-08-18
updated: 2026-09-13
status: review
source_urls:
  - https://vercel.com/academy/build-ai-agent-harness
  - https://vercel.com/academy/build-ai-agent-harness/pruning-old-results
  - https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0
  - https://ai-sdk.dev/docs/reference/ai-sdk-ui/prune-messages
fetched_at: 2026-08-18
---

# Vercel 课程 — Build Your Own AI Coding Agent Harness

See also: [[2026-08-16-AI链接综述与归档]] | [[DSH插件与Hook开发最佳实践]] | [[Articles-Index]] | [[AI-Links-KB-Home]] | [[AGENTS]]

> [!abstract] 课程定位
> Vercel Academy 免费课程：从零手写一个**能真正干活**的 AI 编码 Agent 框架（Harness），产出项目 **TeensyCode**——紧凑 TypeScript 核心 + 真实工具集 + 多沙箱后端。开篇立意即本书主旨：「三个工具的 tool loop 只是 demo；问题从用它干真活才开始」（5000 行文件常驻上下文、`rm -rf`、只会解释不会动手、长任务挤爆窗口、云沙箱按分钟烧钱且超时丢代码）。

## 开篇五痛点 → 模块 → 机制 → 验收判据（2026-09-13 补）

开篇五个痛点不是修辞，各自落到具体模块与可检验的产出（痛点原文逐字取自课程页）：

| 痛点（课程原文） | 模块 | 机制 | 验收判据（本库口径） |
|---|---|---|---|
| You read a 5,000-line file and it stays in context forever | 5 Context Management | `pruneMessages` 剪旧工具结果 + 工具输出有界 | 长任务中 token 曲线不再线性增长；被剪轮次的旧结果不再出现在后续请求体 |
| You give it bash and it runs rm -rf | 1/2/8 工具与审批 | 执行级安全门 + 审批三模式（交互/后台/委托） | 危险命令在无人值守模式下落 deny 而非执行；审批决策可在事件总线回放 |
| You ask it to refactor a module and it explains how to refactor a module | 3 The System Prompt | Agency 节（行动而非解释）+ 验证门契约 | 同一 prompt 下产出 diff 而非说明文；typecheck/lint/test/build 门全绿才算完成 |
| One long task fills the context window and the agent loses its own instructions | 5 + 7 Context/Lifecycle | 有界工具输出 + 快照/恢复 + durable workflow | 跨上下文窗口后 `AGENTS.md` 约束仍生效；恢复后工作区状态与快照一致 |
| The cloud sandbox costs money per minute and your code disappears when it times out | 4 Sandbox + 7 Lifecycle | 三后端可换（本地/内存/远程 VM）+ 生命周期钩子 afterStart/beforeStop/onTimeout | 同一测试用例跑三后端结果一致；超时钩子能落盘现场而非丢代码 |

> 判据取证来源：官方课程已把 Module 5 拆成可独立访问的课页，如 [Pruning Old Results](https://vercel.com/academy/build-ai-agent-harness/pruning-old-results)——页内含 Done-When 判据清单与 `npx tsc --noEmit` 门。上表「验收判据」列为本库按课程模块职责补写的可检验口径，与该课页的 Done-When 清单同源同形。

## 一、你将构建什么（TeensyCode 能力清单）

- **主循环**：`ToolLoopAgent`，工具集 `read/grep/write/edit/bash/task/askUser`
- **安全门**：执行级安全（命令白名单）→ 可配置审批（交互/后台/委托三模式）
- **行为提示词**：结构化 system prompt（Agency / Guardrails / Handling Ambiguity 三节）+ `AGENTS.md` 注入实现每项目配置
- **沙箱抽象**：一个 `Sandbox` 接口，两种实现（本地 Node fs+child_process；内存 just-bash + copy-on-write 虚拟文件系统），换后端工具不变
- **上下文管理**：`pruneMessages`、有界工具输出、cache control
- **子代理委派**：Explorer（只读+便宜模型）/ Executor（全工具+强模型）角色，按任务选模型
- **人在回路**：`askUser` 多选 + 「先搜索、再提问、后行动」的歧义协议
- **沙箱生命周期**：状态机、快照/恢复、durable workflow
- **可扩展性**：事件总线、渐进式披露的 Skills、自定义工具注册

## 二、11 模块大纲

| 模块 | 主题 | 关键课 |
|---|---|---|
| 1 | The Agent Loop | 从 Chatbot 到 Agent（一个工具即质变）；工具描述 = 模型选择 API；危险工具加执行级门 |
| 2 | Tool Design | 5 段式描述契约（WHEN TO USE / WHEN NOT / DO NOT USE FOR / EXAMPLES）；工厂+操作分离；审批：布尔→函数→可辨识联合 |
| 3 | The System Prompt | Agency+Guardrails（行动而非解释）；`buildSystemPrompt()` 动态组合；验证门（typecheck/lint/test/build 契约）；`AGENTS.md` 项目上下文 |
| 4 | Sandbox Abstraction | `Sandbox` 接口（readFile/exec/stop）；本地实现；内存实现（just-bash + CoW 覆盖层）；云端实现（远程 VM 权衡）；生命周期钩子（afterStart/beforeStop/onTimeout） |
| 5 | Context Management | token 日志揭示线性增长；`pruneMessages` 剪旧结果；工具输出有界（预防优于清理）；provider cache control 头 |
| 6 | Subagent Delegation | 单 Agent 失败模式；Explorer（只读/便宜/受限探索）；Executor（全工具/强模型/委托信任）；`task` 工具（路由/权限/按角色选模型） |
| 7 | Sandbox Lifecycle（概念课） | 状态机与超时/活动跟踪；快照与恢复（幂等性陷阱）；Vercel Workflow 的 `sleep()`；生产教训 |
| 8 | Human-in-the-Loop | `askUser` 结构化提问 + 歧义协议；审批配置（模式）+ 策略事件 |
| 9 | Planning and Verification | Todo 工具（分解+状态跟踪）；grep 先行、只读将改之处；验证契约（门序列+限定声明） |
| 10 | Surfaces | CLI 入口（args/沙箱工厂/干净退出）；流式与工具渲染；Web 面（同一 Agent 换渲染器） |
| 11 | Extensibility | Skills 渐进式披露（名字进 prompt、正文按需取）；自定义工具注册（不 fork）；扩展点（生命周期事件：subscribe/block/modify） |

**Capstone**：对真实项目跑 harness——不是「加个 hello world 端点」而是「给 auth 路由加限流」，观察上下文溢出、选错工具、子代理指令错误，修复暴露的问题。

## 二·附：Module 4 / 7 展开（2026-09-13 补）

原文对 Module 4「沙箱抽象」与 Module 7「状态机、快照/恢复、durable workflow」各只有一句结论，下面补到「能照做」。

### 三后端取舍对照

| 后端 | 隔离强度 | 启动延迟量级 | 文件系统语义 | 成本模型 | 主要失败模式 |
|---|---|---|---|---|---|
| 本地 Node（fs + child_process） | 无隔离：与 Agent 同机同用户，bash 直跑真实环境 | 毫秒级 | 真实 FS，改动立即落地 | 只花自己的机器 | `rm -rf` 真删；无快照，事故不可逆 |
| 内存 just-bash + CoW 覆盖层 | 进程内模拟，无真实系统调用 | 毫秒级 | 写时复制虚拟 FS，可整层丢弃 | 计入模型 token，无平台费 | 模拟 bash 与真实 bash 的语义缺口（管道/权限/子进程/信号） |
| Vercel Sandbox 远程 VM | 独立 VM，隔离 FS/git/npm | 秒级（含冷启动） | 远程独立 FS，产物需显式取回 | 按分钟计费 | 超时即销毁 → 未落盘代码丢失；网络与预热延迟 |

> 延迟量级为定性判断（课程未给基准数据），落地前应在目标环境实测；成本模型的「每分钟」口径以 [Vercel Sandbox 文档](https://vercel.com/docs/functions/sandbox) 为准。

### `Sandbox` 接口契约与「换后端工具不变」的验证法

- 接口面：`readFile(path)` / `exec(cmd)` / `stop()`，配套生命周期钩子 `afterStart` / `beforeStop` / `onTimeout`——工具层只依赖这些方法，不碰后端实现。
- 验证法（同 [[DSH插件与Hook开发最佳实践]] 的工具契约思路）：写一个用例「读文件 → 写文件 → 跑命令 → 断言输出」，在本地 / 内存 / 远程三后端各跑一遍；**工具层代码零改动即通过**才算抽象成立，任何一处需要 `if (backend === ...)` 就是抽象漏了。

### 快照/恢复的幂等性判据

- 恢复后 `git status` 干净：不出现重复应用的补丁、重复写入或重复 commit。
- 快照 ID 可复现：同输入状态导出两次得到同一标识（或同一内容哈希）。
- 反例（幂等性陷阱）：恢复流程重放了副作用——二次 `npm install` 产生重复依赖、日志被追加两遍、`append` 型写操作被执行两次。

## 三、技术栈与教学法

| 组件 | 用途 |
|---|---|
| [AI SDK](https://sdk.vercel.ai/) | `ToolLoopAgent`、`tool()`、`stepCountIs`、`pruneMessages`、流式 |
| [AI Gateway](https://vercel.com/ai-gateway) | 模型路由：`"anthropic/claude-haiku-4-5"` 字符串即用，无包装层 |
| [Vercel Sandbox](https://vercel.com/docs/functions/sandbox) | 远程 VM（隔离文件系统/git/npm） |
| [just-bash](https://www.npmjs.com/package/just-bash) | 内存虚拟文件系统 + 模拟 bash |
| [Vercel Workflow](https://vercel.com/docs/workflow) | 沙箱生命周期的 durable workflow |
| [Zod v3](https://zod.dev/) | 工具入参 schema（注意 v4 与 AI SDK v6 类型不兼容） |

> [!warning] 版本漂移提示（2026-09-13 复核）
> 上表 Zod 行的「v4 与 AI SDK v6 类型不兼容」转述自课程页 Tech Stack 表，**转述无误**——但该表述已落后一个大版本：npm `ai` latest = **7.0.99**（2026-09-12 发布），官方文档站默认「v7 (Latest)」并提供《[Migrate AI SDK 6.x to 7.0](https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0)》。课程录制于 AI SDK v6 时期；v6→v7 有破坏性改名（`onFinish`→`onEnd`、`onStepFinish`→`onStepEnd`、`fullStream`→`stream`、`experimental_telemetry`→`telemetry`），**照抄课程代码前先跑官方 codemod**；`pruneMessages` 参考页仍在 v7 文档树内（[链接](https://ai-sdk.dev/docs/reference/ai-sdk-ui/prune-messages)），Module 5 的剪枝思路不受影响。
>
> 同表 AI Gateway 行的 `"anthropic/claude-haiku-4-5"` 取自课程页原文；该 id 是否为 Gateway 当前有效清单成员**本次无法核实**（Gateway 模型页客户端渲染），按原文保留、待人工确认。

- **因果序列教学法**：每步因上一步「坏了」而存在——step1 加 read（看不见文件）→ step2 加 grep（不会搜）→ step3 加 bash（能跑命令了，但也能 rm -rf 了）。
- Module 1-6 全程跟做（写码→运行→验证）；Module 7 纯概念；8-11 混合。
- **前置**：TypeScript/async-await/终端基础；`AI_GATEWAY_API_KEY`；Node 20+ 或 Bun；推荐先学《Building Filesystem Agents》。

## 四、学习价值与本地知识关联

- 学习价值：★★★★★ — 与 [[2026-08-16-AI链接综述与归档]] 的「编码 Agent 解剖」主线（《Pi 的设计艺术》、pi-from-scratch）完全同向，且是**亲手构建**视角的系统课程，覆盖 Harness 全貌（工具契约/审批/沙箱/上下文/子代理/生命周期/界面/扩展）。
- 与本库已有知识的映射：
  - 工具设计与审批 ↔ [[DSH插件与Hook开发最佳实践]]（工具 schema、审批 seam、执行管线）
  - 沙箱抽象/生命周期/快照恢复 ↔ [[Claude-Ops-KB-Home]]（远程运维的沙箱、checkpoint 扛 GPU 丢失等实战教训）
  - 上下文管理/注意力预算 ↔ [[Articles-Index]] 的上下文工程两篇
  - Skills 渐进式披露 ↔ [[Anthropic-Skill系统深度分析]]、[[Skill规模化管理-从渐进式披露到检索式发现]]
  - Module 10 CLI/TUI/Web 多面 ↔ [[DSH-TUI插件使用手册]]（TUI 是渲染策略而非核心）
- 建议学习顺序：先过 [[预训练迷你Kimi-K3实录-章节总结]] 建立「测量优先」心态 → 本课程动手 → 再读 Pi 源码书做对照。

## Related

- [[2026-08-16-AI链接综述与归档]] — 追加条目 #18
- [[DSH插件与Hook开发最佳实践]] — 工具/Hooks 开发对照
- [[Articles-Index]] — 上下文工程/Skill 文章
- [[DSH-TUI插件使用手册]] — 界面层对照
- [[Claude-Ops-KB-Home]] — 沙箱/生命周期实战教训
- [[AI-Links-KB-Home]] — 本子库 MOC

## 补完记录（2026-09-13）

| 类型 | 原问题 | 处置与依据 |
|---|---|---|
| 纠错 | 全篇按 AI SDK v6 生态理解，Zod 行「v4 与 AI SDK v6 类型不兼容」未标明版本已过期 | 技术栈表下新增「版本漂移提示」引用块：npm `ai` latest=7.0.99（2026-09-12）、官方 v6→v7 迁移指南列出破坏性改名（onFinish→onEnd 等）；原转述保留不动，只标注时效 |
| 补疏漏 | 开篇五痛点只当引子，未映射到模块与对策 | 新增「五痛点 → 模块 → 机制 → 验收判据」映射表；判据取证源于官方单课页（如 /pruning-old-results 的 Done-When 清单与 `npx tsc --noEmit` 门） |
| 补疏漏 | Module 4「沙箱抽象」、Module 7「状态机/快照/durable workflow」均只有一句结论 | 新增「二·附」节：三后端取舍对照表、`Sandbox` 接口契约与「换后端工具不变」验证法、快照/恢复幂等性判据 |
| 补疏漏 | frontmatter 只有课程首页一条来源，正文无任何单课链接；Gateway 示例模型名是否有效未标 | `source_urls` 追加单课页与 AI SDK 官方页（迁移指南、pruneMessages）；正文就地标注该模型 id「本次无法核实、待人工确认」 |

依据：[Vercel Academy 课程页](https://vercel.com/academy/build-ai-agent-harness)、[Pruning Old Results 课页](https://vercel.com/academy/build-ai-agent-harness/pruning-old-results)、[npm `ai`](https://registry.npmjs.org/ai)、[AI SDK v6→v7 迁移指南](https://ai-sdk.dev/docs/migration-guides/migration-guide-7-0)。方法论回链：[[CORRECTIONS]]。
